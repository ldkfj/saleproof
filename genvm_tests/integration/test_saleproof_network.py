import os
from pathlib import Path
import pytest


@pytest.mark.integration
def test_saleproof_studionet_integration_lifecycle():
    """BLOCKER 8: Real, environment-gated Studionet integration test.

    Opt-in gated by SALEPROOF_RUN_STUDIONET_INTEGRATION=1.
    Skipped cleanly when env variable is absent or not '1'.
    """
    if os.environ.get("SALEPROOF_RUN_STUDIONET_INTEGRATION") != "1":
        pytest.skip(
            "Opt-in env SALEPROOF_RUN_STUDIONET_INTEGRATION=1 required for Studionet integration test."
        )

    private_key = os.environ.get("SALEPROOF_STUDIONET_PRIVATE_KEY") or os.environ.get(
        "PRIVATE_KEY"
    )
    if not private_key:
        pytest.skip(
            "Missing environment variable SALEPROOF_STUDIONET_PRIVATE_KEY / PRIVATE_KEY."
        )

    rpc_url = os.environ.get("SALEPROOF_STUDIONET_RPC", "https://studio.genlayer.com/api")

    # In opt-in Studionet execution mode:
    # Connect via genlayer_py client, deploy contracts, test view methods and transactions,
    # and rehearse native Root locked-slot upgrade authorization.
    import gltest
    from genlayer_py import GenLayerClient, Account

    account = Account.from_private_key(private_key)
    client = GenLayerClient(rpc_url=rpc_url, chain_id=61999)

    # 1. Deploy PriceLedger
    ledger_factory = gltest.get_contract_factory("PriceLedger")
    ledger_tx = ledger_factory.deploy(account=account, args=[account.address, 300, 1000])
    ledger_address = client.wait_for_transaction_receipt(ledger_tx)["contract_address"]
    assert ledger_address is not None

    # 2. Deploy MerchantBond
    bond_factory = gltest.get_contract_factory("MerchantBond")
    bond_tx = bond_factory.deploy(
        account=account,
        args=[account.address, ledger_address, 1000, 100, 200, 300, 3],
    )
    bond_address = client.wait_for_transaction_receipt(bond_tx)["contract_address"]
    assert bond_address is not None

    # 3. Read views from deployed contracts
    ledger_contract = client.get_contract(address=ledger_address, abi=ledger_factory.abi)
    assert ledger_contract.get_product_count() == 0

    bond_contract = client.get_contract(address=bond_address, abi=bond_factory.abi)
    assert bond_contract.get_counts() == {"sale_count": 0, "claim_count": 0}

    # 4. Rehearse native Root locked-slot upgrade authorization on Studionet
    ledger_code = Path("contracts/price_ledger.py").read_bytes()
    upgrade_tx = ledger_contract.upgrade(ledger_code, account=account)
    receipt = client.wait_for_transaction_receipt(upgrade_tx)
    assert receipt["status"] == "SUCCESS"
