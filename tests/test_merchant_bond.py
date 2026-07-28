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
    gl.message.sender_address = OWNER
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
    gl.message.sender_address = OWNER
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


def register(contract, sender=MERCHANT, *, name="Merchant", value=10_000):
    gl.message.sender_address = sender
    gl.message.value = value
    contract.register_merchant(name)
    gl.message.value = 0


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
    gl.message.sender_address = merchant
    return contract.announce_sale(product_id, 20_000, 1_000, 600, currency)


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
    assert_error("ERR_NOT_MERCHANT", contract.announce_sale, 1, 0, 0, 0, "GBP")

    register(contract)
    gl.message.sender_address = MERCHANT
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
    gl.message.sender_address = MERCHANT
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

    # Second claim by same buyer fails with ERR_SALE_ALREADY_CLAIMED
    gl.message.sender_address = BUYER
    gl.message.value = 100
    assert_error("ERR_SALE_ALREADY_CLAIMED", contract.file_claim, sale_id)

    # Second claim by different buyer ALSO fails with ERR_SALE_ALREADY_CLAIMED
    gl.message.sender_address = BOB
    gl.message.value = 100
    assert_error("ERR_SALE_ALREADY_CLAIMED", contract.file_claim, sale_id)


def test_11_file_claim_coverage_guard(monkeypatch):
    contract, ledger, _ = make_bond(monkeypatch, min_bond=1_000)
    register(contract, value=1_000)
    # Merchant bond = 1,000 wei. Worst case liability per claim = 1,000 * 10% = 100 wei.
    # First sale + claim: reserved = 0, total needed = 100 <= 1000 => OK
    sale1 = announce(contract, ledger, product_id=1)
    claim1 = file_claim(contract, sale1, BUYER)
    assert claim1 == 1

    # Drain bond by repeatedly creating sales and claims up to 10
    for i in range(2, 11):
        ledger.products[i] = {"merchant": MERCHANT, "active": True}
        ledger.observations[i] = valid_observations(3)
        gl.message.sender_address = MERCHANT
        sale_i = contract.announce_sale(i, 20_000, 1_000, 600, "GBP")
        file_claim(contract, sale_i, BUYER)

    # 11th sale claim fails due to ERR_BOND_COVERAGE
    ledger.products[11] = {"merchant": MERCHANT, "active": True}
    ledger.observations[11] = valid_observations(3)
    gl.message.sender_address = MERCHANT
    sale11 = contract.announce_sale(11, 20_000, 1_000, 600, "GBP")
    gl.message.sender_address = BUYER
    gl.message.value = 100
    assert_error("ERR_BOND_COVERAGE", contract.file_claim, sale11)


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
    # 9. One second older than lower boundary (NOW - 2_592_000 - 1) is excluded
    # 10. Exact lower boundary (NOW - 2_592_000) is included
    # 11. Pre-sale observation included
    # 12. Wrong currency excluded
    # 13. ok=False excluded
    announced_at = NOW
    window_start = NOW - 2_592_000

    obs_list = [
        {"price_cents": 1000, "currency": "GBP", "observed_at": window_start - 1, "ok": True},
        {"price_cents": 2000, "currency": "GBP", "observed_at": window_start, "ok": True},
        {"price_cents": 3000, "currency": "USD", "observed_at": NOW - 1000, "ok": True}, # wrong currency
        {"price_cents": 4000, "currency": "GBP", "observed_at": NOW - 500, "ok": False}, # ok=false
        {"price_cents": 2500, "currency": "GBP", "observed_at": NOW, "ok": True}, # exact same second inside prefix
    ]

    filtered = bond_mod._filter_eligible_observations(obs_list, 5, announced_at, "GBP")
    assert len(filtered) == 2
    assert [o["p"] for o in filtered] == [2000, 2500]


def test_18_frozen_prefix_and_post_sale_isolation(monkeypatch):
    # 14. Same-second item inside frozen prefix included
    # 15. Same-second item appended after frozen cutoff excluded
    # 16. Post-sale items excluded
    # 17. > 50 post-sale observations cannot evict 3 pre-sale items
    contract, ledger, _ = make_bond(monkeypatch)
    register(contract)

    # 3 pre-sale observations at NOW
    obs_presale = [
        {"price_cents": 5000, "currency": "GBP", "observed_at": NOW - 100, "ok": True},
        {"price_cents": 4800, "currency": "GBP", "observed_at": NOW - 50, "ok": True},
        {"price_cents": 4900, "currency": "GBP", "observed_at": NOW, "ok": True},
    ]
    ledger.products[1] = {"merchant": MERCHANT, "active": True, "url": "https://shop.test/item"}
    ledger.observations[1] = list(obs_presale)

    sale_id = contract.announce_sale(1, 6000, 1000, 600, "GBP")
    assert contract.get_sale(sale_id)["observation_count_at_announcement"] == 3

    # Append 60 post-sale observations
    for i in range(60):
        ledger.observations[1].append(
            {"price_cents": 10000 + i, "currency": "GBP", "observed_at": NOW + 10 + i, "ok": True}
        )

    claim_id = file_claim(contract, sale_id)

    gl._fake_page = "Product page $60"
    gl._fake_llm_output = '{"verdict": "GENUINE", "confidence_bp": 9000, "reasoning": "valid"}'

    contract.judge_claim(claim_id)

    # Verify prompt received only pre-sale history (count 3, lowest 4800)
    assert "Total eligible pre-sale observations: 3" in gl._last_prompt
    assert "Observed 30-day lowest price: 4800 cents" in gl._last_prompt
    assert '"p":4800' in gl._last_prompt
    assert '"p":10000' not in gl._last_prompt


def test_19_insufficient_history_returns_err_insufficient_history(monkeypatch):
    contract, ledger, _ = make_bond(monkeypatch)
    register(contract)
    ledger.products[1] = {"merchant": MERCHANT, "active": True, "url": "https://shop.test/item"}
    ledger.observations[1] = valid_observations(2, "GBP") # only 2 observations

    gl.message.sender_address = MERCHANT
    assert_error("ERR_INSUFFICIENT_HISTORY", contract.announce_sale, 1, 6000, 1000, 600, "GBP")


def test_20_consensus_failure_leaves_claim_open(monkeypatch):
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


def test_21_upgradability_constructor_and_upgrade(monkeypatch):
    gl.message.sender_address = OWNER
    with pytest.raises(gl.vm.UserError) as exc_info:
        MerchantBond(ZERO, LEDGER, 1000, 100, 200, 300, 3)
    assert str(exc_info.value).startswith("ERR_BAD_UPGRADER")

    contract, _, _ = make_bond(monkeypatch)
    assert contract.is_upgrader(UPGRADER) is True
    assert contract.is_upgrader(BOB) is False

    contract.upgrade(b"new_bond_bytecode")
    assert gl.storage.Root.get().code.get() == bytearray(b"new_bond_bytecode")


def test_22_storage_and_dataclass_layout_snapshot():
    # Verify exact class annotations for Merchant, Sale, Claim
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
