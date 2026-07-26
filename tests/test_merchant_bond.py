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
    validate_verdict,
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
        self.observations = {}
        self.calls = []

    def view(self):
        return self

    def get_product(self, product_id):
        if product_id not in self.products:
            raise Exception("missing product")
        return self.products[product_id]

    def get_observations(self, product_id):
        return self.observations.get(product_id, [])

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
    gl._fake_page = ""
    gl._fake_llm_output = ""
    gl._last_url = ""
    gl._last_mode = ""
    gl._last_prompt = ""
    gl._last_criteria = ""


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
        "url": "https://shop.test/item",
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
        appeal_bond_wei=0,
        original_verdict="",
        created_at=NOW,
        judged_at=0,
    )


def valid_observations(count=3):
    return [
        {
            "price_cents": 10_000 + index * 100,
            "currency": "USD",
            "observed_at": NOW - (count - index) * 60,
            "ok": True,
        }
        for index in range(count)
    ]


def prepare_claim(contract, ledger, buyer=BUYER):
    register(contract)
    sale_id = announce(contract, ledger)
    return file_claim(contract, sale_id, buyer)


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


def test_25_struck_out_merchant_is_inactive_and_banned(monkeypatch):
    contract, _, _ = make_bond(monkeypatch, strike_limit=2)
    register(contract)
    merchant = contract.merchants[Address(MERCHANT)]
    merchant.strikes = contract.strike_limit
    merchant.active = False

    gl.message.sender_address = MERCHANT
    gl.message.value = 1
    assert_error("ERR_MERCHANT_INACTIVE", contract.top_up_bond)
    assert_error(
        "ERR_MERCHANT_INACTIVE",
        contract.add_product,
        "https://shop.test/banned",
    )
    assert_error(
        "ERR_MERCHANT_INACTIVE",
        contract.announce_sale,
        1,
        1_000,
        1_000,
        600,
    )

    gl.message.value = contract.min_bond_wei
    assert_error("ERR_BANNED", contract.register_merchant, "Banned Merchant")


def test_26_voluntary_exit_and_reactivation(monkeypatch):
    contract, ledger, _ = make_bond(monkeypatch)
    register(contract)
    merchant = contract.merchants[Address(MERCHANT)]
    merchant.strikes = 1
    joined_at = merchant.joined_at

    gl.message.sender_address = MERCHANT
    contract.withdraw_bond()
    assert merchant.active is False
    assert merchant.bond_wei == 0
    assert contract.get_withdrawable(MERCHANT)["amount_wei"] == 10_000
    assert_error(
        "ERR_MERCHANT_INACTIVE",
        contract.add_product,
        "https://shop.test/reactivate",
    )
    assert_error(
        "ERR_MERCHANT_INACTIVE",
        contract.announce_sale,
        1,
        1_000,
        1_000,
        600,
    )

    gl.message.value = 12_000
    contract.register_merchant("Reactivated Merchant")
    reactivated = contract.get_merchant(MERCHANT)
    assert reactivated["name"] == "Reactivated Merchant"
    assert reactivated["bond_wei"] == 12_000
    assert reactivated["active"] is True
    assert reactivated["strikes"] == 1
    assert reactivated["joined_at"] == joined_at

    contract.add_product("https://shop.test/reactivate")
    assert ledger.calls[-1]["args"] == (
        "https://shop.test/reactivate",
        Address(MERCHANT),
    )
    ledger.products[1] = {"merchant": MERCHANT, "active": True}
    assert contract.announce_sale(1, 1_000, 1_000, 600) == 1


def test_27_active_merchant_reregister_regression(monkeypatch):
    contract, _, _ = make_bond(monkeypatch)
    register(contract)

    gl.message.sender_address = MERCHANT
    gl.message.value = 0
    assert_error("ERR_ALREADY_MERCHANT", contract.register_merchant, "")


def test_28_strip_fences_and_fenced_verdict_payloads():
    payload = (
        '{"verdict":"GENUINE","confidence_bp":8000,'
        '"reasoning":"history supports the claim"}'
    )
    assert bond_mod._strip_fences(payload) == payload
    assert validate_verdict(f"```json\n{payload}\n```") == (
        VERDICT_GENUINE,
        8000,
        "history supports the claim",
    )
    assert validate_verdict(f"```\n{payload}\n```") == (
        VERDICT_GENUINE,
        8000,
        "history supports the claim",
    )
    with pytest.raises(ValueError) as exc_info:
        validate_verdict("```json\n```")
    assert str(exc_info.value).startswith("ERR_VERDICT_INVALID")


@pytest.mark.parametrize(
    "raw",
    [
        '{"verdict":"UNKNOWN","confidence_bp":8000,"reasoning":"x"}',
        '{"verdict":"GENUINE","confidence_bp":8000,"reasoning":"x","extra":1}',
        '{"verdict":"GENUINE","confidence_bp":8000}',
        '{"verdict":"GENUINE","confidence_bp":true,"reasoning":"x"}',
        '{"verdict":"GENUINE","confidence_bp":"8000","reasoning":"x"}',
        '{"verdict":"GENUINE","confidence_bp":-1,"reasoning":"x"}',
        '{"verdict":"GENUINE","confidence_bp":10001,"reasoning":"x"}',
        '{"verdict":"GENUINE","confidence_bp":8000,"reasoning":"'
        + ("x" * 401)
        + '"}',
        "x" * 3000,
        'Result: {"verdict":"GENUINE","confidence_bp":8000,"reasoning":"x"}',
    ],
    ids=[
        "wrong-verdict",
        "extra-key",
        "missing-key",
        "confidence-bool",
        "confidence-str",
        "confidence-negative",
        "confidence-too-high",
        "reasoning-too-long",
        "raw-too-large",
        "prose-wrapped",
    ],
)
def test_29_validate_verdict_adversarial(raw):
    with pytest.raises(ValueError) as exc_info:
        validate_verdict(raw)
    assert str(exc_info.value).startswith("ERR_VERDICT_INVALID")


def test_30_judge_claim_guards_short_circuit_and_happy(monkeypatch):
    contract, ledger, _ = make_bond(monkeypatch)
    assert_error("ERR_NO_CLAIM", contract.judge_claim, 999)
    claim_id = prepare_claim(contract, ledger)
    claim = contract.claims[claim_id]
    claim.state = STATE_JUDGED
    assert_error("ERR_BAD_TRANSITION", contract.judge_claim, claim_id)

    claim.state = STATE_OPEN
    ledger.observations[1] = valid_observations(2)
    gl._fake_llm_output = (
        '{"verdict":"DECEPTIVE","confidence_bp":9000,'
        '"reasoning":"must not run"}'
    )
    contract.judge_claim(claim_id)
    assert claim.state == STATE_JUDGED
    assert claim.verdict == VERDICT_INSUFFICIENT
    assert claim.confidence_bp == 10000
    assert claim.reasoning == (
        "fewer than 3 valid on-chain price observations"
    )
    assert gl._last_prompt == ""

    happy_contract, happy_ledger, _ = make_bond(monkeypatch)
    happy_claim_id = prepare_claim(happy_contract, happy_ledger)
    happy_ledger.observations[1] = valid_observations(3)
    gl._fake_page = "Current product page price is $90"
    gl._fake_llm_output = (
        '{"verdict":"INFLATED_REFERENCE","confidence_bp":8200,'
        '"reasoning":"reference exceeds the observed low"}'
    )
    happy_contract.judge_claim(happy_claim_id)
    happy_claim = happy_contract.claims[happy_claim_id]
    assert happy_claim.state == STATE_JUDGED
    assert happy_claim.verdict == VERDICT_INFLATED
    assert happy_claim.confidence_bp == 8200
    assert '"p":10000' in gl._last_prompt
    assert "reference price 20000 cents" in gl._last_prompt
    assert "discount 1000 basis points" in gl._last_prompt
    assert "Current product page price is $90" in gl._last_prompt


def test_31_appeal_guards_and_happy_merchant_path(monkeypatch):
    contract, ledger, clock = make_bond(monkeypatch)
    claim_id = prepare_claim(contract, ledger)
    claim = contract.claims[claim_id]
    claim.state = STATE_JUDGED
    claim.verdict = VERDICT_DECEPTIVE
    claim.confidence_bp = 8000
    claim.reasoning = "standing"
    claim.judged_at = NOW

    gl.message.sender_address = MERCHANT
    gl.message.value = contract.appeal_bond_wei
    clock["now"] = NOW + contract.appeal_window_s + 1
    assert_error("ERR_APPEAL_WINDOW_CLOSED", contract.appeal, claim_id)

    clock["now"] = NOW
    gl.message.value = contract.appeal_bond_wei - 1
    assert_error("ERR_APPEAL_BOND", contract.appeal, claim_id)

    gl.message.value = contract.appeal_bond_wei
    gl.message.sender_address = BUYER
    assert_error("ERR_NOT_APPELLANT", contract.appeal, claim_id)
    claim.verdict = VERDICT_GENUINE
    gl.message.sender_address = MERCHANT
    assert_error("ERR_NOT_APPELLANT", contract.appeal, claim_id)

    claim.verdict = VERDICT_DECEPTIVE
    contract.appeal(claim_id)
    assert claim.state == STATE_APPEALED
    assert claim.appellant == Address(MERCHANT)
    assert claim.appeal_bond_wei == contract.appeal_bond_wei
    assert claim.original_verdict == VERDICT_DECEPTIVE


def test_32_judge_appeal_overturn_threshold_and_short_circuit(monkeypatch):
    def appealed_case(observation_count=3):
        contract, ledger, _ = make_bond(monkeypatch)
        claim_id = prepare_claim(contract, ledger)
        claim = contract.claims[claim_id]
        claim.state = STATE_APPEALED
        claim.verdict = VERDICT_DECEPTIVE
        claim.confidence_bp = 8000
        claim.reasoning = "standing"
        claim.appellant = Address(MERCHANT)
        claim.appeal_bond_wei = contract.appeal_bond_wei
        claim.original_verdict = VERDICT_DECEPTIVE
        ledger.observations[1] = valid_observations(observation_count)
        return contract, claim_id, claim

    contract, claim_id, claim = appealed_case()
    gl._fake_llm_output = (
        '{"verdict":"GENUINE","confidence_bp":7500,'
        '"reasoning":"clear contrary evidence"}'
    )
    contract.judge_appeal(claim_id)
    assert claim.state == STATE_FINAL
    assert claim.verdict == VERDICT_GENUINE
    assert claim.confidence_bp == 7500

    low_contract, low_id, low_claim = appealed_case()
    gl._fake_llm_output = (
        '{"verdict":"GENUINE","confidence_bp":7499,'
        '"reasoning":"not confident enough"}'
    )
    low_contract.judge_appeal(low_id)
    assert low_claim.verdict == VERDICT_DECEPTIVE
    assert low_claim.confidence_bp == 8000
    assert low_claim.reasoning == "standing | appeal upheld"

    same_contract, same_id, same_claim = appealed_case()
    gl._fake_llm_output = (
        '{"verdict":"DECEPTIVE","confidence_bp":9000,'
        '"reasoning":"same conclusion"}'
    )
    same_contract.judge_appeal(same_id)
    assert same_claim.verdict == VERDICT_DECEPTIVE
    assert same_claim.confidence_bp == 8000
    assert same_claim.reasoning == "standing | appeal upheld"

    short_contract, short_id, short_claim = appealed_case(2)
    gl._last_prompt = ""
    short_contract.judge_appeal(short_id)
    assert short_claim.state == STATE_FINAL
    assert short_claim.verdict == VERDICT_DECEPTIVE
    assert short_claim.reasoning == "standing"
    assert gl._last_prompt == ""


def test_33_appeal_bond_settlement_and_cancel_lifecycle(monkeypatch):
    overturned, overturned_ledger, _ = make_bond(monkeypatch)
    overturned_id = prepare_claim(overturned, overturned_ledger)
    overturned_claim = overturned.claims[overturned_id]
    overturned_claim.state = STATE_FINAL
    overturned_claim.verdict = VERDICT_GENUINE
    overturned_claim.original_verdict = VERDICT_DECEPTIVE
    overturned_claim.appellant = Address(MERCHANT)
    overturned_claim.appeal_bond_wei = overturned.appeal_bond_wei
    overturned.settle(overturned_id)
    assert overturned.get_withdrawable(MERCHANT)["amount_wei"] == 250
    assert overturned.pool_wei == 50

    upheld, upheld_ledger, _ = make_bond(monkeypatch)
    upheld_id = prepare_claim(upheld, upheld_ledger)
    upheld_claim = upheld.claims[upheld_id]
    upheld_claim.state = STATE_FINAL
    upheld_claim.verdict = VERDICT_INSUFFICIENT
    upheld_claim.original_verdict = VERDICT_INSUFFICIENT
    upheld_claim.appellant = Address(BUYER)
    upheld_claim.appeal_bond_wei = upheld.appeal_bond_wei
    upheld.settle(upheld_id)
    assert upheld.get_withdrawable(BUYER)["amount_wei"] == 100
    assert upheld.pool_wei == 200

    cancellable, cancellable_ledger, _ = make_bond(monkeypatch)
    assert_error("ERR_NO_SALE", cancellable.cancel_sale, 999)
    register(cancellable)
    sale_id = announce(cancellable, cancellable_ledger)
    gl.message.sender_address = BOB
    assert_error("ERR_NOT_YOUR_SALE", cancellable.cancel_sale, sale_id)
    gl.message.sender_address = MERCHANT
    cancellable.cancel_sale(sale_id)
    assert cancellable.sales[sale_id].active is False
    assert_error("ERR_SALE_INACTIVE", cancellable.cancel_sale, sale_id)
    gl.message.sender_address = BUYER
    gl.message.value = cancellable.claim_deposit_wei
    assert_error("ERR_SALE_INACTIVE", cancellable.file_claim, sale_id)

    claimed, claimed_ledger, _ = make_bond(monkeypatch)
    claimed_id = prepare_claim(claimed, claimed_ledger)
    gl.message.sender_address = MERCHANT
    assert_error(
        "ERR_SALE_HAS_CLAIMS",
        claimed.cancel_sale,
        claimed.claims[claimed_id].sale_id,
    )

    exiting, exiting_ledger, _ = make_bond(monkeypatch)
    register(exiting)
    exiting_sale_id = announce(exiting, exiting_ledger)
    gl.message.sender_address = MERCHANT
    assert_error("ERR_ACTIVE_SALES", exiting.withdraw_bond)
    exiting.cancel_sale(exiting_sale_id)
    exiting.withdraw_bond()
    assert exiting.get_merchant(MERCHANT)["bond_wei"] == 0
    assert exiting.get_withdrawable(MERCHANT)["amount_wei"] == 10_000


def test_34_full_appealed_journey_bookkeeping(monkeypatch):
    contract, ledger, _ = make_bond(monkeypatch)
    claim_id = prepare_claim(contract, ledger)
    ledger.observations[1] = valid_observations(3)
    gl._fake_page = "Product is now listed for $90"
    gl._fake_llm_output = (
        '{"verdict":"DECEPTIVE","confidence_bp":8000,'
        '"reasoning":"the advertised reference is false"}'
    )
    contract.judge_claim(claim_id)
    claim = contract.claims[claim_id]
    assert claim.state == STATE_JUDGED

    gl.message.sender_address = MERCHANT
    gl.message.value = contract.appeal_bond_wei
    contract.appeal(claim_id)
    assert claim.state == STATE_APPEALED

    gl._fake_llm_output = (
        '{"verdict":"GENUINE","confidence_bp":7500,'
        '"reasoning":"the complete history supports the sale"}'
    )
    contract.judge_appeal(claim_id)
    assert claim.state == STATE_FINAL
    assert claim.original_verdict == VERDICT_DECEPTIVE
    assert claim.verdict == VERDICT_GENUINE

    gl.message.sender_address = BOB
    contract.settle(claim_id)
    assert claim.state == STATE_SETTLED
    assert contract.get_withdrawable(MERCHANT)["amount_wei"] == 250
    assert contract.get_withdrawable(BUYER)["amount_wei"] == 0
    assert contract.pool_wei == 50
    assert contract.get_merchant(MERCHANT)["bond_wei"] == 10_000
    assert contract.get_merchant(MERCHANT)["strikes"] == 0

    recorder = TransferRecorder(contract)
    monkeypatch.setattr(bond_mod, "_Recipient", recorder)
    gl.message.sender_address = MERCHANT
    contract.withdraw()
    assert recorder.calls == [
        {
            "recipient": Address(MERCHANT),
            "value": 250,
            "entry_at_emit": 0,
        }
    ]
