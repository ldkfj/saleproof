import pytest
import cloudpickle
from genlayer import gl, Address
import contracts.price_ledger as ledger_mod
from contracts.price_ledger import PriceLedger, validate_extraction

UPGRADER = "0x9999999999999999999999999999999999999999"
OWNER = "0x1111111111111111111111111111111111111111"
ALICE = "0x2222222222222222222222222222222222222222"
MERCHANT = "0x4444444444444444444444444444444444444444"


@pytest.mark.direct
def test_direct_price_ledger_deploy_and_crud(direct_vm, monkeypatch):
    monkeypatch.setattr(ledger_mod, "_now", lambda: direct_vm.timestamp)
    gl.message.sender_address = OWNER
    gl.storage.Root.reset()

    ledger = PriceLedger(upgrader_address=UPGRADER)
    assert ledger.is_upgrader(UPGRADER) is True

    ledger.add_registrar(ALICE)
    gl.message.sender_address = ALICE

    p_id = ledger.register_product("https://shop.com/shoes", MERCHANT)
    assert p_id == 1

    prod = ledger.get_product(1)
    assert prod["registered_at"] == 1785196800
    assert prod["merchant"] == Address(MERCHANT)


@pytest.mark.direct
def test_direct_price_ledger_user_error_messages(direct_vm):
    gl.message.sender_address = OWNER
    gl.storage.Root.reset()
    ledger = PriceLedger(upgrader_address=UPGRADER)

    with pytest.raises(gl.vm.UserError) as exc_info:
        ledger.get_product(999)
    assert str(exc_info.value) == "ERR_NO_PRODUCT"


@pytest.mark.direct
def test_direct_price_ledger_snapshot_and_cloudpickle(direct_vm, monkeypatch):
    monkeypatch.setattr(ledger_mod, "_now", lambda: direct_vm.timestamp)
    gl.message.sender_address = OWNER
    gl.storage.Root.reset()

    ledger = PriceLedger(upgrader_address=UPGRADER)
    ledger.add_registrar(ALICE)

    gl.message.sender_address = ALICE
    p_id = ledger.register_product("https://shop.com/fenced", MERCHANT)

    url = "https://shop.com/fenced"
    fenced_json = '```json\n{"found": true, "price_cents": 5177, "currency": "GBP", "note": "Fenced Item"}\n```'

    def leader_closure():
        raw = fenced_json
        found, price_cents, currency, note = validate_extraction(raw)
        return {"found": found, "price_cents": price_cents, "currency": currency, "note": note}

    def validator_closure(res):
        return res["found"] is True and res["currency"] == "GBP" and res["price_cents"] == 5177

    # Explicitly cloudpickle leader and validator closures to verify serialization safety
    leader_bytes = cloudpickle.dumps(leader_closure)
    validator_bytes = cloudpickle.dumps(validator_closure)
    assert len(leader_bytes) > 0
    assert len(validator_bytes) > 0

    restored_leader = cloudpickle.loads(leader_bytes)
    res = restored_leader()
    assert res == {"found": True, "price_cents": 5177, "currency": "GBP", "note": "Fenced Item"}

    gl._fake_page = "Fenced Item price £51.77"
    gl._fake_llm_output = fenced_json
    ledger.snapshot(p_id)

    obs = ledger.get_observations(p_id)
    assert len(obs) == 1
    assert obs[0]["price_cents"] == 5177
    assert obs[0]["currency"] == "GBP"
