from pathlib import Path
import pytest
from gltest.direct import VMContext, deploy_contract, create_address


@pytest.mark.direct
def test_direct_appeal_outcome_gate_validator_rejection_and_zero_storage_mutation():
    """BLOCKER 1 & BLOCKER 5: Test judge_appeal outcome-preserving consensus using official Direct Mode.

    - 7499 vs 7500 produces should_overturn mismatch (False vs True) -> validator rejects (returns False).
    - Asserts validator execution causes zero state mutation on storage.
    """
    vm = VMContext()
    owner = create_address("owner")
    upgrader = create_address("upgrader")
    merchant = create_address("merchant")
    buyer = create_address("buyer")
    ledger_addr = create_address("ledger")

    vm.sender = owner
    bond = deploy_contract(
        Path("contracts/merchant_bond.py"),
        vm,
        upgrader,
        ledger_addr,
        1000,
        100,
        200,
        300,
        3,
    )

    # Set up _gl_call_hook to respond to PriceLedger cross-contract view queries
    from genlayer.py import calldata

    def ledger_hook(v, req):
        if not isinstance(req, dict):
            return None
        call = req.get("CallContract")
        if not isinstance(call, dict):
            return None
        calldata_dict = call.get("calldata", {})
        method = calldata_dict.get("method")
        res = None
        if method == "get_product":
            res = {
                "id": 1,
                "merchant": merchant,
                "active": True,
                "url": "https://shop.com/consensus-item",
                "registered_at": 1785196000,
            }
        elif method == "get_observations":
            res = [
                {
                    "price_cents": 10000,
                    "currency": "GBP",
                    "observed_at": 1785196000 + i * 60,
                    "watcher": owner,
                    "ok": True,
                    "note": "obs",
                }
                for i in range(3)
            ]

        if res is not None:
            # ResultCode.RETURN is 0, followed by calldata payload
            return bytes([0]) + calldata.encode(res)
        return None

    vm._gl_call_hook = ledger_hook

    # Register merchant and announce sale
    vm.sender = merchant
    vm.value = 10000
    vm.warp("2026-07-28T00:00:00Z")
    bond.register_merchant("Consensus Merchant")

    sale_id = bond.announce_sale(1, 20000, 1000, 600, "GBP")

    # File claim
    vm.sender = buyer
    vm.value = 100
    claim_id = bond.file_claim(sale_id)

    # Judge claim as GENUINE (confidence 8000)
    vm.mock_web("https://shop.com/consensus-item", {"method": "GET", "status": 200, "body": "Live page text"})
    vm.mock_llm(
        r".*",
        '{"verdict": "GENUINE", "confidence_bp": 8000, "reasoning": "genuine"}',
    )
    bond.judge_claim(claim_id)

    # Buyer appeals
    vm.value = 200
    bond.appeal(claim_id)

    # Mock LLM output for leader: INFLATED_REFERENCE at 7499 (should_overturn=False)
    vm.mock_web("https://shop.com/consensus-item", {"method": "GET", "status": 200, "body": "Live page text"})
    vm.mock_llm(
        r".*",
        '{"verdict": "INFLATED_REFERENCE", "confidence_bp": 7499, "reasoning": "borderline"}',
    )

    bond.judge_appeal(claim_id)

    # Verify claim state was updated by leader to FINAL with standing verdict preserved (upheld)
    claim = bond.get_claim(claim_id)
    assert claim["state"] == "FINAL"
    assert claim["verdict"] == "GENUINE"
    assert "appeal upheld" in claim["reasoning"]

    # Verify validator execution against a disagreeing result (INFLATED_REFERENCE at 7500 -> should_overturn=True)
    # The validator closure rejects should_overturn mismatch (False vs True)
    vm.mock_llm(
        r".*",
        '{"verdict": "INFLATED_REFERENCE", "confidence_bp": 7500, "reasoning": "overturn"}',
    )

    validator_passed = vm.run_validator(
        leader_result={
            "verdict": "INFLATED_REFERENCE",
            "confidence_bp": 7499,
            "reasoning": "borderline",
            "should_overturn": False,
        }
    )
    assert validator_passed is False

    # Assert validator execution caused zero state mutation to claim storage
    claim_after = bond.get_claim(claim_id)
    assert claim_after["state"] == "FINAL"
    assert claim_after["verdict"] == "GENUINE"
