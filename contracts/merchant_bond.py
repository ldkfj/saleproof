# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
from dataclasses import dataclass
import json
import time


STATE_OPEN = "OPEN"
STATE_JUDGED = "JUDGED"
STATE_APPEALED = "APPEALED"
STATE_FINAL = "FINAL"
STATE_SETTLED = "SETTLED"

VERDICT_GENUINE = "GENUINE"
VERDICT_INFLATED = "INFLATED_REFERENCE"
VERDICT_DECEPTIVE = "DECEPTIVE"
VERDICT_INSUFFICIENT = "INSUFFICIENT_EVIDENCE"
VERDICT_NONE = ""

ALLOWED_VERDICTS = {
    VERDICT_GENUINE,
    VERDICT_INFLATED,
    VERDICT_DECEPTIVE,
    VERDICT_INSUFFICIENT,
}

TRANSITIONS = {
    (STATE_OPEN, "judge"): STATE_JUDGED,
    (STATE_JUDGED, "appeal"): STATE_APPEALED,
    (STATE_APPEALED, "judge_appeal"): STATE_FINAL,
    (STATE_JUDGED, "finalize"): STATE_FINAL,
    (STATE_FINAL, "settle"): STATE_SETTLED,
}


# keep in sync with price_ledger.py
def _strip_fences(raw: str) -> str:
    """Deterministically remove one leading/trailing markdown code fence (``` or ```json) and surrounding whitespace. No other repair."""
    s = raw.strip()
    if s.startswith("```"):
        first_nl = s.find("\n")
        s = s[first_nl + 1:] if first_nl != -1 else ""
        if s.rstrip().endswith("```"):
            s = s.rstrip()[:-3]
    return s.strip()


def validate_verdict(raw: str) -> tuple[str, int, str]:
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > 2048:
        raise ValueError("ERR_VERDICT_INVALID: payload exceeds 2048 bytes")

    try:
        data = json.loads(_strip_fences(raw))
    except Exception as e:
        raise ValueError(f"ERR_VERDICT_INVALID: JSON parse error: {e}")

    if not isinstance(data, dict):
        raise ValueError("ERR_VERDICT_INVALID: expected JSON object")

    expected_keys = {"verdict", "confidence_bp", "reasoning"}
    if set(data.keys()) != expected_keys:
        raise ValueError(
            f"ERR_VERDICT_INVALID: keys must be exactly {expected_keys}"
        )

    verdict = data["verdict"]
    if type(verdict) is not str or verdict not in ALLOWED_VERDICTS:
        raise ValueError("ERR_VERDICT_INVALID: invalid verdict")

    confidence_bp = data["confidence_bp"]
    if type(confidence_bp) is not int:
        raise ValueError("ERR_VERDICT_INVALID: confidence_bp must be an int")
    if confidence_bp < 0 or confidence_bp > 10000:
        raise ValueError("ERR_VERDICT_INVALID: confidence_bp out of range")

    reasoning = data["reasoning"]
    if type(reasoning) is not str or len(reasoning) > 400:
        raise ValueError(
            "ERR_VERDICT_INVALID: reasoning must be str <= 400 chars"
        )

    return (verdict, confidence_bp, reasoning)


def _now() -> int:
    """Unix seconds; validator-synchronized by the GenVM runtime."""
    return int(time.time())


def _to_address(v) -> Address:
    """Normalize an address that Studio/clients may pass as Address, hex str, bytes, or int."""
    try:
        if isinstance(v, Address):
            return v
        if isinstance(v, bool):
            pass  # bool is an int subclass; fall through to the error
        elif isinstance(v, int):
            return Address(v.to_bytes(20, "big"))
        elif isinstance(v, (bytes, bytearray)):
            return Address(bytes(v))
        elif isinstance(v, str):
            return Address(v)
    except Exception:
        pass
    raise Exception("ERR_BAD_ADDRESS")


@allow_storage
@dataclass
class Merchant:
    addr: Address
    name: str
    bond_wei: u256
    strikes: u64
    active: bool
    joined_at: u64


@allow_storage
@dataclass
class Sale:
    id: u64
    merchant: Address
    product_id: u64
    claimed_ref_price_cents: u64
    claimed_discount_bp: u64
    announced_at: u64
    ends_at: u64
    active: bool


@allow_storage
@dataclass
class Claim:
    id: u64
    sale_id: u64
    buyer: Address
    deposit_wei: u256
    state: str
    verdict: str
    confidence_bp: u64
    reasoning: str
    appellant: Address
    created_at: u64
    judged_at: u64


def _transition(claim: Claim, action: str) -> None:
    next_state = TRANSITIONS.get((claim.state, action))
    if next_state is None:
        raise Exception("ERR_BAD_TRANSITION")
    claim.state = next_state


def compute_settlement(verdict: str, deposit_wei: int, bond_wei: int) -> dict:
    if verdict == VERDICT_GENUINE:
        merchant_wei = deposit_wei // 2
        return {
            "buyer_wei": 0,
            "merchant_wei": merchant_wei,
            "pool_wei": deposit_wei - merchant_wei,
            "bond_delta_wei": 0,
            "strike": False,
        }
    if verdict == VERDICT_INFLATED:
        compensation = bond_wei * 500 // 10000
        return {
            "buyer_wei": deposit_wei + compensation,
            "merchant_wei": 0,
            "pool_wei": 0,
            "bond_delta_wei": -compensation,
            "strike": True,
        }
    if verdict == VERDICT_DECEPTIVE:
        compensation = bond_wei * 1000 // 10000
        return {
            "buyer_wei": deposit_wei + compensation,
            "merchant_wei": 0,
            "pool_wei": 0,
            "bond_delta_wei": -compensation,
            "strike": True,
        }
    if verdict == VERDICT_INSUFFICIENT:
        return {
            "buyer_wei": deposit_wei,
            "merchant_wei": 0,
            "pool_wei": 0,
            "bond_delta_wei": 0,
            "strike": False,
        }
    raise ValueError("ERR_BAD_VERDICT")


@gl.evm.contract_interface
class _Recipient:
    class View:
        pass

    class Write:
        pass


class MerchantBond(gl.Contract):
    owner: Address
    ledger: Address
    merchants: TreeMap[Address, Merchant]
    sales: TreeMap[u64, Sale]
    sale_count: u64
    claims: TreeMap[u64, Claim]
    claim_count: u64
    claims_by_sale_buyer: TreeMap[str, u64]
    withdrawable: TreeMap[Address, u256]
    pool_wei: u256
    min_bond_wei: u256
    claim_deposit_wei: u256
    appeal_bond_wei: u256
    appeal_window_s: u64
    strike_limit: u64

    def __init__(
        self,
        ledger: Address,
        min_bond_wei: u256,
        claim_deposit_wei: u256,
        appeal_bond_wei: u256,
        appeal_window_s: u64,
        strike_limit: u64,
    ):
        self.owner = _to_address(gl.message.sender_address)
        self.ledger = _to_address(ledger)
        self.sale_count = u64(0)
        self.claim_count = u64(0)
        self.pool_wei = u256(0)
        self.min_bond_wei = min_bond_wei
        self.claim_deposit_wei = claim_deposit_wei
        self.appeal_bond_wei = appeal_bond_wei
        self.appeal_window_s = appeal_window_s
        self.strike_limit = strike_limit

    @gl.public.write.payable
    def register_merchant(self, name: str) -> None:
        sender = _to_address(gl.message.sender_address)
        existing = None
        if sender in self.merchants:
            existing = self.merchants[sender]
            if existing.active:
                raise Exception("ERR_ALREADY_MERCHANT")
            if existing.strikes >= self.strike_limit:
                raise Exception("ERR_BANNED")
        if not name or not name.strip() or len(name) > 100:
            raise Exception("ERR_NAME")
        value = gl.message.value
        if value < self.min_bond_wei:
            raise Exception("ERR_MIN_BOND")
        if existing is not None:
            existing.name = name
            existing.bond_wei = value
            existing.active = True
        else:
            self.merchants[sender] = Merchant(
                addr=sender,
                name=name,
                bond_wei=value,
                strikes=u64(0),
                active=True,
                joined_at=u64(_now()),
            )

    @gl.public.write.payable
    def top_up_bond(self) -> None:
        sender = _to_address(gl.message.sender_address)
        if sender not in self.merchants:
            raise Exception("ERR_NOT_MERCHANT")
        merchant = self.merchants[sender]
        if not merchant.active:
            raise Exception("ERR_MERCHANT_INACTIVE")
        value = gl.message.value
        if value == 0:
            raise Exception("ERR_ZERO_VALUE")
        merchant.bond_wei = u256(merchant.bond_wei + value)

    @gl.public.write
    def add_product(self, url: str) -> None:
        sender = _to_address(gl.message.sender_address)
        if sender not in self.merchants:
            raise Exception("ERR_NOT_MERCHANT")
        merchant = self.merchants[sender]
        if not merchant.active:
            raise Exception("ERR_MERCHANT_INACTIVE")
        if not url or not url.strip():
            raise Exception("ERR_URL_EMPTY")
        if not (url.startswith("http://") or url.startswith("https://")):
            raise Exception("ERR_URL_SCHEME")
        if len(url) > 500:
            raise Exception("ERR_URL_TOO_LONG")
        gl.get_contract_at(self.ledger).emit(on="finalized").register_product(
            url, sender
        )

    @gl.public.write
    def announce_sale(
        self,
        product_id: u64,
        claimed_ref_price_cents: u64,
        claimed_discount_bp: u64,
        duration_s: u64,
    ) -> u64:
        sender = _to_address(gl.message.sender_address)
        if sender not in self.merchants:
            raise Exception("ERR_NOT_MERCHANT")
        merchant = self.merchants[sender]
        if not merchant.active:
            raise Exception("ERR_MERCHANT_INACTIVE")
        if claimed_ref_price_cents < 1 or claimed_ref_price_cents > 1_000_000_000:
            raise Exception("ERR_PRICE")
        if claimed_discount_bp < 100 or claimed_discount_bp > 9500:
            raise Exception("ERR_DISCOUNT")
        if duration_s < 600 or duration_s > 2_592_000:
            raise Exception("ERR_DURATION")
        try:
            product = (
                gl.get_contract_at(self.ledger).view().get_product(product_id)
            )
        except Exception:
            raise Exception("ERR_NO_PRODUCT")
        if _to_address(product["merchant"]) != sender:
            raise Exception("ERR_NOT_YOUR_PRODUCT")
        if not product["active"]:
            raise Exception("ERR_PRODUCT_INACTIVE")

        self.sale_count = u64(self.sale_count + 1)
        sale_id = self.sale_count
        now = u64(_now())
        self.sales[sale_id] = Sale(
            id=sale_id,
            merchant=sender,
            product_id=product_id,
            claimed_ref_price_cents=claimed_ref_price_cents,
            claimed_discount_bp=claimed_discount_bp,
            announced_at=now,
            ends_at=u64(now + duration_s),
            active=True,
        )
        return sale_id

    @gl.public.write.payable
    def file_claim(self, sale_id: u64) -> u64:
        if sale_id not in self.sales:
            raise Exception("ERR_NO_SALE")
        sale = self.sales[sale_id]
        now = u64(_now())
        if now > sale.ends_at:
            raise Exception("ERR_SALE_CLOSED")

        buyer = _to_address(gl.message.sender_address)
        if buyer == _to_address(sale.merchant):
            raise Exception("ERR_SELF_CLAIM")
        value = gl.message.value
        if value != self.claim_deposit_wei:
            raise Exception("ERR_DEPOSIT")
        claim_key = f"{sale_id}:{str(buyer)}"
        if claim_key in self.claims_by_sale_buyer:
            raise Exception("ERR_DUPLICATE_CLAIM")

        merchant = self.merchants[_to_address(sale.merchant)]
        worst_case_liability = merchant.bond_wei * 1000 // 10000
        reserved_wei = u256(0)
        # Demo-scale O(n) scan is accepted for Phase 3; index it before production scale.
        for existing_claim_id in range(1, self.claim_count + 1):
            existing_claim = self.claims[existing_claim_id]
            existing_sale = self.sales[existing_claim.sale_id]
            if (
                existing_claim.state != STATE_SETTLED
                and _to_address(existing_sale.merchant)
                == _to_address(merchant.addr)
            ):
                reserved_wei = u256(reserved_wei + worst_case_liability)
        if merchant.bond_wei < reserved_wei + worst_case_liability:
            raise Exception("ERR_BOND_COVERAGE")

        self.claim_count = u64(self.claim_count + 1)
        claim_id = self.claim_count
        self.claims[claim_id] = Claim(
            id=claim_id,
            sale_id=sale_id,
            buyer=buyer,
            deposit_wei=value,
            state=STATE_OPEN,
            verdict=VERDICT_NONE,
            confidence_bp=u64(0),
            reasoning="",
            appellant=_to_address(
                "0x0000000000000000000000000000000000000000"
            ),
            created_at=now,
            judged_at=u64(0),
        )
        self.claims_by_sale_buyer[claim_key] = claim_id
        return claim_id

    @gl.public.write
    def finalize_unappealed(self, claim_id: u64) -> None:
        if claim_id not in self.claims:
            raise Exception("ERR_NO_CLAIM")
        claim = self.claims[claim_id]
        if claim.state != STATE_JUDGED:
            raise Exception("ERR_BAD_TRANSITION")
        now = u64(_now())
        if now <= claim.judged_at + self.appeal_window_s:
            raise Exception("ERR_APPEAL_WINDOW_OPEN")
        _transition(claim, "finalize")

    @gl.public.write
    def settle(self, claim_id: u64) -> None:
        if claim_id not in self.claims:
            raise Exception("ERR_BAD_TRANSITION")
        claim = self.claims[claim_id]
        if claim.state != STATE_FINAL:
            raise Exception("ERR_BAD_TRANSITION")

        sale = self.sales[claim.sale_id]
        merchant_addr = _to_address(sale.merchant)
        merchant = self.merchants[merchant_addr]
        result = compute_settlement(
            claim.verdict, claim.deposit_wei, merchant.bond_wei
        )
        new_bond = merchant.bond_wei + result["bond_delta_wei"]
        if new_bond < 0:
            raise Exception("ERR_INSOLVENT")

        buyer = _to_address(claim.buyer)
        self.withdrawable[buyer] = u256(
            self.withdrawable.get(buyer, u256(0)) + result["buyer_wei"]
        )
        self.withdrawable[merchant_addr] = u256(
            self.withdrawable.get(merchant_addr, u256(0))
            + result["merchant_wei"]
        )
        self.pool_wei = u256(self.pool_wei + result["pool_wei"])
        merchant.bond_wei = u256(new_bond)
        if result["strike"]:
            merchant.strikes = u64(merchant.strikes + 1)
            if merchant.strikes >= self.strike_limit:
                merchant.active = False
        _transition(claim, "settle")

    @gl.public.write
    def withdraw(self) -> None:
        sender = _to_address(gl.message.sender_address)
        amount = self.withdrawable.get(sender, u256(0))
        if amount == 0:
            raise Exception("ERR_NOTHING_TO_WITHDRAW")
        self.withdrawable[sender] = u256(0)
        _Recipient(sender).emit_transfer(value=u256(amount))

    @gl.public.write
    def withdraw_bond(self) -> None:
        sender = _to_address(gl.message.sender_address)
        if sender not in self.merchants:
            raise Exception("ERR_NOT_MERCHANT")
        merchant = self.merchants[sender]

        for claim_id in range(1, self.claim_count + 1):
            claim = self.claims[claim_id]
            sale = self.sales[claim.sale_id]
            if (
                _to_address(sale.merchant) == sender
                and claim.state != STATE_SETTLED
            ):
                raise Exception("ERR_OPEN_CLAIMS")

        now = u64(_now())
        for sale_id in range(1, self.sale_count + 1):
            sale = self.sales[sale_id]
            if (
                _to_address(sale.merchant) == sender
                and sale.active
                and now <= sale.ends_at
            ):
                raise Exception("ERR_ACTIVE_SALES")

        amount = merchant.bond_wei
        self.withdrawable[sender] = u256(
            self.withdrawable.get(sender, u256(0)) + amount
        )
        merchant.bond_wei = u256(0)
        merchant.active = False

    @gl.public.view
    def get_merchant(self, addr: Address) -> dict:
        addr = _to_address(addr)
        if addr not in self.merchants:
            raise Exception("ERR_NO_MERCHANT")
        merchant = self.merchants[addr]
        return {
            "addr": merchant.addr,
            "name": merchant.name,
            "bond_wei": merchant.bond_wei,
            "strikes": merchant.strikes,
            "active": merchant.active,
            "joined_at": merchant.joined_at,
        }

    @gl.public.view
    def get_sale(self, sale_id: u64) -> dict:
        if sale_id not in self.sales:
            raise Exception("ERR_NO_SALE")
        sale = self.sales[sale_id]
        return {
            "id": sale.id,
            "merchant": sale.merchant,
            "product_id": sale.product_id,
            "claimed_ref_price_cents": sale.claimed_ref_price_cents,
            "claimed_discount_bp": sale.claimed_discount_bp,
            "announced_at": sale.announced_at,
            "ends_at": sale.ends_at,
            "active": sale.active,
        }

    @gl.public.view
    def get_claim(self, claim_id: u64) -> dict:
        if claim_id not in self.claims:
            raise Exception("ERR_NO_CLAIM")
        claim = self.claims[claim_id]
        return {
            "id": claim.id,
            "sale_id": claim.sale_id,
            "buyer": claim.buyer,
            "deposit_wei": claim.deposit_wei,
            "state": claim.state,
            "verdict": claim.verdict,
            "confidence_bp": claim.confidence_bp,
            "reasoning": claim.reasoning,
            "appellant": claim.appellant,
            "created_at": claim.created_at,
            "judged_at": claim.judged_at,
        }

    @gl.public.view
    def get_config(self) -> dict:
        return {
            "owner": self.owner,
            "ledger": self.ledger,
            "min_bond_wei": self.min_bond_wei,
            "claim_deposit_wei": self.claim_deposit_wei,
            "appeal_bond_wei": self.appeal_bond_wei,
            "appeal_window_s": self.appeal_window_s,
            "strike_limit": self.strike_limit,
            "pool_wei": self.pool_wei,
        }

    @gl.public.view
    def get_withdrawable(self, addr: Address) -> dict:
        addr = _to_address(addr)
        return {
            "addr": addr,
            "amount_wei": self.withdrawable.get(addr, u256(0)),
        }

    @gl.public.view
    def get_counts(self) -> dict:
        return {
            "sale_count": self.sale_count,
            "claim_count": self.claim_count,
        }
