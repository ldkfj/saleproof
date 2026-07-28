---
date: 2026-07-26
description: "Full technical specification for SaleProof — discount-authenticity protocol on GenLayer: two contracts (PriceLedger + MerchantBond), appeals state machine, frontend, tests, phases."
tags:
  - spec
  - genlayer
  - saleproof
status: pending_dual_review
---

# SaleProof — Specification v1.0

> Status: PENDING DUAL REVIEW (Updated for Round A GenVM compatibility, evidence model, and Root upgradability).
> Author: Claude & Codex. Primary implementation worker: Antigravity.
> Workspace: `E:\Genlayer-Projects\saleproof`. Governance: `E:\Genlayer` (read-only).

## 0. One-liner

SaleProof is a discount-authenticity protocol on GenLayer: merchants stake a bond promising their sales are genuine; the chain itself accumulates price evidence over time by reading product pages, and when a buyer challenges a sale, validators read the live page, weigh it against the on-chain price history, and deliver a graduated AI verdict that pays out from the merchant's bond.

**Why it cannot exist without GenLayer:** the verdict requires (a) trustless reading of live product pages at multiple points in time and (b) a subjective judgment — "is this discount materially honest given the price history?" — that no single party (merchant, marketplace, buyer) can be trusted to make. Remove either the on-chain web reading or the consensus AI judgment and the product is meaningless.

## 1. Trust problem

"Fake sales" (inflating a reference price before a promotion, then advertising a large discount against it) are illegal in many jurisdictions (e.g., EU Omnibus Directive requires displaying the lowest price of the prior 30 days) but effectively unenforced. Buyers lose real money; honest merchants lose trust premium; marketplaces are conflicted (they profit from sale events). No single party should decide whether a discount was honest.

## 2. Actors

| Actor | Wallet | Actions | Money at stake |
|---|---|---|---|
| Merchant | own address | register + stake bond, list product URLs, announce sales, appeal verdicts | bond (slashable), appeal bond |
| Watcher | any address | trigger price snapshots for registered products | none (gas only); on-chain contribution counter |
| Buyer | any address | file a claim against a sale with an anti-spam deposit, appeal | claim deposit |
| Anyone | any address | read all state, verdicts, price histories | — |

## 3. Architecture — two cooperating contracts

Targeting contract-quality 5: multi-contract + event sourcing + appeals state machine + Root Slot Upgradability.

```
┌──────────────────┐   register_product / append   ┌──────────────────┐
│  MerchantBond    │ ────────────────────────────► │   PriceLedger    │
│  (core engine)   │                               │ (event-sourced   │
│  merchants, bonds│ ◄──────────────────────────── │  observation log)│
│  sales, claims,  │   get_history (view)          │  append-only,    │
│  verdicts, appeals│                              │  queryable by ANY│
└──────────────────┘                               │  contract        │
                                                   └──────────────────┘
```

- **PriceLedger** is an independent, append-only, publicly queryable log. Classified as `UPGRADABLE` via external Root upgrader.
- **MerchantBond** holds funds and runs the claim/appeal state machine. Classified as `UPGRADABLE` via external Root upgrader.

### 3.1 PriceLedger contract

Storage (GenLayer types — `TreeMap[u256, Product]`, `TreeMap[u256, DynArray[Observation]]`, scaled ints; u64 public IDs normalized via `_id_key`):

```python
products: TreeMap[u256, Product]        # product_id -> Product
product_count: u64
observations: TreeMap[u256, DynArray[Observation]]  # product_id -> append-only log
registrars: TreeMap[Address, bool]     # contracts/addresses allowed to register products
owner: Address
```

`Product`: `{ id: u64, url: str, merchant: Address, registered_at: u64, active: bool }`
`Observation`: `{ price_cents: u64, currency: str, observed_at: u64, watcher: Address, ok: bool, note: str }`

Methods:

| Method | Type | Guards (deterministic, UserError forms) |
|---|---|---|
| `__init__(upgrader_address, snapshot_cooldown_s, max_observations)` | ctor | upgrader non-zero (`ERR_BAD_UPGRADER`), registers in Root slot |
| `register_product(url, merchant)` | write | caller in `registrars`; url non-empty, http(s), length ≤ 500; no duplicate active url |
| `snapshot(product_id)` | write, nondet | product exists + active; cooldown: ≥ 300 s; observation cap 500 |
| `get_product(product_id)` | view | — |
| `get_observations(product_id)` | view | returns full log |
| `get_recent_observations(product_id, k)` | view | last k |
| `is_upgrader(addr)` | view | checks Root upgrader slot |
| `upgrade(new_code)` | write | Root slot upgrader execution |

### 3.2 MerchantBond contract

Storage:

```python
owner: Address
ledger: Address
merchants: TreeMap[Address, Merchant]
sales: TreeMap[u256, Sale];        sale_count: u64
claims: TreeMap[u256, Claim];      claim_count: u64
withdrawable: TreeMap[Address, u256]
pool_wei: u256
min_bond_wei: u256
claim_deposit_wei: u256
appeal_bond_wei: u256
appeal_window_s: u64
strike_limit: u64
```

`Sale`: `{ id, merchant, product_id, claimed_ref_price_cents, claimed_discount_bp, currency, announced_at, ends_at, observation_count_at_announcement, claim_id, active }`
`Claim`: `{ id, sale_id, buyer, deposit_wei, state, verdict, confidence_bp, reasoning, appellant, appeal_bond_wei, original_verdict, created_at, judged_at }`

### 3.3 Evidence Filtering & Canonical Claim Rules

1. **Pre-sale frozen evidence filtering:**
   - Look only at observations recorded prior to announcement: `observations[:observation_count_at_announcement]`.
   - Filter by exact currency (`sale.currency`), `ok == True`, valid price range (1..1,000,000,000), and 30-day window (`announced_at - 2,592,000 <= observed_at <= announced_at`).
   - Require at least 3 eligible observations at announcement (`ERR_INSUFFICIENT_HISTORY`).
   - Deterministic lowest price is computed over the full eligible set before capping prompt history to 50 items.
   - Appeal reuses the exact same frozen evidence snapshot.

2. **One canonical claim per sale:**
   - `Sale.claim_id` holds the single canonical claim ID.
   - Subsequent claims against a sale with `claim_id != 0` return `ERR_SALE_ALREADY_CLAIMED`.
   - One sale produces at most one adjudication, one slash, and one strike.

## 4. Upgradability Classification

Both contracts are classified as **`UPGRADABLE`**:
- External user-controlled wallet specified at deployment time as `upgrader_address`.
- Registered into GenVM `gl.storage.Root.get().upgraders`.
- Code upgraded via `@gl.public.write def upgrade(self, new_code: bytes)`.
