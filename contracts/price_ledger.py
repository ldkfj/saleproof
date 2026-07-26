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

    @gl.public.write
    def add_registrar(self, addr: Address):
        if gl.message.sender_address != self.owner:
            raise Exception("ERR_NOT_OWNER")
        if self.registrars.get(addr, False):
            raise Exception("ERR_ALREADY_REGISTRAR")
        self.registrars[addr] = True

    @gl.public.write
    def remove_registrar(self, addr: Address):
        if gl.message.sender_address != self.owner:
            raise Exception("ERR_NOT_OWNER")
        if not self.registrars.get(addr, False):
            raise Exception("ERR_NOT_REGISTRAR")
        self.registrars[addr] = False

    @gl.public.write
    def register_product(self, url: str, merchant: Address) -> u64:
        if not self.registrars.get(gl.message.sender_address, False):
            raise Exception("ERR_NOT_REGISTRAR")
        if not url or not url.strip():
            raise Exception("ERR_URL_EMPTY")
        if not (url.startswith("http://") or url.startswith("https://")):
            raise Exception("ERR_URL_SCHEME")
        if len(url) > 500:
            raise Exception("ERR_URL_TOO_LONG")

        for p_id in range(1, self.product_count + 1):
            if p_id in self.products:
                p = self.products[p_id]
                if p.active and p.url == url:
                    raise Exception("ERR_URL_DUPLICATE")

        self.product_count += 1
        product_id = self.product_count
        now = gl.message.timestamp
        self.products[product_id] = Product(
            id=product_id,
            url=url,
            merchant=merchant,
            registered_at=now,
            active=True,
        )
        self.observations[product_id] = DynArray()
        return product_id

    @gl.public.write
    def deactivate_product(self, product_id: u64):
        if not self.registrars.get(gl.message.sender_address, False):
            raise Exception("ERR_NOT_REGISTRAR")
        if product_id not in self.products or product_id == 0 or product_id > self.product_count:
            raise Exception("ERR_NO_PRODUCT")
        p = self.products[product_id]
        if not p.active:
            raise Exception("ERR_INACTIVE")
        p.active = False

    @gl.public.view
    def get_product(self, product_id: u64) -> dict:
        if product_id not in self.products or product_id == 0 or product_id > self.product_count:
            raise Exception("ERR_NO_PRODUCT")
        p = self.products[product_id]
        return {
            "id": p.id,
            "url": p.url,
            "merchant": p.merchant,
            "registered_at": p.registered_at,
            "active": p.active,
        }

    @gl.public.view
    def get_observations(self, product_id: u64) -> list[dict]:
        if product_id not in self.products or product_id == 0 or product_id > self.product_count:
            raise Exception("ERR_NO_PRODUCT")
        obs_list = self.observations.get(product_id, [])
        return [
            {
                "price_cents": o.price_cents,
                "currency": o.currency,
                "observed_at": o.observed_at,
                "watcher": o.watcher,
                "ok": o.ok,
                "note": o.note,
            }
            for o in obs_list
        ]

    @gl.public.view
    def get_recent_observations(self, product_id: u64, k: u64) -> list[dict]:
        all_obs = self.get_observations(product_id)
        if k == 0:
            return []
        if k >= len(all_obs):
            return all_obs
        return all_obs[-k:]


    @gl.public.view
    def get_product_count(self) -> u64:
        return self.product_count

    @gl.public.view
    def is_registrar(self, addr: Address) -> bool:
        return bool(self.registrars.get(addr, False))


# snapshot() arrives in Phase 2 (nondet flow) — see docs/SPEC.md §3.1


