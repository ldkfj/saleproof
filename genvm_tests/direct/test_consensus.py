from copy import deepcopy

import pytest


BOND_PATH = "contracts/merchant_bond.py"
PRODUCT_URL = "https://shop.com/consensus-item"


def _install_ledger_view_hook(vm, merchant, watcher):
    """Direct Mode 0.29.2 has no public cross-contract view-mock API."""
    from genlayer.py import calldata

    def ledger_hook(_vm, request):
        if not isinstance(request, dict):
            return None
        call = request.get("CallContract")
        if not isinstance(call, dict):
            return None
        method = call.get("calldata", {}).get("method")
        if method == "get_product":
            result = {
                "id": 1,
                "merchant": merchant,
                "active": True,
                "url": PRODUCT_URL,
                "registered_at": 1785196000,
            }
        elif method == "get_observations":
            result = [
                {
                    "price_cents": 10000,
                    "currency": "GBP",
                    "observed_at": 1785196000 + i * 60,
                    "watcher": watcher,
                    "ok": True,
                    "note": "obs",
                }
                for i in range(3)
            ]
        else:
            return None
        return bytes([0]) + calldata.encode(result)

    # Narrow compatibility seam for a capability absent from the public
    # Direct Mode API; no loader/VM methods are monkeypatched.
    vm._gl_call_hook = ledger_hook


def _set_judgment_mocks(vm, response):
    vm.clear_mocks()
    vm.mock_web(
        PRODUCT_URL,
        {"method": "GET", "status": 200, "body": "Live page text"},
    )
    vm.mock_llm(r"^You are a consumer-protection analyst", response)


def _set_appeal_mocks(vm, response):
    vm.clear_mocks()
    vm.mock_web(
        PRODUCT_URL,
        {"method": "GET", "status": 200, "body": "Live page text"},
    )
    vm.mock_llm(r"^You are a skeptical senior auditor", response)


def _bond_state(bond, merchant, buyer, upgrader):
    """Snapshot every populated ordinary storage field through public views."""
    return deepcopy(
        {
            "config": bond.get_config(),
            "counts": bond.get_counts(),
            "merchant": bond.get_merchant(merchant),
            "sale": bond.get_sale(1),
            "claim": bond.get_claim(1),
            "buyer_withdrawable": bond.get_withdrawable(buyer),
            "merchant_withdrawable": bond.get_withdrawable(merchant),
            "upgrader_registered": bond.is_upgrader(upgrader),
        }
    )


@pytest.mark.direct
def test_direct_appeal_validator_preserves_7500_outcome_gate_and_storage(
    direct_vm,
    direct_deploy,
    direct_owner,
    direct_alice,
    direct_bob,
    direct_charlie,
):
    direct_vm.check_pickling = True
    direct_vm.strict_mocks = True
    direct_vm.warp("2026-07-28T00:00:00Z")
    direct_vm.sender = direct_owner
    bond = direct_deploy(
        BOND_PATH,
        direct_charlie,
        direct_owner,
        1000,
        100,
        200,
        300,
        3,
    )
    _install_ledger_view_hook(direct_vm, direct_alice, direct_owner)

    direct_vm.sender = direct_alice
    direct_vm.value = 10000
    bond.register_merchant("Consensus Merchant")
    sale_id = bond.announce_sale(1, 20000, 1000, 600, "GBP")

    direct_vm.sender = direct_bob
    direct_vm.value = 100
    claim_id = bond.file_claim(sale_id)

    _set_judgment_mocks(
        direct_vm,
        '{"verdict": "GENUINE", "confidence_bp": 8000, "reasoning": "genuine"}',
    )
    bond.judge_claim(claim_id)

    direct_vm.sender = direct_bob
    direct_vm.value = 200
    bond.appeal(claim_id)

    _set_appeal_mocks(
        direct_vm,
        '{"verdict": "INFLATED_REFERENCE", "confidence_bp": 7499, "reasoning": "borderline"}',
    )
    bond.judge_appeal(claim_id)
    leader_state = _bond_state(
        bond, direct_alice, direct_bob, direct_charlie
    )
    assert leader_state["claim"]["state"] == "FINAL"
    assert leader_state["claim"]["verdict"] == "GENUINE"

    # Genuine cross-boundary disagreement: the leader is below 7500 while
    # the validator independently derives the opposite outcome at 7500.
    _set_appeal_mocks(
        direct_vm,
        '{"verdict": "INFLATED_REFERENCE", "confidence_bp": 7500, "reasoning": "overturn"}',
    )
    assert direct_vm.run_validator() is False
    assert _bond_state(
        bond, direct_alice, direct_bob, direct_charlie
    ) == leader_state

    # A fabricated leader flag cannot bypass the threshold, and bool-as-int
    # is rejected before any nondeterministic validator work is attempted.
    direct_vm.clear_mocks()
    invalid_flag = {
        "verdict": "INFLATED_REFERENCE",
        "confidence_bp": 7499,
        "reasoning": "fabricated",
        "should_overturn": True,
    }
    assert direct_vm.run_validator(leader_result=invalid_flag) is False
    invalid_type = dict(invalid_flag, should_overturn=1)
    assert direct_vm.run_validator(leader_result=invalid_type) is False
    assert _bond_state(
        bond, direct_alice, direct_bob, direct_charlie
    ) == leader_state

    # Values may vary inside one outcome region without changing the branch.
    _set_appeal_mocks(
        direct_vm,
        '{"verdict": "INFLATED_REFERENCE", "confidence_bp": 7600, "reasoning": "overturn"}',
    )
    same_region_leader = {
        "verdict": "INFLATED_REFERENCE",
        "confidence_bp": 7500,
        "reasoning": "overturn",
        "should_overturn": True,
    }
    assert (
        direct_vm.run_validator(leader_result=same_region_leader) is True
    )
    assert _bond_state(
        bond, direct_alice, direct_bob, direct_charlie
    ) == leader_state
