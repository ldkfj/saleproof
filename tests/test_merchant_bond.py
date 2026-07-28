import pytest
from genlayer import Address, gl

import contracts.merchant_bond as bond_mod
from contracts.merchant_bond import (
    Claim,
    MerchantBond,
    Sale,
    Merchant,
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
UPGRADER = "0x9999999999999999999999999999999999999999"
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
            raise gl.vm.UserError("ERR_NO_PRODUCT")
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
    gl.message.sender_address = Address(OWNER)
    gl.message.value = 0
    gl._fake_contract = None
    gl._fake_page = ""
    gl._fake_llm_output = ""
    gl._last_url = ""
    gl._last_mode = ""
    gl._last_prompt = ""
    gl._last_criteria = ""
    gl.storage.Root.reset()


def assert_error(code, fn, *args):
    with pytest.raises(gl.vm.UserError) as exc_info:
        fn(*args)
    assert str(exc_info.value).startswith(code)


def make_bond(monkeypatch, *, strike_limit=3, min_bond=10_000):
    clock = {"now": NOW}
    monkeypatch.setattr(bond_mod, "_now", lambda: clock["now"])
    fake_ledger = FakeLedger()
    gl._fake_contract = fake_ledger
    gl.message.sender_address = Address(OWNER)
    contract = MerchantBond(
        upgrader_address=UPGRADER,
        ledger=LEDGER,
        min_bond_wei=min_bond,
        claim_deposit_wei=100,
        appeal_bond_wei=200,
        appeal_window_s=300,
        strike_limit=strike_limit,
    )
    return contract, fake_ledger, clock


def deposit_credit(contract, sender, value):
    gl.message.sender_address = Address(sender)
    gl.message.value = value
    contract.deposit()
    gl.message.value = 0


def register(contract, sender=MERCHANT, *, name="Merchant", value=10_000):
    deposit_credit(contract, sender, value)
    gl.message.sender_address = Address(sender)
    contract.register_merchant(name, value)


def valid_observations(count=3, currency="GBP", start_time=NOW - 1000):
    return [
        {
            "price_cents": 10_000 + index * 100,
            "currency": currency,
            "observed_at": start_time + index * 60,
            "ok": True,
        }
        for index in range(count)
    ]


def announce(contract, ledger, *, merchant=MERCHANT, product_id=1, currency="GBP"):
    ledger.products[product_id] = {
        "merchant": merchant,
        "active": True,
        "url": "https://shop.test/item",
    }
    ledger.observations[product_id] = valid_observations(3, currency=currency)
    gl.message.sender_address = Address(merchant)
    return contract.announce_sale(product_id, 20_000, 1_000, 600, currency)


def file_claim(contract, sale_id=1, buyer=BUYER):
    deposit_credit(contract, buyer, contract.claim_deposit_wei)
    gl.message.sender_address = Address(buyer)
    claim_id = contract.file_claim(sale_id, contract.claim_deposit_wei)
    return claim_id


def appeal_claim(contract, claim_id, appellant, amount=None):
    amount = contract.appeal_bond_wei if amount is None else amount
    deposit_credit(contract, appellant, amount)
    gl.message.sender_address = Address(appellant)
    contract.appeal(claim_id, amount)


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


def prepare_claim(contract, ledger, buyer=BUYER, currency="GBP"):
    register(contract)
    sale_id = announce(contract, ledger, currency=currency)
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
    assert contract.is_upgrader(UPGRADER) is True


def test_2_registration_guards(monkeypatch):
    contract, _, _ = make_bond(monkeypatch)
    register(contract)
    merchant_before = contract.get_merchant(MERCHANT)

    deposit_credit(contract, MERCHANT, 777)
    assert_error("ERR_ALREADY_MERCHANT", contract.register_merchant, "", 0)
    assert contract.get_merchant(MERCHANT) == merchant_before
    assert contract.get_withdrawable(MERCHANT)["amount_wei"] == 777

    gl.message.sender_address = Address(BOB)
    assert_error("ERR_NAME", contract.register_merchant, "   ", 10_000)
    assert_error("ERR_NAME", contract.register_merchant, "x" * 101, 10_000)
    assert_error("ERR_MIN_BOND", contract.register_merchant, "Bob", 9_999)


def test_3_top_up_happy_path(monkeypatch):
    contract, _, _ = make_bond(monkeypatch)
    register(contract)

    deposit_credit(contract, MERCHANT, 250)
    contract.top_up_bond(250)
    assert contract.get_merchant(MERCHANT)["bond_wei"] == 10_250


def test_4_top_up_guards(monkeypatch):
    contract, _, _ = make_bond(monkeypatch)
    gl.message.sender_address = Address(BOB)
    assert_error("ERR_NOT_MERCHANT", contract.top_up_bond, 0)

    register(contract)
    gl.message.sender_address = Address(MERCHANT)
    assert_error("ERR_ZERO_VALUE", contract.top_up_bond, 0)


def test_5_add_product_guards_and_emit(monkeypatch):
    contract, ledger, _ = make_bond(monkeypatch)
    gl.message.sender_address = Address(BOB)
    assert_error("ERR_NOT_MERCHANT", contract.add_product, "")

    register(contract)
    gl.message.sender_address = Address(MERCHANT)
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
    gl.message.sender_address = Address(BOB)
    assert_error("ERR_NOT_MERCHANT", contract.announce_sale, 1, 0, 0, 0, "GBP")

    register(contract)
    gl.message.sender_address = Address(MERCHANT)
    for price in (0, 1_000_000_001):
        assert_error("ERR_PRICE", contract.announce_sale, 1, price, 1_000, 600, "GBP")
    for discount in (99, 9_501):
        assert_error(
            "ERR_DISCOUNT", contract.announce_sale, 1, 1_000, discount, 600, "GBP"
        )
    for duration in (599, 2_592_001):
        assert_error(
            "ERR_DURATION", contract.announce_sale, 1, 1_000, 1_000, duration, "GBP"
        )
    assert_error("ERR_CURRENCY", contract.announce_sale, 1, 1_000, 1_000, 600, "INVALID")


def test_7_announce_sale_product_guards(monkeypatch):
    contract, ledger, _ = make_bond(monkeypatch)
    register(contract)
    gl.message.sender_address = Address(MERCHANT)
    assert_error("ERR_NO_PRODUCT", contract.announce_sale, 1, 1_000, 1_000, 600, "GBP")

    ledger.products[1] = {"merchant": BOB, "active": True}
    assert_error(
        "ERR_NOT_YOUR_PRODUCT", contract.announce_sale, 1, 1_000, 1_000, 600, "GBP"
    )
    ledger.products[1] = {"merchant": MERCHANT, "active": False}
    assert_error(
        "ERR_PRODUCT_INACTIVE", contract.announce_sale, 1, 1_000, 1_000, 600, "GBP"
    )


def test_8_announce_sale_happy_path(monkeypatch):
    contract, ledger, _ = make_bond(monkeypatch)
    register(contract)
    sale_id = announce(contract, ledger, currency="GBP")

    assert sale_id == 1
    assert contract.get_sale(1) == {
        "id": 1,
        "merchant": Address(MERCHANT),
        "product_id": 1,
        "claimed_ref_price_cents": 20_000,
        "claimed_discount_bp": 1_000,
        "currency": "GBP",
        "announced_at": NOW,
        "ends_at": NOW + 600,
        "observation_count_at_announcement": 3,
        "claim_id": 0,
        "active": True,
    }


def test_9_file_claim_base_guards(monkeypatch):
    contract, ledger, clock = make_bond(monkeypatch)
    register(contract)
    deposit_credit(contract, BUYER, 100)
    assert_error("ERR_NO_SALE", contract.file_claim, 999, 100)
    assert contract.get_withdrawable(BUYER)["amount_wei"] == 100

    sale_id = announce(contract, ledger)
    clock["now"] = NOW + 601
    gl.message.sender_address = Address(BUYER)
    assert_error("ERR_SALE_CLOSED", contract.file_claim, sale_id, 100)
    assert contract.get_withdrawable(BUYER)["amount_wei"] == 100
    clock["now"] = NOW

    deposit_credit(contract, MERCHANT, 100)
    assert_error("ERR_SELF_CLAIM", contract.file_claim, sale_id, 100)
    assert contract.get_withdrawable(MERCHANT)["amount_wei"] == 100
    gl.message.sender_address = Address(BUYER)
    assert_error("ERR_DEPOSIT", contract.file_claim, sale_id, 99)
    assert contract.get_withdrawable(BUYER)["amount_wei"] == 100


def test_10_file_claim_happy_and_canonical_claim_prevention(monkeypatch):
    contract, ledger, _ = make_bond(monkeypatch)
    register(contract)
    sale_id = announce(contract, ledger)
    claim_id = file_claim(contract, sale_id)

    assert claim_id == 1
    claim = contract.get_claim(claim_id)
    assert claim["buyer"] == Address(BUYER)
    assert claim["deposit_wei"] == 100
    assert claim["state"] == STATE_OPEN
    assert contract.get_sale(sale_id)["claim_id"] == 1

    deposit_credit(contract, BUYER, 100)
    assert_error(
        "ERR_SALE_ALREADY_CLAIMED",
        contract.file_claim,
        sale_id,
        contract.claim_deposit_wei,
    )
    assert contract.get_withdrawable(BUYER)["amount_wei"] == 100

    deposit_credit(contract, BOB, 100)
    assert_error(
        "ERR_SALE_ALREADY_CLAIMED",
        contract.file_claim,
        sale_id,
        contract.claim_deposit_wei,
    )
    assert contract.get_withdrawable(BOB)["amount_wei"] == 100


def test_11_file_claim_coverage_guard(monkeypatch):
    contract, ledger, _ = make_bond(monkeypatch, min_bond=1_000)
    register(contract, value=1_000)

    sale1 = announce(contract, ledger, product_id=1)
    claim1 = file_claim(contract, sale1, BUYER)
    assert claim1 == 1

    for i in range(2, 11):
        ledger.products[i] = {"merchant": MERCHANT, "active": True}
        ledger.observations[i] = valid_observations(3)
        gl.message.sender_address = Address(MERCHANT)
        sale_i = contract.announce_sale(i, 20_000, 1_000, 600, "GBP")
        file_claim(contract, sale_i, BUYER)

    ledger.products[11] = {"merchant": MERCHANT, "active": True}
    ledger.observations[11] = valid_observations(3)
    gl.message.sender_address = Address(MERCHANT)
    sale11 = contract.announce_sale(11, 20_000, 1_000, 600, "GBP")
    deposit_credit(contract, BUYER, 100)
    assert_error(
        "ERR_BOND_COVERAGE",
        contract.file_claim,
        sale11,
        contract.claim_deposit_wei,
    )
    assert contract.get_withdrawable(BUYER)["amount_wei"] == 100


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
    with pytest.raises(gl.vm.UserError) as exc_info:
        compute_settlement("UNKNOWN", 100, 1_000)
    assert str(exc_info.value).startswith("ERR_BAD_VERDICT")


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


def test_17_evidence_filtering_boundaries_and_prefix():
    announced_at = NOW
    window_start = NOW - 2_592_000

    obs_list = [
        {"price_cents": 1000, "currency": "GBP", "observed_at": window_start - 1, "ok": True},
        {"price_cents": 2000, "currency": "GBP", "observed_at": window_start, "ok": True},
        {"price_cents": 3000, "currency": "USD", "observed_at": NOW - 1000, "ok": True},
        {"price_cents": 4000, "currency": "GBP", "observed_at": NOW - 500, "ok": False},
        {"price_cents": 2500, "currency": "GBP", "observed_at": NOW, "ok": True},
    ]

    filtered = bond_mod._filter_eligible_observations(obs_list, 5, announced_at, "GBP")
    assert len(filtered) == 2
    assert [o["p"] for o in filtered] == [2000, 2500]


def test_18_frozen_prefix_and_post_sale_isolation(monkeypatch):
    contract, ledger, _ = make_bond(monkeypatch)
    register(contract)

    obs_presale = [
        {"price_cents": 5000, "currency": "GBP", "observed_at": NOW - 100, "ok": True},
        {"price_cents": 4800, "currency": "GBP", "observed_at": NOW - 50, "ok": True},
        {"price_cents": 4900, "currency": "GBP", "observed_at": NOW, "ok": True},
    ]
    ledger.products[1] = {"merchant": MERCHANT, "active": True, "url": "https://shop.test/item"}
    ledger.observations[1] = list(obs_presale)

    sale_id = contract.announce_sale(1, 6000, 1000, 600, "GBP")
    assert contract.get_sale(sale_id)["observation_count_at_announcement"] == 3

    for i in range(60):
        ledger.observations[1].append(
            {"price_cents": 10000 + i, "currency": "GBP", "observed_at": NOW + 10 + i, "ok": True}
        )

    claim_id = file_claim(contract, sale_id)

    gl._fake_page = "Product page $60"
    gl._fake_llm_output = '{"verdict": "GENUINE", "confidence_bp": 9000, "reasoning": "valid"}'

    contract.judge_claim(claim_id)

    assert "Total eligible pre-sale observations: 3" in gl._last_prompt
    assert "Observed 30-day lowest price: 4800 cents" in gl._last_prompt
    assert '"p":4800' in gl._last_prompt
    assert '"p":10000' not in gl._last_prompt


def test_19_true_over_50_eligible_pre_sale_observations(monkeypatch):
    """BLOCKER 4: True >50 eligible pre-sale observations inside 30-day window."""
    contract, ledger, _ = make_bond(monkeypatch)
    register(contract)

    obs_51 = []
    obs_51.append({"price_cents": 1000, "currency": "GBP", "observed_at": NOW - 2500000, "ok": True})
    for i in range(1, 51):
        obs_51.append({"price_cents": 5000 + i, "currency": "GBP", "observed_at": NOW - 2000000 + i * 100, "ok": True})

    ledger.products[1] = {"merchant": MERCHANT, "active": True, "url": "https://shop.test/item51"}
    ledger.observations[1] = obs_51

    sale_id = contract.announce_sale(1, 6000, 1000, 600, "GBP")
    assert contract.get_sale(sale_id)["observation_count_at_announcement"] == 51

    claim_id = file_claim(contract, sale_id)

    gl._fake_page = "Item page text"
    gl._fake_llm_output = '{"verdict": "DECEPTIVE", "confidence_bp": 9500, "reasoning": "low price observed"}'

    contract.judge_claim(claim_id)

    prompt = gl._last_prompt
    assert "Total eligible pre-sale observations: 51" in prompt
    assert "Observed 30-day lowest price: 1000 cents" in prompt

    history_marker = "(capped to final 50 eligible items, chronological JSON, prices in cents): "
    start_idx = prompt.find(history_marker) + len(history_marker)
    end_idx = prompt.find("\nLIVE PAGE TEXT")
    history_str = prompt[start_idx:end_idx].strip()

    import json
    history_items = json.loads(history_str)
    assert len(history_items) == 50
    assert not any(item["p"] == 1000 for item in history_items)
    assert history_items[0]["p"] == 5001
    assert history_items[-1]["p"] == 5050


def test_20_insufficient_history_returns_err_insufficient_history(monkeypatch):
    contract, ledger, _ = make_bond(monkeypatch)
    register(contract)
    ledger.products[1] = {"merchant": MERCHANT, "active": True, "url": "https://shop.test/item"}
    ledger.observations[1] = valid_observations(2, "GBP")

    gl.message.sender_address = Address(MERCHANT)
    assert_error("ERR_INSUFFICIENT_HISTORY", contract.announce_sale, 1, 6000, 1000, 600, "GBP")


def test_21_consensus_failure_leaves_claim_open(monkeypatch):
    contract, ledger, _ = make_bond(monkeypatch)
    claim_id = prepare_claim(contract, ledger)

    def raise_majority_disagree(*args, **kwargs):
        raise gl.vm.UserError("MAJORITY_DISAGREE")

    monkeypatch.setattr(gl.eq_principle, "prompt_comparative", raise_majority_disagree)

    with pytest.raises(gl.vm.UserError) as exc_info:
        contract.judge_claim(claim_id)
    assert str(exc_info.value) == "MAJORITY_DISAGREE"

    claim = contract.get_claim(claim_id)
    assert claim["state"] == STATE_OPEN
    assert claim["confidence_bp"] == 0
    assert claim["verdict"] == ""
    assert claim["judged_at"] == 0


def test_22_upgradability_constructor_and_upgrade(monkeypatch):
    gl.message.sender_address = Address(OWNER)
    with pytest.raises(gl.vm.UserError) as exc_info:
        MerchantBond(ZERO, LEDGER, 1000, 100, 200, 300, 3)
    assert str(exc_info.value).startswith("ERR_BAD_UPGRADER")

    contract, _, _ = make_bond(monkeypatch)
    assert contract.is_upgrader(UPGRADER) is True
    assert contract.is_upgrader(BOB) is False
    register(contract)
    merchant_before = contract.get_merchant(MERCHANT)
    config_before = contract.get_config()

    gl.message.sender_address = Address(BOB)
    with pytest.raises(gl.vm.VMError):
        contract.upgrade(b"unauthorized_bytecode")

    gl.message.sender_address = Address(UPGRADER)
    contract.upgrade(b"new_bond_bytecode")
    assert gl.storage.Root.get().code._value == bytearray(b"new_bond_bytecode")
    assert contract.get_merchant(MERCHANT) == merchant_before
    assert contract.get_config() == config_before
    assert contract.is_upgrader(UPGRADER) is True


def test_23_storage_layout_snapshot_merchant_bond():
    merchant_annotations = list(Merchant.__annotations__.items())
    assert merchant_annotations == [
        ("addr", Address),
        ("name", str),
        ("bond_wei", bond_mod.u256),
        ("strikes", bond_mod.u64),
        ("active", bool),
        ("joined_at", bond_mod.u64),
    ]

    sale_annotations = list(Sale.__annotations__.items())
    assert sale_annotations == [
        ("id", bond_mod.u64),
        ("merchant", Address),
        ("product_id", bond_mod.u64),
        ("claimed_ref_price_cents", bond_mod.u64),
        ("claimed_discount_bp", bond_mod.u64),
        ("currency", str),
        ("announced_at", bond_mod.u64),
        ("ends_at", bond_mod.u64),
        ("observation_count_at_announcement", bond_mod.u64),
        ("claim_id", bond_mod.u64),
        ("active", bool),
    ]

    claim_annotations = list(Claim.__annotations__.items())
    assert claim_annotations == [
        ("id", bond_mod.u64),
        ("sale_id", bond_mod.u64),
        ("buyer", Address),
        ("deposit_wei", bond_mod.u256),
        ("state", str),
        ("verdict", str),
        ("confidence_bp", bond_mod.u64),
        ("reasoning", str),
        ("appellant", Address),
        ("appeal_bond_wei", bond_mod.u256),
        ("original_verdict", str),
        ("created_at", bond_mod.u64),
        ("judged_at", bond_mod.u64),
    ]

    bond_annotations = list(MerchantBond.__annotations__.items())
    assert bond_annotations == [
        ("owner", Address),
        ("ledger", Address),
        ("merchants", bond_mod.TreeMap[Address, Merchant]),
        ("sales", bond_mod.TreeMap[bond_mod.u256, Sale]),
        ("sale_count", bond_mod.u64),
        ("claims", bond_mod.TreeMap[bond_mod.u256, Claim]),
        ("claim_count", bond_mod.u64),
        ("withdrawable", bond_mod.TreeMap[Address, bond_mod.u256]),
        ("pool_wei", bond_mod.u256),
        ("min_bond_wei", bond_mod.u256),
        ("claim_deposit_wei", bond_mod.u256),
        ("appeal_bond_wei", bond_mod.u256),
        ("appeal_window_s", bond_mod.u64),
        ("strike_limit", bond_mod.u64),
    ]


def test_24_cancel_sale_lifecycle_and_guards(monkeypatch):
    contract, ledger, _ = make_bond(monkeypatch)
    register(contract)
    sale_id = announce(contract, ledger)

    gl.message.sender_address = Address(BOB)
    assert_error("ERR_NOT_YOUR_SALE", contract.cancel_sale, sale_id)

    gl.message.sender_address = Address(MERCHANT)
    contract.cancel_sale(sale_id)

    assert contract.get_sale(sale_id)["active"] is False
    assert_error("ERR_SALE_INACTIVE", contract.cancel_sale, sale_id)


def test_25_cancel_sale_blocked_if_claim_exists(monkeypatch):
    contract, ledger, _ = make_bond(monkeypatch)
    register(contract)
    sale_id = announce(contract, ledger)
    file_claim(contract, sale_id)

    gl.message.sender_address = Address(MERCHANT)
    assert_error("ERR_SALE_HAS_CLAIMS", contract.cancel_sale, sale_id)


def test_26_finalize_unappealed_window_open_and_closed(monkeypatch):
    contract, ledger, clock = make_bond(monkeypatch)
    claim_id = prepare_claim(contract, ledger)

    gl._fake_page = "Page text"
    gl._fake_llm_output = '{"verdict": "GENUINE", "confidence_bp": 9000, "reasoning": "genuine"}'
    contract.judge_claim(claim_id)

    assert_error("ERR_APPEAL_WINDOW_OPEN", contract.finalize_unappealed, claim_id)

    clock["now"] = NOW + 301
    contract.finalize_unappealed(claim_id)
    assert contract.get_claim(claim_id)["state"] == STATE_FINAL


def test_27_appeal_guards_and_appellant_permissions(monkeypatch):
    contract, ledger, _ = make_bond(monkeypatch)
    claim_id = prepare_claim(contract, ledger)

    deposit_credit(contract, BUYER, contract.appeal_bond_wei)
    assert_error(
        "ERR_BAD_TRANSITION",
        contract.appeal,
        claim_id,
        contract.appeal_bond_wei,
    )
    assert contract.get_withdrawable(BUYER)["amount_wei"] == 200

    gl._fake_page = "Page text"
    gl._fake_llm_output = '{"verdict": "GENUINE", "confidence_bp": 9000, "reasoning": "genuine"}'
    contract.judge_claim(claim_id)

    deposit_credit(contract, MERCHANT, contract.appeal_bond_wei)
    assert_error(
        "ERR_NOT_APPELLANT",
        contract.appeal,
        claim_id,
        contract.appeal_bond_wei,
    )
    assert contract.get_withdrawable(MERCHANT)["amount_wei"] == 200

    gl.message.sender_address = Address(BUYER)
    assert_error("ERR_APPEAL_BOND", contract.appeal, claim_id, 10)
    assert contract.get_withdrawable(BUYER)["amount_wei"] == 200

    contract.appeal(claim_id, contract.appeal_bond_wei)
    assert contract.get_claim(claim_id)["state"] == STATE_APPEALED
    assert contract.get_withdrawable(BUYER)["amount_wei"] == 0


def test_28_judge_appeal_consensus_outcomes(monkeypatch):
    """BLOCKER 1: Outcome-preserving appeal consensus tests."""
    contract, ledger, _ = make_bond(monkeypatch)
    claim_id = prepare_claim(contract, ledger)

    gl._fake_page = "Page text"
    gl._fake_llm_output = '{"verdict": "GENUINE", "confidence_bp": 8000, "reasoning": "genuine"}'
    contract.judge_claim(claim_id)

    appeal_claim(contract, claim_id, BUYER)
    assert contract.get_claim(claim_id)["state"] == STATE_APPEALED

    # Test 1: Re-judge with INFLATED_REFERENCE at 7499 -> should_overturn is False -> appeal upheld
    gl._fake_llm_output = '{"verdict": "INFLATED_REFERENCE", "confidence_bp": 7499, "reasoning": "borderline"}'
    contract.judge_appeal(claim_id)
    claim = contract.get_claim(claim_id)
    assert claim["state"] == STATE_FINAL
    assert claim["verdict"] == VERDICT_GENUINE
    assert "appeal upheld" in claim["reasoning"]

    # Re-setup for 7500 test using product_id=2
    sale_id2 = announce(contract, ledger, product_id=2)
    claim_id2 = file_claim(contract, sale_id2, buyer=BOB)
    gl._fake_llm_output = '{"verdict": "GENUINE", "confidence_bp": 8000, "reasoning": "genuine"}'
    contract.judge_claim(claim_id2)
    appeal_claim(contract, claim_id2, BOB)

    # Test 2: Re-judge with INFLATED_REFERENCE at 7500 -> should_overturn is True -> overturned
    gl._fake_llm_output = '{"verdict": "INFLATED_REFERENCE", "confidence_bp": 7500, "reasoning": "clear inflation"}'
    contract.judge_appeal(claim_id2)
    claim2 = contract.get_claim(claim_id2)
    assert claim2["state"] == STATE_FINAL
    assert claim2["verdict"] == VERDICT_INFLATED
    assert claim2["confidence_bp"] == 7500

    # Re-setup for 7501 test using product_id=3
    sale_id3 = announce(contract, ledger, product_id=3)
    claim_id3 = file_claim(contract, sale_id3, buyer="0x6666666666666666666666666666666666666666")
    gl._fake_llm_output = '{"verdict": "GENUINE", "confidence_bp": 8000, "reasoning": "genuine"}'
    contract.judge_claim(claim_id3)
    appeal_claim(
        contract,
        claim_id3,
        "0x6666666666666666666666666666666666666666",
    )

    # Test 3: Re-judge with DECEPTIVE at 7501 -> should_overturn is True -> overturned
    gl._fake_llm_output = '{"verdict": "DECEPTIVE", "confidence_bp": 7501, "reasoning": "deceptive price"}'
    contract.judge_appeal(claim_id3)
    claim3 = contract.get_claim(claim_id3)
    assert claim3["state"] == STATE_FINAL
    assert claim3["verdict"] == VERDICT_DECEPTIVE


@pytest.mark.parametrize(
    (
        "verdict",
        "expected_bond",
        "expected_strikes",
        "expected_buyer",
        "expected_merchant",
        "expected_pool",
    ),
    [
        (VERDICT_GENUINE, 10_000, 0, 0, 50, 50),
        (VERDICT_INFLATED, 9_500, 1, 600, 0, 0),
        (VERDICT_DECEPTIVE, 9_000, 1, 1_100, 0, 0),
        (VERDICT_INSUFFICIENT, 10_000, 0, 100, 0, 0),
    ],
)
def test_29_settle_all_verdicts_and_bookkeeping(
    monkeypatch,
    verdict,
    expected_bond,
    expected_strikes,
    expected_buyer,
    expected_merchant,
    expected_pool,
):
    contract, ledger, _ = make_bond(monkeypatch)
    claim_id = prepare_claim(contract, ledger)

    gl._fake_page = "Page"
    gl._fake_llm_output = (
        '{"verdict": "'
        + verdict
        + '", "confidence_bp": 9000, "reasoning": "settlement case"}'
    )
    contract.judge_claim(claim_id)

    monkeypatch.setattr(bond_mod, "_now", lambda: NOW + 400)
    contract.finalize_unappealed(claim_id)
    contract.settle(claim_id)

    assert contract.get_claim(claim_id)["state"] == STATE_SETTLED
    assert contract.get_merchant(MERCHANT)["strikes"] == expected_strikes
    assert contract.get_merchant(MERCHANT)["bond_wei"] == expected_bond
    assert contract.get_withdrawable(BUYER)["amount_wei"] == expected_buyer
    assert (
        contract.get_withdrawable(MERCHANT)["amount_wei"]
        == expected_merchant
    )
    assert contract.get_config()["pool_wei"] == expected_pool
    assert_error("ERR_BAD_TRANSITION", contract.settle, claim_id)


def test_30_withdraw_zero_before_transfer(monkeypatch):
    contract, ledger, _ = make_bond(monkeypatch)
    claim_id = prepare_claim(contract, ledger)
    gl._fake_page = "Page"
    gl._fake_llm_output = '{"verdict": "DECEPTIVE", "confidence_bp": 9000, "reasoning": "deceptive"}'
    contract.judge_claim(claim_id)
    monkeypatch.setattr(bond_mod, "_now", lambda: NOW + 400)
    contract.finalize_unappealed(claim_id)
    contract.settle(claim_id)

    gl.message.sender_address = Address(BUYER)
    assert contract.get_withdrawable(BUYER)["amount_wei"] == 1100

    recorder = TransferRecorder(contract)
    monkeypatch.setattr(bond_mod, "_Recipient", recorder)
    contract.withdraw()
    assert contract.get_withdrawable(BUYER)["amount_wei"] == 0
    assert recorder.calls == [
        {
            "recipient": Address(BUYER),
            "value": 1100,
            "entry_at_emit": 0,
        }
    ]

    assert_error("ERR_NOTHING_TO_WITHDRAW", contract.withdraw)


def test_31_withdraw_bond_guards_and_success(monkeypatch):
    contract, ledger, clock = make_bond(monkeypatch)
    register(contract)
    sale_id = announce(contract, ledger)

    gl.message.sender_address = Address(MERCHANT)
    assert_error("ERR_ACTIVE_SALES", contract.withdraw_bond)

    clock["now"] = NOW + 601
    contract.withdraw_bond()

    assert contract.get_merchant(MERCHANT)["active"] is False
    assert contract.get_merchant(MERCHANT)["bond_wei"] == 0
    assert contract.get_withdrawable(MERCHANT)["amount_wei"] == 10000


def test_32_struck_out_merchant_banned(monkeypatch):
    contract, ledger, clock = make_bond(monkeypatch, strike_limit=1)
    register(contract)
    sale_id = announce(contract, ledger)
    claim_id = file_claim(contract, sale_id)

    gl._fake_page = "Page"
    gl._fake_llm_output = '{"verdict": "DECEPTIVE", "confidence_bp": 9000, "reasoning": "deceptive"}'
    contract.judge_claim(claim_id)
    clock["now"] = NOW + 400
    contract.finalize_unappealed(claim_id)
    contract.settle(claim_id)

    assert contract.get_merchant(MERCHANT)["active"] is False
    assert contract.get_merchant(MERCHANT)["strikes"] == 1

    gl.message.sender_address = Address(MERCHANT)
    assert_error("ERR_MERCHANT_INACTIVE", contract.top_up_bond, 100)
    assert_error(
        "ERR_MERCHANT_INACTIVE",
        contract.add_product,
        "https://shop.test/banned",
    )
    assert_error(
        "ERR_MERCHANT_INACTIVE",
        contract.announce_sale,
        2,
        20_000,
        1_000,
        600,
        "GBP",
    )
    assert_error("ERR_BANNED", contract.register_merchant, "Re-try", 10_000)


def test_33_judge_appeal_guards_not_in_claims(monkeypatch):
    contract, _, _ = make_bond(monkeypatch)
    assert_error("ERR_NO_CLAIM", contract.judge_appeal, 999)


def test_34_judge_appeal_guards_wrong_state(monkeypatch):
    contract, ledger, _ = make_bond(monkeypatch)
    claim_id = prepare_claim(contract, ledger)
    # Claim is OPEN, not APPEALED -> ERR_BAD_TRANSITION
    assert_error("ERR_BAD_TRANSITION", contract.judge_appeal, claim_id)


def test_35_judge_appeal_insufficient_history_short_circuit(monkeypatch):
    contract, ledger, _ = make_bond(monkeypatch)
    claim_id = prepare_claim(contract, ledger)

    gl._fake_page = "Page"
    gl._fake_llm_output = '{"verdict": "GENUINE", "confidence_bp": 9000, "reasoning": "valid"}'
    contract.judge_claim(claim_id)

    appeal_claim(contract, claim_id, BUYER)

    # Empty observations before appeal judgment -> short circuits to state FINAL
    ledger.observations[1] = []
    contract.judge_appeal(claim_id)
    assert contract.get_claim(claim_id)["state"] == STATE_FINAL


def test_36_judge_appeal_consensus_failure_leaves_state_appealed(monkeypatch):
    contract, ledger, _ = make_bond(monkeypatch)
    claim_id = prepare_claim(contract, ledger)

    gl._fake_page = "Page"
    gl._fake_llm_output = '{"verdict": "GENUINE", "confidence_bp": 9000, "reasoning": "valid"}'
    contract.judge_claim(claim_id)

    appeal_claim(contract, claim_id, BUYER)

    def raise_majority_disagree(*args, **kwargs):
        raise gl.vm.UserError("MAJORITY_DISAGREE")

    monkeypatch.setattr(gl.vm, "run_nondet_unsafe", raise_majority_disagree)

    with pytest.raises(gl.vm.UserError) as exc_info:
        contract.judge_appeal(claim_id)
    assert str(exc_info.value) == "MAJORITY_DISAGREE"

    # State remains APPEALED
    assert contract.get_claim(claim_id)["state"] == STATE_APPEALED


def test_37_settle_overturned_appeal_refunds_appellant(monkeypatch):
    contract, ledger, clock = make_bond(monkeypatch)
    claim_id = prepare_claim(contract, ledger)

    gl._fake_page = "Page"
    gl._fake_llm_output = '{"verdict": "GENUINE", "confidence_bp": 8000, "reasoning": "genuine"}'
    contract.judge_claim(claim_id)

    # Buyer appeals
    appeal_claim(contract, claim_id, BUYER)

    # Overturned to DECEPTIVE (confidence 9000)
    gl._fake_llm_output = '{"verdict": "DECEPTIVE", "confidence_bp": 9000, "reasoning": "deceptive"}'
    contract.judge_appeal(claim_id)
    assert contract.get_claim(claim_id)["state"] == STATE_FINAL

    contract.settle(claim_id)
    assert contract.get_claim(claim_id)["state"] == STATE_SETTLED

    # Appellant (BUYER) refunded appeal bond (200) + deposit compensation (1100) = 1300
    assert contract.get_withdrawable(BUYER)["amount_wei"] == 1300


def test_38_settle_upheld_appeal_forfeits_appellant_bond_to_pool(monkeypatch):
    contract, ledger, clock = make_bond(monkeypatch)
    claim_id = prepare_claim(contract, ledger)

    gl._fake_page = "Page"
    gl._fake_llm_output = '{"verdict": "GENUINE", "confidence_bp": 8000, "reasoning": "genuine"}'
    contract.judge_claim(claim_id)

    # Buyer appeals
    appeal_claim(contract, claim_id, BUYER)

    # Upheld (same verdict GENUINE)
    gl._fake_llm_output = '{"verdict": "GENUINE", "confidence_bp": 8000, "reasoning": "genuine"}'
    contract.judge_appeal(claim_id)

    contract.settle(claim_id)

    # Pool receives appeal bond (200) + merchant share of deposit (50) = 250
    assert contract.get_config()["pool_wei"] == 250


def test_39_withdraw_bond_blocked_by_open_claim(monkeypatch):
    contract, ledger, _ = make_bond(monkeypatch)
    register(contract)
    sale_id = announce(contract, ledger)
    file_claim(contract, sale_id)

    gl.message.sender_address = Address(MERCHANT)
    assert_error("ERR_OPEN_CLAIMS", contract.withdraw_bond)


def test_40_voluntary_exit_and_reactivation(monkeypatch):
    contract, ledger, clock = make_bond(monkeypatch)
    register(contract)
    contract.merchants[Address(MERCHANT)].strikes = 1
    joined_at = contract.get_merchant(MERCHANT)["joined_at"]
    announce(contract, ledger)
    clock["now"] = NOW + 601

    gl.message.sender_address = Address(MERCHANT)
    contract.withdraw_bond()
    assert contract.get_merchant(MERCHANT)["active"] is False

    # Re-register merchant after exit
    deposit_credit(contract, MERCHANT, 12_345)
    contract.register_merchant("Re-joined Merchant", 12_345)
    merchant = contract.get_merchant(MERCHANT)
    assert merchant["active"] is True
    assert merchant["name"] == "Re-joined Merchant"
    assert merchant["bond_wei"] == 12_345
    assert merchant["strikes"] == 1
    assert merchant["joined_at"] == joined_at

    deposit_credit(contract, MERCHANT, 55)
    contract.top_up_bond(55)
    assert contract.get_merchant(MERCHANT)["bond_wei"] == 12_400
    contract.add_product("https://shop.test/reactivated")
    assert ledger.calls[-1]["args"] == (
        "https://shop.test/reactivated",
        Address(MERCHANT),
    )
    assert announce(contract, ledger, product_id=2) == 2


def test_41_validate_verdict_adversarial_suite():
    valid = validate_verdict('{"verdict": "GENUINE", "confidence_bp": 8500, "reasoning": "ok"}')
    assert valid == ("GENUINE", 8500, "ok")

    invalid_payloads = [
        '{"verdict": "INVALID_VERDICT", "confidence_bp": 8500, "reasoning": "ok"}',
        '{"verdict": "GENUINE", "confidence_bp": -1, "reasoning": "ok"}',
        '{"verdict": "GENUINE", "confidence_bp": 10001, "reasoning": "ok"}',
        '{"verdict": "GENUINE", "confidence_bp": 8500, "reasoning": "' + ('x' * 401) + '"}',
        '{"verdict": "GENUINE", "confidence_bp": "8500", "reasoning": "ok"}',
        '{"verdict": "GENUINE", "confidence_bp": true, "reasoning": "ok"}',
        '{"verdict": true, "confidence_bp": 8500, "reasoning": "ok"}',
        '{"verdict": "GENUINE", "confidence_bp": 8500}',
        '{"verdict": "GENUINE", "confidence_bp": 8500, "reasoning": "ok", "extra": 1}',
        'prefix {"verdict": "GENUINE", "confidence_bp": 8500, "reasoning": "ok"} suffix',
        "x" * 2049,
        'NOT_JSON',
        '[]',
    ]
    for payload in invalid_payloads:
        with pytest.raises(gl.vm.UserError) as exc_info:
            validate_verdict(payload)
        assert str(exc_info.value).startswith("ERR_VERDICT_INVALID")


def test_42_validate_verdict_fenced_json_variants():
    fenced = '```json\n{"verdict": "DECEPTIVE", "confidence_bp": 9200, "reasoning": "fenced text"}\n```'
    assert validate_verdict(fenced) == ("DECEPTIVE", 9200, "fenced text")


def test_43_appeal_window_closed_guard(monkeypatch):
    contract, ledger, clock = make_bond(monkeypatch)
    claim_id = prepare_claim(contract, ledger)

    gl._fake_page = "Page"
    gl._fake_llm_output = '{"verdict": "GENUINE", "confidence_bp": 9000, "reasoning": "valid"}'
    contract.judge_claim(claim_id)

    # Fast forward past appeal window (300 s)
    clock["now"] = NOW + 301
    deposit_credit(contract, BUYER, contract.appeal_bond_wei)
    assert_error(
        "ERR_APPEAL_WINDOW_CLOSED",
        contract.appeal,
        claim_id,
        contract.appeal_bond_wei,
    )
    assert contract.get_withdrawable(BUYER)["amount_wei"] == 200


def test_44_appeal_merchant_path_for_inflated_verdict(monkeypatch):
    contract, ledger, _ = make_bond(monkeypatch)
    claim_id = prepare_claim(contract, ledger)

    gl._fake_page = "Page"
    gl._fake_llm_output = '{"verdict": "INFLATED_REFERENCE", "confidence_bp": 9000, "reasoning": "inflated"}'
    contract.judge_claim(claim_id)

    # Merchant can appeal INFLATED_REFERENCE
    appeal_claim(contract, claim_id, MERCHANT)
    assert contract.get_claim(claim_id)["state"] == STATE_APPEALED


def test_45_judge_claim_insufficient_history_short_circuit(monkeypatch):
    contract, ledger, _ = make_bond(monkeypatch)
    register(contract)
    ledger.products[1] = {"merchant": MERCHANT, "active": True, "url": "https://shop.test/item"}
    # Seed 3 observations at announcement
    ledger.observations[1] = valid_observations(3, "GBP")

    sale_id = contract.announce_sale(1, 20000, 1000, 600, "GBP")
    claim_id = file_claim(contract, sale_id)

    # Remove observations before judging
    ledger.observations[1] = []

    contract.judge_claim(claim_id)
    claim = contract.get_claim(claim_id)
    assert claim["state"] == STATE_JUDGED
    assert claim["verdict"] == VERDICT_INSUFFICIENT
    assert claim["confidence_bp"] == 10000


def test_46_full_appealed_journey_bookkeeping(monkeypatch):
    contract, ledger, clock = make_bond(monkeypatch)
    register(contract, value=10000)
    sale_id = announce(contract, ledger)
    claim_id = file_claim(contract, sale_id, buyer=BUYER)

    # Initial judgment: GENUINE
    gl._fake_page = "Page"
    gl._fake_llm_output = '{"verdict": "GENUINE", "confidence_bp": 8000, "reasoning": "genuine"}'
    contract.judge_claim(claim_id)

    # Buyer appeals with 200 wei appeal bond
    appeal_claim(contract, claim_id, BUYER)

    # Re-judge appeal: DECEPTIVE (confidence 8500 >= 7500 -> should_overturn=True)
    gl._fake_llm_output = '{"verdict": "DECEPTIVE", "confidence_bp": 8500, "reasoning": "deceptive reference"}'
    contract.judge_appeal(claim_id)

    assert contract.get_claim(claim_id)["state"] == STATE_FINAL
    assert contract.get_claim(claim_id)["verdict"] == VERDICT_DECEPTIVE

    # Settle
    contract.settle(claim_id)

    # Merchant: 1 strike, bond reduced by 1000 (10% of 10000) -> 9000
    assert contract.get_merchant(MERCHANT)["strikes"] == 1
    assert contract.get_merchant(MERCHANT)["bond_wei"] == 9000

    # Buyer: deposit (100) + compensation (1000) + appeal bond refund (200) = 1300 wei withdrawable
    assert contract.get_withdrawable(BUYER)["amount_wei"] == 1300


def test_47_merchant_address_normalization_at_public_boundaries(monkeypatch):
    contract, _, _ = make_bond(monkeypatch)
    gl.message.sender_address = int(MERCHANT, 16)
    gl.message.value = 10_000
    contract.deposit()
    gl.message.value = 0
    contract.register_merchant("Integer Sender", 10_000)

    merchant = contract.get_merchant(int(MERCHANT, 16))
    assert merchant["addr"] == Address(MERCHANT)
    assert contract.is_upgrader(int(UPGRADER, 16)) is True

    gl.message.value = 25
    contract.deposit()
    gl.message.value = 0
    contract.top_up_bond(25)
    assert contract.get_merchant(MERCHANT)["bond_wei"] == 10_025

    for bad in (True, None, 3.14, b"short", "0x1234", 2 ** 200):
        with pytest.raises(gl.vm.UserError) as exc_info:
            contract.get_merchant(bad)
        assert str(exc_info.value).startswith("ERR_BAD_ADDRESS")


def test_48_appeal_outcome_helper_boundaries():
    assert (
        bond_mod._appeal_should_overturn(
            VERDICT_INFLATED, 7499, VERDICT_GENUINE
        )
        is False
    )
    assert (
        bond_mod._appeal_should_overturn(
            VERDICT_INFLATED, 7500, VERDICT_GENUINE
        )
        is True
    )
    assert (
        bond_mod._appeal_should_overturn(
            VERDICT_DECEPTIVE, 7501, VERDICT_GENUINE
        )
        is True
    )
    assert (
        bond_mod._appeal_should_overturn(
            VERDICT_GENUINE, 10_000, VERDICT_GENUINE
        )
        is False
    )


def test_49_prepaid_deposit_is_additive_zero_safe_and_wallet_isolated(
    monkeypatch,
):
    contract, _, _ = make_bond(monkeypatch)

    deposit_credit(contract, BUYER, 40)
    deposit_credit(contract, BUYER, 60)
    deposit_credit(contract, BUYER, 0)
    deposit_credit(contract, BOB, 25)

    assert contract.get_withdrawable(BUYER)["amount_wei"] == 100
    assert contract.get_withdrawable(BOB)["amount_wei"] == 25
    assert contract.get_withdrawable(MERCHANT)["amount_wei"] == 0


def test_50_all_credit_consuming_actions_reject_insufficient_credit(
    monkeypatch,
):
    contract, ledger, _ = make_bond(monkeypatch)

    gl.message.sender_address = Address(MERCHANT)
    assert_error(
        "ERR_INSUFFICIENT_CREDIT",
        contract.register_merchant,
        "Merchant",
        10_000,
    )
    assert contract.get_withdrawable(MERCHANT)["amount_wei"] == 0

    register(contract)
    merchant_before = contract.get_merchant(MERCHANT)
    assert_error("ERR_INSUFFICIENT_CREDIT", contract.top_up_bond, 1)
    assert contract.get_merchant(MERCHANT) == merchant_before

    sale_id = announce(contract, ledger)
    gl.message.sender_address = Address(BUYER)
    assert_error(
        "ERR_INSUFFICIENT_CREDIT",
        contract.file_claim,
        sale_id,
        contract.claim_deposit_wei,
    )
    assert contract.get_counts()["claim_count"] == 0
    assert contract.get_sale(sale_id)["claim_id"] == 0

    claim_id = file_claim(contract, sale_id)
    gl._fake_page = "Page text"
    gl._fake_llm_output = (
        '{"verdict": "GENUINE", "confidence_bp": 9000, '
        '"reasoning": "genuine"}'
    )
    contract.judge_claim(claim_id)
    gl.message.sender_address = Address(BUYER)
    assert_error(
        "ERR_INSUFFICIENT_CREDIT",
        contract.appeal,
        claim_id,
        contract.appeal_bond_wei,
    )
    assert contract.get_claim(claim_id)["state"] == STATE_JUDGED
    assert contract.get_withdrawable(BUYER)["amount_wei"] == 0


def test_51_successes_consume_exact_credit_and_leave_excess(monkeypatch):
    contract, ledger, _ = make_bond(monkeypatch)

    deposit_credit(contract, MERCHANT, 10_100)
    contract.register_merchant("Merchant", 10_000)
    assert contract.get_withdrawable(MERCHANT)["amount_wei"] == 100

    deposit_credit(contract, MERCHANT, 50)
    contract.top_up_bond(125)
    assert contract.get_merchant(MERCHANT)["bond_wei"] == 10_125
    assert contract.get_withdrawable(MERCHANT)["amount_wei"] == 25

    sale_id = announce(contract, ledger)
    deposit_credit(contract, BUYER, 150)
    contract.file_claim(sale_id, contract.claim_deposit_wei)
    assert contract.get_withdrawable(BUYER)["amount_wei"] == 50

    gl._fake_page = "Page text"
    gl._fake_llm_output = (
        '{"verdict": "GENUINE", "confidence_bp": 9000, '
        '"reasoning": "genuine"}'
    )
    contract.judge_claim(1)
    deposit_credit(contract, BUYER, 225)
    contract.appeal(1, contract.appeal_bond_wei)
    assert contract.get_withdrawable(BUYER)["amount_wei"] == 75
    assert contract.get_claim(1)["appeal_bond_wei"] == 200


def test_52_unused_prepaid_credit_is_withdrawable(monkeypatch):
    contract, _, _ = make_bond(monkeypatch)
    deposit_credit(contract, BUYER, 321)

    recorder = TransferRecorder(contract)
    monkeypatch.setattr(bond_mod, "_Recipient", recorder)
    contract.withdraw()

    assert contract.get_withdrawable(BUYER)["amount_wei"] == 0
    assert recorder.calls == [
        {
            "recipient": Address(BUYER),
            "value": 321,
            "entry_at_emit": 0,
        }
    ]


def test_53_internal_custody_accounting_is_conserved(monkeypatch):
    contract, ledger, _ = make_bond(monkeypatch)
    initial_total = 12_750

    deposit_credit(contract, MERCHANT, 12_000)
    deposit_credit(contract, BUYER, 500)
    deposit_credit(contract, BOB, 250)
    gl.message.sender_address = Address(MERCHANT)
    contract.register_merchant("Merchant", 10_000)

    assert (
        contract.get_merchant(MERCHANT)["bond_wei"]
        + contract.get_withdrawable(MERCHANT)["amount_wei"]
        + contract.get_withdrawable(BUYER)["amount_wei"]
        + contract.get_withdrawable(BOB)["amount_wei"]
        + contract.get_config()["pool_wei"]
        == initial_total
    )

    sale_id = announce(contract, ledger)
    gl.message.sender_address = Address(BUYER)
    claim_id = contract.file_claim(sale_id, contract.claim_deposit_wei)
    gl._fake_page = "Page text"
    gl._fake_llm_output = (
        '{"verdict": "GENUINE", "confidence_bp": 9000, '
        '"reasoning": "genuine"}'
    )
    contract.judge_claim(claim_id)
    contract.appeal(claim_id, contract.appeal_bond_wei)

    claim = contract.get_claim(claim_id)
    assert (
        contract.get_merchant(MERCHANT)["bond_wei"]
        + contract.get_withdrawable(MERCHANT)["amount_wei"]
        + contract.get_withdrawable(BUYER)["amount_wei"]
        + contract.get_withdrawable(BOB)["amount_wei"]
        + claim["deposit_wei"]
        + claim["appeal_bond_wei"]
        + contract.get_config()["pool_wei"]
        == initial_total
    )

    contract.judge_appeal(claim_id)
    contract.settle(claim_id)

    assert (
        contract.get_merchant(MERCHANT)["bond_wei"]
        + contract.get_withdrawable(MERCHANT)["amount_wei"]
        + contract.get_withdrawable(BUYER)["amount_wei"]
        + contract.get_withdrawable(BOB)["amount_wei"]
        + contract.get_config()["pool_wei"]
        == initial_total
    )
