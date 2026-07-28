import base64
import hashlib
import os
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
LEDGER_SOURCE = ROOT / "contracts" / "price_ledger.py"
BOND_SOURCE = ROOT / "contracts" / "merchant_bond.py"
STUDIONET_CHAIN_ID = 61999
STUDIONET_RPC = "https://studio.genlayer.com/api"


def _enabled(name: str) -> None:
    if os.environ.get(name) != "1":
        pytest.skip(f"Opt in with {name}=1.")


def _required_address(name: str) -> str:
    value = os.environ.get(name, "")
    if len(value) != 42 or not value.startswith("0x"):
        pytest.fail(f"{name} must contain a real 20-byte contract address.")
    try:
        int(value[2:], 16)
    except ValueError:
        pytest.fail(f"{name} must contain a hexadecimal contract address.")
    return value


def _assert_studionet(client) -> None:
    assert client.chain.id == STUDIONET_CHAIN_ID
    assert client.provider.url == STUDIONET_RPC


def _deployed_source(client, address: str) -> str:
    response = client.provider.make_request("gen_getContractCode", [address])
    encoded = response.get("result")
    assert isinstance(encoded, str) and encoded
    return base64.b64decode(encoded, validate=True).decode("utf-8")


def _sha256(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _marker_source(source: str, marker: str) -> str:
    anchor = "    @gl.public.write\n    def upgrade(self, new_code: bytes) -> None:\n"
    assert source.count(anchor) == 1
    marker_view = (
        "    @gl.public.view\n"
        "    def recovery_rehearsal_marker(self) -> str:\n"
        f'        return "{marker}"\n\n'
    )
    return source.replace(anchor, marker_view + anchor)


@pytest.mark.integration
def test_corrected_studionet_source_and_config():
    """Read-only parity check for the user-authorized corrected deployment."""
    _enabled("SALEPROOF_RUN_STUDIONET_INTEGRATION")

    from gltest import get_contract_factory, get_gl_client

    ledger_address = _required_address("SALEPROOF_STUDIONET_LEDGER_ADDRESS")
    bond_address = _required_address("SALEPROOF_STUDIONET_BOND_ADDRESS")
    owner_address = _required_address("SALEPROOF_STUDIONET_OWNER_ADDRESS")
    upgrader_address = _required_address("SALEPROOF_STUDIONET_UPGRADER_ADDRESS")

    client = get_gl_client()
    _assert_studionet(client)

    ledger_source = LEDGER_SOURCE.read_text(encoding="utf-8")
    bond_source = BOND_SOURCE.read_text(encoding="utf-8")
    assert _sha256(_deployed_source(client, ledger_address)) == _sha256(ledger_source)
    assert _sha256(_deployed_source(client, bond_address)) == _sha256(bond_source)

    ledger = get_contract_factory(
        contract_file_path=LEDGER_SOURCE
    ).build_contract(ledger_address)
    bond = get_contract_factory(contract_file_path=BOND_SOURCE).build_contract(
        bond_address
    )

    ledger_config = ledger.get_config().call()
    bond_config = bond.get_config().call()
    assert str(ledger_config["owner"]).lower() == owner_address.lower()
    assert str(bond_config["owner"]).lower() == owner_address.lower()
    assert str(bond_config["ledger"]).lower() == ledger_address.lower()
    assert ledger.is_upgrader(args=[upgrader_address]).call() is True
    assert bond.is_upgrader(args=[upgrader_address]).call() is True
    assert ledger.is_registrar(args=[bond_address]).call() is True


def _rehearse_upgrade(
    *,
    client,
    factory,
    address: str,
    authorized,
    unauthorized,
    state_reader,
    marker: str,
) -> None:
    from genlayer_py.types import TransactionStatus
    from gltest.assertions import tx_execution_failed, tx_execution_succeeded
    from gltest.contracts import ContractFactory

    original_source = factory.contract_code
    rehearsal_source = _marker_source(original_source, marker)
    contract = factory.build_contract(address, account=authorized)
    before_state = state_reader(contract)
    before_code = _deployed_source(client, address)
    assert before_code == original_source

    unauthorized_contract = contract.connect(unauthorized)
    denied = unauthorized_contract.upgrade(
        args=[rehearsal_source.encode("utf-8")]
    ).transact(wait_transaction_status=TransactionStatus.FINALIZED)
    assert tx_execution_failed(denied)
    assert _deployed_source(client, address) == before_code

    rehearsed = contract.upgrade(args=[rehearsal_source.encode("utf-8")]).transact(
        wait_transaction_status=TransactionStatus.FINALIZED
    )
    assert tx_execution_succeeded(rehearsed)
    assert _deployed_source(client, address) == rehearsal_source

    rehearsal_factory = ContractFactory(
        contract_name=factory.contract_name,
        contract_code=rehearsal_source,
    )
    rehearsed_contract = rehearsal_factory.build_contract(address, account=authorized)
    assert rehearsed_contract.recovery_rehearsal_marker().call() == marker
    assert state_reader(rehearsed_contract) == before_state

    restored = rehearsed_contract.upgrade(
        args=[original_source.encode("utf-8")]
    ).transact(wait_transaction_status=TransactionStatus.FINALIZED)
    assert tx_execution_succeeded(restored)
    assert _deployed_source(client, address) == original_source
    restored_contract = factory.build_contract(address, account=authorized)
    assert state_reader(restored_contract) == before_state


@pytest.mark.integration
def test_studionet_root_upgrade_rehearsal():
    """Explicitly destructive rehearsal on dedicated, disposable contracts only."""
    _enabled("SALEPROOF_RUN_STUDIONET_UPGRADE_REHEARSAL")

    from gltest import (
        get_accounts,
        get_contract_factory,
        get_default_account,
        get_gl_client,
    )

    ledger_address = _required_address(
        "SALEPROOF_STUDIONET_REHEARSAL_LEDGER_ADDRESS"
    )
    bond_address = _required_address("SALEPROOF_STUDIONET_REHEARSAL_BOND_ADDRESS")
    release_addresses = {
        os.environ.get("SALEPROOF_STUDIONET_LEDGER_ADDRESS", "").lower(),
        os.environ.get("SALEPROOF_STUDIONET_BOND_ADDRESS", "").lower(),
    }
    assert ledger_address.lower() not in release_addresses
    assert bond_address.lower() not in release_addresses

    client = get_gl_client()
    _assert_studionet(client)
    authorized = get_default_account()
    unauthorized = next(
        (
            account
            for account in get_accounts()
            if account.address.lower() != authorized.address.lower()
        ),
        None,
    )
    if unauthorized is None:
        pytest.fail("The rehearsal requires a second configured Studionet account.")

    ledger_factory = get_contract_factory(contract_file_path=LEDGER_SOURCE)
    bond_factory = get_contract_factory(contract_file_path=BOND_SOURCE)
    ledger = ledger_factory.build_contract(ledger_address)
    bond = bond_factory.build_contract(bond_address)
    assert ledger.is_upgrader(args=[authorized.address]).call() is True
    assert bond.is_upgrader(args=[authorized.address]).call() is True
    assert ledger.is_upgrader(args=[unauthorized.address]).call() is False
    assert bond.is_upgrader(args=[unauthorized.address]).call() is False

    _rehearse_upgrade(
        client=client,
        factory=ledger_factory,
        address=ledger_address,
        authorized=authorized,
        unauthorized=unauthorized,
        state_reader=lambda contract: (
            contract.get_config().call(),
            contract.get_product_count().call(),
        ),
        marker="saleproof-ledger-root-rehearsal-v1",
    )
    _rehearse_upgrade(
        client=client,
        factory=bond_factory,
        address=bond_address,
        authorized=authorized,
        unauthorized=unauthorized,
        state_reader=lambda contract: (
            contract.get_config().call(),
            contract.get_counts().call(),
        ),
        marker="saleproof-bond-root-rehearsal-v1",
    )
