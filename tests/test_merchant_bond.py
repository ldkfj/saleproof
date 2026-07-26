import pytest
from genlayer import Address, gl

import contracts.merchant_bond as bond_mod
from contracts.merchant_bond import (
    Claim,
    MerchantBond,
    STATE_APPEALED,
    STATE_FINAL,
    STATE_JUDGED,
    STATE_OPEN,
    STATE_SETTLED,
    VERDICT_DECEPTIVE,
    VERDICT_GENUINE,
    VERDICT_INFLATED,
    VERDICT_INSUFFICIENT,
    compute_settlement,
)


OWNER = "0x1111111111111111111111111111111111111111"
MERCHANT = "0x2222222222222222222222222222222222222222"
BUYER = "0x3333333333333333333333333333333333333333"
BOB = "0x4444444444444444444444444444444444444444"
LEDGER = "0x5555555555555555555555555555555555555555"
ZERO = "0x0000000000000000000000000000000000000000"
NOW = 1_710_000_000


class EmitRecorder:
    def __init__(self, ledger, on):
        self.ledger = ledger
        self.on = on

    def register_product(self, *args):
        self.ledger.calls.append(
            {"method": "register_product", "args": args, "on": self.on}
        )


class FakeLedger:
    def __init__(self):
        self.products = {}
        self.calls = []

    def view(self):
        return self

    def get_product(self, product_id):
        if product_id not in self.products:
            raise Exception("missing product")
        return self.products[product_id]

    def emit(self, on=None):
        return EmitRecorder(self, on)


class TransferProxy:
    def __init__(self, recorder, recipient):
        self.recorder = recorder
        self.recipient = recipient

    def emit_transfer(self, *, value):
        self.recorder.calls.append(
            {
                "recipient": self.recipient,
                "value": value,
                "entry_at_emit": self.recorder.contract.withdrawable.get(
                    self.recipient, 0
                ),
            }
        )


class TransferRecorder:
    def __init__(self, contract):
        self.contract = contract
        self.calls = []

    def __call__(self, recipient):
        return TransferProxy(self, recipient)


@pytest.fixture(autouse=True)
def reset_gl():
    gl.message.sender_address = OWNER
    gl.message.value = 0
    gl._fake_contract = None


def assert_error(code, fn, *args):
    with pytest.raises(Exception) as exc_info:
        fn(*args)
    assert str(exc_info.value).startswith(code)


def make_bond(monkeypatch, *, strike_limit=3, min_bond=10_000):
    clock = {"now": NOW}
    monkeypatch.setattr(bond_mod, "_now", lambda: clock["now"])
    fake_ledger = FakeLedger()
    gl._fake_contract = fake_ledger
    gl.message.sender_address = OWNER
    contract = MerchantBond(
        ledger=LEDGER,
        min_bond_wei=min_bond,
        claim_deposit_wei=100,
        appeal_bond_wei=200,
        appeal_window_s=300,
        strike_limit=strike_limit,
    )
    return contract, fake_ledger, clock


def register(contract, sender=MERCHANT, *, name="Merchant", value=10_000):
    gl.message.sender_address = sender
    gl.message.value = value
    contract.register_merchant(name)
    gl.message.value = 0


def announce(contract, ledger, *, merchant=MERCHANT, product_id=1):
    ledger.products[product_id] = {
        "merchant": merchant,
        "active": True,
    }
    gl.message.sender_address = merchant
    return contract.announce_sale(product_id, 20_000, 1_000, 600)


def file_claim(contract, sale_id=1, buyer=BUYER):
    gl.message.sender_address = buyer
    gl.message.value = contract.claim_deposit_wei
    claim_id = contract.file_claim(sale_id)
    gl.message.value = 0
    return claim_id


def bare_claim(state=STATE_OPEN):
    return Claim(
        id=1,
        sale_id=1,
        buyer=Address(BUYER),
        deposit_wei=100,
        state=state,
        verdict="",
        confidence_bp=0,
        reasoning="",
        appellant=Address(ZERO),
        created_at=NOW,
        judged_at=0,
    )


def test_1_registration_happy_path(monkeypatch):
    contract, _, _ = make_bond(monkeypatch)
    register(contract)

    merchant = contract.get_merchant(MERCHANT)
    assert merchant == {
        "addr": Address(MERCHANT),
        "name": "Merchant",
        "bond_wei": 10_000,
        "strikes": 0,
        "active": True,
        "joined_at": NOW,
    }
    assert contract.get_counts() == {"sale_count": 0, "claim_count": 0}
    assert contract.get_config()["ledger"] == Address(LEDGER)


def test_2_registration_guards(monkeypatch):
    contract, _, _ = make_bond(monkeypatch)
    register(contract)

    gl.message.sender_address = MERCHANT
    gl.message.value = 0
    assert_error("ERR_ALREADY_MERCHANT", contract.register_merchant, "")

    gl.message.sender_address = BOB
    gl.message.value = 10_000
    assert_error("ERR_NAME", contract.register_merchant, "   ")
    assert_error("ERR_NAME", contract.register_merchant, "x" * 101)
    gl.message.value = 9_999
    assert_error("ERR_MIN_BOND", contract.register_merchant, "Bob")


def test_3_top_up_happy_path(monkeypatch):
    contract, _, _ = make_bond(monkeypatch)
    register(contract)

    gl.message.sender_address = MERCHANT
    gl.message.value = 250
    contract.top_up_bond()
    assert contract.get_merchant(MERCHANT)["bond_wei"] == 10_250


def test_4_top_up_guards(monkeypatch):
    contract, _, _ = make_bond(monkeypatch)
    gl.message.sender_address = BOB
    gl.message.value = 0
    assert_error("ERR_NOT_MERCHANT", contract.top_up_bond)

    register(contract)
    gl.message.sender_address = MERCHANT
    gl.message.value = 0
    assert_error("ERR_ZERO_VALUE", contract.top_up_bond)


def test_5_add_product_guards_and_emit(monkeypatch):
    contract, ledger, _ = make_bond(monkeypatch)
    gl.message.sender_address = BOB
    assert_error("ERR_NOT_MERCHANT", contract.add_product, "")

    register(contract)
    gl.message.sender_address = MERCHANT
    assert_error("ERR_URL_EMPTY", contract.add_product, "   ")
    assert_error("ERR_URL_SCHEME", contract.add_product, "ftp://shop.test/item")
    assert_error(
        "ERR_URL_TOO_LONG",
        contract.add_product,
        "https://shop.test/" + "x" * 490,
    )

    contract.add_product("https://shop.test/item")
    call = ledger.calls[0]
    assert call["method"] == "register_product"
    assert call["args"] == ("https://shop.test/item", Address(MERCHANT))
    assert call["on"] == "finalized"


def test_6_announce_sale_scalar_guards(monkeypatch):
    contract, _, _ = make_bond(monkeypatch)
    gl.message.sender_address = BOB
    assert_error("ERR_NOT_MERCHANT", contract.announce_sale, 1, 0, 0, 0)

    register(contract)
    gl.message.sender_address = MERCHANT
    for price in (0, 1_000_000_001):
        assert_error("ERR_PRICE", contract.announce_sale, 1, price, 1_000, 600)
    for discount in (99, 9_501):
        assert_error(
            "ERR_DISCOUNT", contract.announce_sale, 1, 1_000, discount, 600
        )
    for duration in (599, 2_592_001):
        assert_error(
            "ERR_DURATION", contract.announce_sale, 1, 1_000, 1_000, duration
        )


def test_7_announce_sale_product_guards(monkeypatch):
    contract, ledger, _ = make_bond(monkeypatch)
    register(contract)
    gl.message.sender_address = MERCHANT
    assert_error("ERR_NO_PRODUCT", contract.announce_sale, 1, 1_000, 1_000, 600)

    ledger.products[1] = {"merchant": BOB, "active": True}
    assert_error(
        "ERR_NOT_YOUR_PRODUCT", contract.announce_sale, 1, 1_000, 1_000, 600
    )
    ledger.products[1] = {"merchant": MERCHANT, "active": False}
    assert_error(
        "ERR_PRODUCT_INACTIVE", contract.announce_sale, 1, 1_000, 1_000, 600
    )


def test_8_announce_sale_happy_path(monkeypatch):
    contract, ledger, _ = make_bond(monkeypatch)
    register(contract)
    sale_id = announce(contract, ledger)

    assert sale_id == 1
    assert contract.get_sale(1) == {
        "id": 1,
        "merchant": Address(MERCHANT),
        "product_id": 1,
        "claimed_ref_price_cents": 20_000,
        "claimed_discount_bp": 1_000,
        "announced_at": NOW,
        "ends_at": NOW + 600,
        "active": True,
    }


def test_9_file_claim_base_guards(monkeypatch):
    contract, ledger, clock = make_bond(monkeypatch)
    register(contract)
    gl.message.sender_address = BUYER
    assert_error("ERR_NO_SALE", contract.file_claim, 999)

    sale_id = announce(contract, ledger)
    clock["now"] = NOW + 601
    assert_error("ERR_SALE_CLOSED", contract.file_claim, sale_id)
    clock["now"] = NOW

    gl.message.sender_address = MERCHANT
    gl.message.value = 100
    assert_error("ERR_SELF_CLAIM", contract.file_claim, sale_id)
    gl.message.sender_address = BUYER
    gl.message.value = 99
    assert_error("ERR_DEPOSIT", contract.file_claim, sale_id)


def test_10_file_claim_happy_and_duplicate(monkeypatch):
    contract, ledger, _ = make_bond(monkeypatch)
    register(contract)
    sale_id = announce(contract, ledger)
    claim_id = file_claim(contract, sale_id)

    assert claim_id == 1
    claim = contract.get_claim(claim_id)
    assert claim["buyer"] == Address(BUYER)
    assert claim["deposit_wei"] == 100
    assert claim["state"] == STATE_OPEN
    assert claim["verdict"] == ""
    assert claim["appellant"] == Address(ZERO)

    gl.message.sender_address = BUYER
    gl.message.value = 100
    assert_error("ERR_DUPLICATE_CLAIM", contract.file_claim, sale_id)


def test_11_file_claim_coverage_guard(monkeypatch):
    contract, ledger, _ = make_bond(monkeypatch)
    register(contract)
    sale_id = announce(contract, ledger)

    for offset in range(10):
        buyer = "0x" + f"{0x60 + offset:040x}"
        assert file_claim(contract, sale_id, buyer) == offset + 1

    eleventh_buyer = "0x" + f"{0x70:040x}"
    gl.message.sender_address = eleventh_buyer
    gl.message.value = 100
    assert_error("ERR_BOND_COVERAGE", contract.file_claim, sale_id)


def test_12_compute_settlement_all_verdicts_and_invariant():
    cases = {
        VERDICT_GENUINE: (0, 50, 51, 0, False),
        VERDICT_INFLATED: (151, 0, 0, -50, True),
        VERDICT_DECEPTIVE: (201, 0, 0, -100, True),
        VERDICT_INSUFFICIENT: (101, 0, 0, 0, False),
    }
    for verdict, expected in cases.items():
        result = compute_settlement(verdict, 101, 1_000)
        assert tuple(result.values()) == expected
        assert (
            result["buyer_wei"]
            + result["merchant_wei"]
            + result["pool_wei"]
            == 101 + max(0, -result["bond_delta_wei"])
        )

    assert compute_settlement(VERDICT_DECEPTIVE, 101, 0)["buyer_wei"] == 101


def test_13_compute_settlement_unknown_verdict():
    with pytest.raises(ValueError) as exc_info:
        compute_settlement("UNKNOWN", 100, 1_000)
    assert str(exc_info.value) == "ERR_BAD_VERDICT"


def test_14_transition_unappealed_path():
    claim = bare_claim()
    bond_mod._transition(claim, "judge")
    assert claim.state == STATE_JUDGED
    bond_mod._transition(claim, "finalize")
    assert claim.state == STATE_FINAL
    bond_mod._transition(claim, "settle")
    assert claim.state == STATE_SETTLED


def test_15_transition_appealed_path():
    claim = bare_claim()
    bond_mod._transition(claim, "judge")
    bond_mod._transition(claim, "appeal")
    assert claim.state == STATE_APPEALED
    bond_mod._transition(claim, "judge_appeal")
    assert claim.state == STATE_FINAL
    bond_mod._transition(claim, "settle")
    assert claim.state == STATE_SETTLED


def test_16_transition_illegal_actions():
    illegal = [
        (STATE_OPEN, "settle"),
        (STATE_JUDGED, "judge"),
        (STATE_APPEALED, "finalize"),
        (STATE_FINAL, "appeal"),
        (STATE_SETTLED, "settle"),
    ]
    for state, action in illegal:
        assert_error("ERR_BAD_TRANSITION", bond_mod._transition, bare_claim(state), action)


def test_17_finalize_unappealed_window(monkeypatch):
    contract, ledger, clock = make_bond(monkeypatch)
    register(contract)
    claim_id = file_claim(contract, announce(contract, ledger))
    claim = contract.claims[claim_id]
    claim.state = STATE_JUDGED
    claim.judged_at = NOW

    assert_error("ERR_APPEAL_WINDOW_OPEN", contract.finalize_unappealed, claim_id)
    clock["now"] = NOW + contract.appeal_window_s + 1
    contract.finalize_unappealed(claim_id)
    assert claim.state == STATE_FINAL


def test_18_settle_per_verdict_bookkeeping(monkeypatch):
    expected = {
        VERDICT_GENUINE: (0, 50, 50, 10_000),
        VERDICT_INFLATED: (600, 0, 0, 9_500),
        VERDICT_DECEPTIVE: (1_100, 0, 0, 9_000),
        VERDICT_INSUFFICIENT: (100, 0, 0, 10_000),
    }
    for verdict, amounts in expected.items():
        contract, ledger, _ = make_bond(monkeypatch)
        register(contract)
        claim_id = file_claim(contract, announce(contract, ledger))
        claim = contract.claims[claim_id]
        claim.state = STATE_FINAL
        claim.verdict = verdict
        gl.message.sender_address = BOB
        contract.settle(claim_id)

        buyer, merchant, pool, bond = amounts
        assert contract.get_withdrawable(BUYER)["amount_wei"] == buyer
        assert contract.get_withdrawable(MERCHANT)["amount_wei"] == merchant
        assert contract.pool_wei == pool
        assert contract.get_merchant(MERCHANT)["bond_wei"] == bond
        assert claim.state == STATE_SETTLED


def test_19_settle_strikes_deactivation_and_double_settle(monkeypatch):
    contract, ledger, _ = make_bond(monkeypatch, strike_limit=2)
    register(contract)
    sale_id = announce(contract, ledger)

    first = file_claim(contract, sale_id, BUYER)
    second = file_claim(contract, sale_id, BOB)
    for claim_id in (first, second):
        contract.claims[claim_id].state = STATE_FINAL
        contract.claims[claim_id].verdict = VERDICT_DECEPTIVE
        contract.settle(claim_id)

    merchant = contract.get_merchant(MERCHANT)
    assert merchant["strikes"] == 2
    assert merchant["active"] is False
    before = contract.get_withdrawable(BOB)["amount_wei"]
    assert_error("ERR_BAD_TRANSITION", contract.settle, second)
    assert contract.get_withdrawable(BOB)["amount_wei"] == before


def test_20_withdraw_zero_before_transfer(monkeypatch):
    contract, _, _ = make_bond(monkeypatch)
    sender = Address(BUYER)
    contract.withdrawable[sender] = 123
    recorder = TransferRecorder(contract)
    monkeypatch.setattr(bond_mod, "_Recipient", recorder)

    gl.message.sender_address = BUYER
    contract.withdraw()
    assert recorder.calls == [
        {"recipient": sender, "value": 123, "entry_at_emit": 0}
    ]
    assert_error("ERR_NOTHING_TO_WITHDRAW", contract.withdraw)


def test_21_withdraw_bond_blocked_by_open_claim(monkeypatch):
    contract, ledger, _ = make_bond(monkeypatch)
    register(contract)
    file_claim(contract, announce(contract, ledger))

    gl.message.sender_address = MERCHANT
    assert_error("ERR_OPEN_CLAIMS", contract.withdraw_bond)


def test_22_withdraw_bond_blocked_by_active_sale(monkeypatch):
    contract, ledger, _ = make_bond(monkeypatch)
    register(contract)
    announce(contract, ledger)

    gl.message.sender_address = MERCHANT
    assert_error("ERR_ACTIVE_SALES", contract.withdraw_bond)


def test_23_withdraw_bond_happy_path(monkeypatch):
    contract, ledger, clock = make_bond(monkeypatch)
    register(contract)
    sale_id = announce(contract, ledger)
    clock["now"] = contract.sales[sale_id].ends_at + 1

    gl.message.sender_address = MERCHANT
    contract.withdraw_bond()
    merchant = contract.get_merchant(MERCHANT)
    assert merchant["bond_wei"] == 0
    assert merchant["active"] is False
    assert contract.get_withdrawable(MERCHANT)["amount_wei"] == 10_000


def test_24_int_sender_normalization_and_view_errors(monkeypatch):
    contract, _, _ = make_bond(monkeypatch)
    register(contract, sender=int(MERCHANT, 16))

    assert contract.get_merchant(MERCHANT)["addr"] == Address(MERCHANT)
    gl.message.sender_address = MERCHANT
    gl.message.value = 1
    contract.top_up_bond()
    assert len(contract.merchants) == 1
    assert contract.get_merchant(int(MERCHANT, 16))["bond_wei"] == 10_001
    assert contract.get_withdrawable(int(MERCHANT, 16))["amount_wei"] == 0

    assert_error("ERR_NO_MERCHANT", contract.get_merchant, BOB)
    assert_error("ERR_NO_SALE", contract.get_sale, 1)
    assert_error("ERR_NO_CLAIM", contract.get_claim, 1)
