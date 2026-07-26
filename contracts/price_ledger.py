# { "Depends": "py-genlayer:test" }
from genlayer import *


@allow_storage
@dataclass
class Product:
    id: u64
    url: str
    merchant: Address
    registered_at: u64
    active: bool


@allow_storage
@dataclass
class Observation:
    price_cents: u64
    currency: str
    observed_at: u64
    watcher: Address
    ok: bool
    note: str


class PriceLedger(gl.Contract):
    owner: Address
    products: TreeMap[u64, Product]
    product_count: u64
    observations: TreeMap[u64, DynArray[Observation]]
    registrars: TreeMap[Address, bool]
    snapshot_cooldown_s: u64
    max_observations: u64

    def __init__(
        self, snapshot_cooldown_s: u64 = 300, max_observations: u64 = 500
    ):
        self.owner = gl.message.sender_address
        self.snapshot_cooldown_s = snapshot_cooldown_s
        self.max_observations = max_observations
        self.product_count = 0
