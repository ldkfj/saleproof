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
