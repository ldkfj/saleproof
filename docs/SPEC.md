---
date: 2026-07-26
description: "Full technical specification for SaleProof — discount-authenticity protocol on GenLayer: two contracts (PriceLedger + MerchantBond), appeals state machine, frontend, tests, phases."
tags:
  - spec
  - genlayer
  - saleproof
status: draft
---

# SaleProof — Specification v1.0

> Status: DRAFT — awaiting user approval (Step 2 of standard project flow).
> Author: Claude (supreme technical commander). Implementation workers: Antigravity (default), Codex (escalation).
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

Targeting contract-quality 5: multi-contract + event sourcing + appeals state machine, decided here at spec time.

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

- **PriceLedger** is an independent, append-only, publicly queryable log. Other contracts (not just MerchantBond) can consume its histories — satisfying the "registry/log contract other contracts can consume" criterion.
- **MerchantBond** holds funds and runs the claim/appeal state machine. It records the PriceLedger address at deploy time (constructor param).

### 3.1 PriceLedger contract

Storage (GenLayer types only — `TreeMap`, `DynArray`, scaled ints; never reassigned in `__init__`):

```python
products: TreeMap[u64, Product]        # product_id -> Product
product_count: u64
observations: TreeMap[u64, DynArray[Observation]]  # product_id -> append-only log
registrars: TreeMap[Address, bool]     # contracts/addresses allowed to register products
owner: Address
```

`Product`: `{ id: u64, url: str, merchant: Address, registered_at: u64, active: bool }`
`Observation`: `{ price_cents: u64, currency: str, observed_at: u64, watcher: Address, ok: bool, note: str }`

All money values are **integer cents** (`u64`). All percentages are **basis points** (`u64`). No `float` anywhere in public signatures or storage.

Methods:

| Method | Type | Guards (deterministic, before any nondet) |
|---|---|---|
| `register_product(url, merchant)` | write | caller in `registrars`; url non-empty, http(s), length ≤ 500; no duplicate active url |
| `snapshot(product_id)` | write, nondet | product exists + active; cooldown: ≥ N blocks/seconds since last observation (default 300 s); observation cap per product (default 500) |
| `get_product(product_id)` | view | — |
| `get_observations(product_id)` | view | returns full log |
| `get_recent_observations(product_id, k)` | view | last k |
| `add_registrar(addr)` / `remove_registrar(addr)` | write | owner only |

`snapshot` nondet flow:

1. Extract primitives to locals before the closure: `url: str`.
2. `leader_fn`: `page = gl.nondet.web.render(url, mode="text")` → `gl.nondet.exec_prompt(EXTRACT_PROMPT + truncated page)` asking for strict JSON `{"found": bool, "price_cents": int, "currency": "USD|EUR|VND|...", "note": str}`.
3. `validator_fn` (deterministic, zero LLM/nondet calls): parse JSON; require exact key set; `price_cents` in `[1, 10_000_000_00]`; `currency` in allow-list; `note` ≤ 200 chars; reject if payload > 1 KB. Semantic tolerance is handled by the equivalence check on `price_cents` (leader/validator independent fetches may differ; accept within ±2% or exact-equal fallback — final helper choice verified against current docs at implementation: prefer `gl.eq_principle.*` if it fits, else custom check inside `run_nondet_unsafe`).
4. Outside the nondet block: append `Observation`. If `found == false` → append with `ok=false` (dead-URL evidence is still evidence).

Prompt-injection defense: page text is untrusted; the extractor prompt instructs "output JSON only"; the deterministic validator enforces the shape/ranges regardless of what the page said — instructions embedded in page content cannot widen the decision space.

### 3.2 MerchantBond contract

Storage:

```python
ledger: Address                       # PriceLedger, set in __init__ (constructor param, real address)
merchants: TreeMap[Address, Merchant]
sales: TreeMap[u64, Sale];        sale_count: u64
claims: TreeMap[u64, Claim];      claim_count: u64
config: Config                        # min_bond_cents, claim_deposit_cents, appeal_bond_cents, windows, strike_limit
```

`Merchant`: `{ addr, name, bond_cents: u64, strikes: u8, active: bool, locked_until: u64, product_ids: DynArray[u64] }`
`Sale`: `{ id, merchant, product_id, claimed_ref_price_cents: u64, claimed_discount_bp: u64, announced_at, ends_at, status }`
`Claim`: `{ id, sale_id, buyer, deposit_cents, state, verdict, confidence_bp, reasoning: str, appeal_by: Address|0, created_at, judged_at }`

**Claim state machine** (explicit, enforced by a single transition table):

```
OPEN ──judge_claim──► JUDGED ──appeal (within window, bond paid)──► APPEALED ──judge_appeal──► FINAL
                        │                                                                        
                        └───settle (window expired, no appeal)──► FINAL ──settle──► SETTLED (payouts done)
```

Verdict enum (graduated — closed set, validator-enforced):

| Verdict | Meaning | Payout |
|---|---|---|
| `GENUINE` | discount honest vs history | buyer deposit → 50% merchant / 50% stays in protocol pool; no strike |
| `INFLATED_REFERENCE` | reference price inflated but discount partially real | buyer: deposit back + compensation = 10% of claimed_ref_price (cap: 5% of bond); strike +1 |
| `DECEPTIVE` | discount materially false | buyer: deposit back + compensation = 25% of claimed_ref_price (cap: 10% of bond); strike +1; at `strikes ≥ strike_limit` (3) → merchant deactivated, remaining bond escrowed for open claims then withdrawable by... (v1: frozen for claim window, then returned minus penalties — no full confiscation in v1) |
| `INSUFFICIENT_EVIDENCE` | page dead / history too thin | deposit returned in full; no strike; sale unaffected |

All payout arithmetic in integer cents with explicit caps; bond can never go below the sum owed to open claims (deterministic guard on `file_claim`: refuse new claims when uncovered).

Methods (all with deterministic guards listed in §5):

- `register_merchant(name)` — payable ≥ `min_bond_cents`
- `top_up_bond()` — payable
- `add_product(url)` — cross-contract write → `ledger.register_product(url, caller)`
- `announce_sale(product_id, claimed_ref_price_cents, claimed_discount_bp, duration_s)`
- `file_claim(sale_id)` — payable = `claim_deposit_cents`
- `judge_claim(claim_id)` — nondet (below)
- `appeal(claim_id)` — payable = `appeal_bond_cents`; only merchant (if verdict against them) or buyer (if `GENUINE`); once per claim
- `judge_appeal(claim_id)` — nondet, stricter persona + higher confidence threshold
- `settle(claim_id)` — pure deterministic payout per table; idempotent-guarded
- `withdraw_bond()` — merchant, only when no open claims/sales and after `locked_until`
- views: `get_merchant`, `get_sale`, `get_claim`, `list_open_claims`, `get_config`

`judge_claim` nondet flow:

1. Deterministic pre-work: read history via cross-contract **view** on `ledger` → serialize the observation list into a compact JSON **string**; copy sale fields into primitive locals. Only primitives (`str`, `int`) are captured by the closure — no storage objects (pickling rule).
2. `leader_fn`: `live = gl.nondet.web.render(product_url, mode="text")` (truncated); `gl.nondet.exec_prompt(JUDGE_PROMPT)` where JUDGE_PROMPT contains: role ("consumer-protection analyst"), the sale's claimed reference price + discount, the serialized on-chain history, the truncated live page text, the EU 30-day-lowest-price rule as the judging standard, and a strict output contract: JSON `{"verdict": one of 4, "confidence_bp": 0..10000, "reasoning": ≤ 400 chars}`.
3. `validator_fn` (deterministic): exact key set; verdict ∈ closed set; confidence in range; reasoning length cap; payload cap; reject any output that references instructions from page content (structural checks only — shape/range/set, no LLM). Consensus on the **semantic decision** = the verdict label (+ confidence bucket), not byte-identical reasoning.
4. Appeal rerun uses a second persona ("skeptical auditor — burden of proof on the claimant side that won round 1") and requires `confidence_bp ≥ 7500` to overturn; otherwise round-1 verdict stands.
5. Storage writes (verdict, state transition) happen strictly outside the nondet block.

## 4. Config defaults (constructor params, integer only)

| Param | Default |
|---|---|
| min_bond_cents | 200_00 (≈ 200 GEN-cents demo scale) |
| claim_deposit_cents | 5_00 |
| appeal_bond_cents | 20_00 |
| snapshot_cooldown_s | 300 |
| appeal_window_s | 3600 |
| strike_limit | 3 |
| history_min_observations | 3 (below this → `INSUFFICIENT_EVIDENCE` is the expected verdict; enforced in prompt, not hard-coded) |

Demo values are small so multi-wallet journeys are cheap; production values are a config redeploy away.

## 5. Deterministic guards (before any AI call)

- state validity for every transition (single transition table; invalid transition → revert with typed error)
- positive amounts; exact payable amounts for deposit/appeal
- authorization: merchant-only, buyer-only, owner-only paths
- duplicate prevention: one claim per (sale, buyer); one appeal per claim; settle idempotence
- bond coverage check before accepting a claim
- cooldown + caps on snapshots
- URL sanity (scheme, length) at registration

## 6. Edge cases (explicitly handled)

| Case | Behavior |
|---|---|
| Dead URL at snapshot | observation appended with `ok=false` |
| Dead URL at judgment | verdict `INSUFFICIENT_EVIDENCE` path; no slash |
| Malformed LLM JSON | validator rejects → consensus fails → tx error; claim stays `OPEN`, re-judgeable |
| Prompt injection in page text | deterministic shape/set/range validation; closed verdict set |
| History < min observations | `INSUFFICIENT_EVIDENCE` expected |
| Claim spam | deposit + one-claim-per-buyer-per-sale |
| Appeal spam | single appeal, appeal bond forfeited if not overturned |
| Bond exhaustion | new claims refused when uncovered |
| Merchant exit with pending claims | withdraw blocked until all claims FINAL/SETTLED + lock elapsed |
| MAJORITY_DISAGREE on judgment | claim remains OPEN; retry allowed after cooldown |
| Currency mismatch across observations | judge prompt instructed to treat mixed-currency history as weak evidence |

## 7. Frontend (React + Vite + TypeScript + genlayer-js)

Structure: `contracts/` (2 × .py), `frontend/`, `tests/`, `scripts/` (deploy helpers), `docs/`.

Pages / flows (full journey coverage):

1. **Merchants** — registry list (bond, strikes, status badges), register + top-up forms
2. **Product detail** — on-chain price-history chart (from `PriceLedger.get_observations`), "Trigger snapshot" button (watcher journey), snapshot cooldown countdown
3. **Sales** — announce-sale form (merchant), active sales with claimed discount vs history sparkline
4. **Claim flow** — file claim → live consensus progress (tx status polling) → verdict card showing label, confidence, and the AI's reasoning (actionable feedback, never just a spinner)
5. **Appeal** — window countdown, appeal form, round-2 verdict comparison
6. **Settlement** — payout breakdown, explorer links for every tx

UI state rules (per governance): update state only when tx is `FINALIZED` **and** result `SUCCESS`; render tx error + traceback summary otherwise. No hardcoded/simulated verdicts anywhere in production flow. Accessibility + motion rules per `Antigravity Knowledge Rules` (labels, focus-visible, reduced-motion, no `transition: all`).

Env: `frontend/.env` gets `VITE_LEDGER_ADDRESS` / `VITE_BOND_ADDRESS` **only after** real deployment shows FINALIZED + SUCCESS. Placeholder addresses are forbidden.

## 8. Testing

- **Unit (pure Python, no chain):** payout math, transition table, validator_fn parsers (feed adversarial payloads incl. injection strings, oversized JSON, wrong keys, out-of-range values)
- **Integration (GenLayer Studio / genlayer-test):** happy path per journey — register→snapshot×3→announce→claim→judge→settle; appeal path; insufficient-evidence path; guard reverts (duplicate claim, bad deposit, early withdraw)
- Contract header + `Depends` hash verified against the current Studio "new contract" template at implementation time (version-sensitive; do not trust this spec's memory)

## 9. Implementation phases (each = one Anti handoff, incremental commits mandatory)

| Phase | Scope | Key acceptance criteria |
|---|---|---|
| 1 | Repo scaffold, `contracts/price_ledger.py` storage + views + register/registrar logic, unit tests | ≥ 4 meaningful commits; tests green; no nondet yet |
| 2 | PriceLedger `snapshot` nondet flow + guards | deployed to Studio, snapshot tx FINALIZED+SUCCESS on a real URL; injection tests |
| 3 | MerchantBond storage, registration, sales, claims, payout math, transition table (no AI yet), unit tests | all guards revert correctly; math property tests |
| 4 | `judge_claim` + `judge_appeal` nondet flows + settle | full state machine walk in Studio; MAJORITY_DISAGREE handling shown |
| 5 | Frontend scaffold + all read flows + price chart | renders real chain data; no writes |
| 6 | Frontend write flows + consensus UX + polish | full journey clickable end-to-end on Studio |
| 7 | Testnet deploy, real-usage journeys (≥ 2 wallets), README + submission notes, demo video | explorer shows multi-wallet activity; docs match build exactly |

Escalation per governance: Anti 1 fail → Codex (2 attempts) → Claude implements directly.

## 10. Deployment order

1. Deploy `PriceLedger` → record address (FINALIZED + SUCCESS required)
2. Deploy `MerchantBond(ledger_address, config...)` → record address
3. `PriceLedger.add_registrar(MerchantBond)` tx
4. Wire frontend env with the two real addresses; verify a read + a write before calling it integrated

## 11. Out of scope (v1)

- Watcher monetary rewards (counter only)
- Multi-currency conversion (history is per-product; mixed currency = weak evidence)
- Marketplace-wide crawling; only merchant-registered URLs
- Full bond confiscation / claimant redistribution beyond per-claim compensation
- DAO governance of config

## 12. Submission-notes skeleton (kept in sync with build)

What it does / problem / why GenLayer (the one-liner in §0) / how to use step-by-step / contract files + addresses + explorer + live URL / roadmap line (separate, clearly future).

## Related

Governance sources this spec is bound by: [[AI Project Orchestration Rules]], [[Antigravity Knowledge Rules]], `E:\Genlayer\governance\AI-HIERARCHY.md`.
