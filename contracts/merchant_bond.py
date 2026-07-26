# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
from dataclasses import dataclass
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

TRANSITIONS = {
    (STATE_OPEN, "judge"): STATE_JUDGED,
    (STATE_JUDGED, "appeal"): STATE_APPEALED,
    (STATE_APPEALED, "judge_appeal"): STATE_FINAL,
    (STATE_JUDGED, "finalize"): STATE_FINAL,
    (STATE_FINAL, "settle"): STATE_SETTLED,
}


# keep in sync with price_ledger.py
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
        if sender in self.merchants:
            raise Exception("ERR_ALREADY_MERCHANT")
        if not name or not name.strip() or len(name) > 100:
            raise Exception("ERR_NAME")
        value = gl.message.value
        if value < self.min_bond_wei:
            raise Exception("ERR_MIN_BOND")
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
        value = gl.message.value
        if value == 0:
            raise Exception("ERR_ZERO_VALUE")
        merchant = self.merchants[sender]
        merchant.bond_wei = u256(merchant.bond_wei + value)

    @gl.public.write
    def add_product(self, url: str) -> None:
        sender = _to_address(gl.message.sender_address)
        if sender not in self.merchants:
            raise Exception("ERR_NOT_MERCHANT")
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
                and _to_address(existing_sale.merchant) == merchant.addr
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
