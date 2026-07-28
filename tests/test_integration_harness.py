import ast
import base64
import inspect
from pathlib import Path

import pytest
from genlayer_py.types import TransactionHashVariant

from genvm_tests.integration import test_saleproof_network as network

ROOT = Path(__file__).resolve().parents[1]


def test_integration_contract_calls_request_latest_final():
    tree = ast.parse(inspect.getsource(network))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "call"
    ]
    assert len(calls) == 22
    for call in calls:
        keyword = next(
            item for item in call.keywords if item.arg == "transaction_hash_variant"
        )
        assert isinstance(keyword.value, ast.Attribute)
        assert keyword.value.attr == "LATEST_FINAL"
    assert TransactionHashVariant.LATEST_FINAL.value == "latest-final"


def test_studionet_code_read_keeps_legacy_address_shape():
    source = "# reviewed source\n"
    address = "0x1111111111111111111111111111111111111111"

    class FakeProvider:
        def make_request(self, method, params):
            assert method == "gen_getContractCode"
            assert params == [address]
            return {"result": base64.b64encode(source.encode()).decode()}

    class FakeClient:
        provider = FakeProvider()

    assert network._deployed_source(FakeClient(), address) == source


def test_live_address_readbacks_are_canonicalized():
    address = "0x0123456789abcdef0123456789abcdef01234567"
    raw = bytes.fromhex(address[2:])

    class AddressLike:
        as_bytes = raw

    class MethodAddressLike:
        def as_bytes(self):
            return raw

    assert network._canonical_address(int(address, 16)) == address
    assert network._canonical_address(raw) == address
    assert network._canonical_address(address.upper()) == address
    assert network._canonical_address(AddressLike()) == address
    assert network._canonical_address(MethodAddressLike()) == address


@pytest.mark.parametrize(
    "value",
    [
        True,
        1 << 160,
        b"\x00" * 19,
        "0x1234",
        "0xgggggggggggggggggggggggggggggggggggggggg",
    ],
)
def test_invalid_live_address_readbacks_fail_closed(value):
    with pytest.raises(pytest.fail.Exception):
        network._canonical_address(value)


def test_rehearsal_transaction_hash_is_validated_and_normalized():
    expected = "0x" + "ab" * 32
    assert network._transaction_hash({"tx_id": expected.upper()}) == expected
    assert network._transaction_hash({"hash": bytes.fromhex("ab" * 32)}) == expected
    with pytest.raises(pytest.fail.Exception, match="no 32-byte transaction hash"):
        network._transaction_hash({"tx_id": "0x1234"})


def test_rehearsal_receipt_check_requires_finalized_actual_leader():
    def transaction(status, receipts):
        return {
            "status_name": status,
            "consensus_data": {"leader_receipt": receipts},
        }

    assert network._finalized_leader_succeeded(
        transaction(
            "FINALIZED",
            [
                {"mode": "validator", "execution_result": "ERROR"},
                {"mode": "leader", "execution_result": "SUCCESS"},
            ],
        )
    )
    assert not network._finalized_leader_succeeded(
        transaction(
            "FINALIZED",
            [
                {"mode": "validator", "execution_result": "SUCCESS"},
                {"mode": "leader", "execution_result": "ERROR"},
            ],
        )
    )
    with pytest.raises(pytest.fail.Exception, match="exactly one actual leader"):
        network._finalized_leader_succeeded(
            transaction(
                "FINALIZED",
                [{"mode": "validator", "execution_result": "SUCCESS"}],
            )
        )
    with pytest.raises(pytest.fail.Exception, match="not FINALIZED"):
        network._finalized_leader_succeeded(
            transaction(
                "ACCEPTED",
                [{"mode": "leader", "execution_result": "SUCCESS"}],
            )
        )


def test_frontend_contract_reads_request_finalized_state():
    source = (ROOT / "frontend" / "src" / "lib" / "contracts.ts").read_text(
        encoding="utf-8"
    )
    assert source.count("client.readContract({") == 12
    assert (
        source.count("transactionHashVariant: TransactionHashVariant.LATEST_FINAL")
        == 12
    )


def test_live_verifier_requests_finalized_state():
    source = (ROOT / "frontend" / "scripts" / "verify-live.mjs").read_text(
        encoding="utf-8"
    )
    assert 'from "genlayer-js/types"' in source
    assert (
        source.count("transactionHashVariant: TransactionHashVariant.LATEST_FINAL") == 2
    )
