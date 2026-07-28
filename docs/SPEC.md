---
date: 2026-07-26
description: "Technical specification for SaleProof, a two-contract discount-authenticity protocol on GenLayer."
tags:
  - spec
  - genlayer
  - saleproof
status: pending_corrected_deployment_and_dual_review
---

# SaleProof — Specification v1.1

> Status: local correction complete only after its recorded checks pass. A corrected Studionet deployment, live evidence package, Codex approval, and anonymous co-review AI approval are still required.
>
> Technical authority: Codex. Implementation history: Antigravity, with Codex takeover after the second correction attempt failed review.
>
> Workspace: `E:\Genlayer-Projects\saleproof`. Current release network: Studionet only.

## 0. Product statement

SaleProof lets a merchant stake a native-GEN bond behind an advertised sale. Independent watchers build an on-chain price history from live product pages. If a buyer challenges the sale, GenLayer validators compare the frozen on-chain evidence with a fresh page read and reach a bounded verdict that drives settlement from the bond.

The trust problem is structural:

- a merchant can inflate a reference price;
- a buyer can file a self-serving complaint;
- a marketplace can benefit from promotion volume;
- a single scraper or AI operator can alter evidence or judgment.

GenLayer is required because the contract itself performs validator-replicated web access and subjective adjudication, while deterministic contract logic constrains inputs, state transitions, and money movement. The caller never supplies the authenticated verdict or payout tier.

This is a Studionet demonstration. Studionet GEN is test value, not production money.

## 1. Actors and authority

| Actor | Authority | Value at risk |
|---|---|---|
| Upgrader wallet | Root-slot code replacement for both contracts | Operational key responsibility |
| PriceLedger registrar | Register and deactivate products | None |
| Merchant | Deposit reusable credit, stake/top up bond, register products, announce/cancel sales, appeal adverse verdicts, exit when safe | Prepaid credit, merchant bond, and appeal bond |
| Buyer | Deposit reusable credit, file one canonical claim for a sale, appeal a non-adverse result, withdraw unused/awarded value | Prepaid credit, claim deposit, and possible appeal bond |
| Watcher | Trigger a public price snapshot | Transaction cost only |
| Any caller | Trigger judgment, finalization, settlement, and read public views | Transaction cost only |

Wallet addresses are normalized through `_to_address` at public boundaries and when message senders are stored, compared, or used as map keys. Supported calldata representations are `Address`, 20-byte values, 40-hex-character strings with `0x`, and non-boolean integers fitting 160 bits. Invalid representations fail with `ERR_BAD_ADDRESS`.

### 1.1 Trust-boundary matrix

The table below is the release authority model. “Sender” means
`gl.message.sender_address` normalized with `_to_address` before it is stored,
compared, or used as a `TreeMap` key.

| Actor / trigger | Entry point | Identity and gate | Result determiner | Override or privilege | State / value consequence |
|---|---|---|---|---|---|
| Deployment sender | both constructors | Sender becomes normalized `owner`; constructor calldata supplies a separately normalized, nonzero Root upgrader | Deterministic constructor guards | Establishes initial owner and Root authority only | Initializes configuration and empty counters; does not create products, sales, or claims |
| Registered Root upgrader | `upgrade` on either contract | GenVM locked Root code slot checks the caller against `Root.upgraders`; contract owner status is irrelevant | Exact `new_code` bytes submitted by the authorized upgrader | Sole code-replacement authority; no in-contract method can add an upgrader | Replaces executable code while retaining storage bytes; no automatic schema migration or on-chain rollback history |
| PriceLedger owner | `add_registrar`, `remove_registrar` | Sender must equal the normalized constructor owner | Deterministic membership guards | May change registrar membership, but cannot write products, observations, bonds, sales, claims, or verdicts directly | Flips one registrar-map entry |
| Authorized PriceLedger registrar (normally MerchantBond for registration) | `register_product`, `deactivate_product` | PriceLedger normalizes the caller and requires its address in `registrars`; the `merchant` argument to registration is independently normalized | URL/product guards and registrar membership | May create/deactivate product records only; MerchantBond exposes only its merchant-triggered registration cross-call | Creates a product owned by the supplied merchant or marks an existing product inactive |
| Any wallet | `deposit` | Normalized sender is the only credit beneficiary; incoming value cannot name a third party | No business validation; zero is a no-op and every positive value is credited | May fund only its own reusable credit | Increases native contract balance and the same sender's `withdrawable` credit by exactly the same amount |
| Merchant wallet | `register_merchant`, `top_up_bond`, `withdraw_bond` | Sender is the merchant key; active/banned/open-claim/live-sale guards apply; registration/top-up consume only the sender's prepaid credit | Deterministic lifecycle, amount, and credit guards | May manage only its own merchant record and bond; reactivation preserves lifetime strikes and `joined_at` | Reclassifies sender credit into a bond, tops up that bond, or exits and routes the eligible bond back to sender credit |
| Merchant wallet | `add_product`, `announce_sale`, `cancel_sale` | Product addition and sale announcement require an active merchant; cancellation requires sale ownership but intentionally remains available after merchant deactivation | Deterministic product, history, currency, duration, ownership, and state guards; PriceLedger supplies frozen history | Cannot manufacture observations or cancel another merchant’s sale | Registers a linked product, freezes the observation boundary in a sale, or deactivates an unclaimed sale |
| Watcher wallet | `snapshot` | Any sender may trigger; normalized sender is stored only after deterministic product/active/cap/cooldown guards pass | Validator-replicated web render, strict extraction, and equivalence principle | Chooses when to request an eligible snapshot, not the returned price/currency/note | Appends one bounded observation and records the watcher address |
| Buyer wallet | `file_claim` | Sender becomes normalized buyer; self-claim, sale state, one-claim, exact deposit amount, merchant bond-coverage, and prepaid-credit guards apply | Deterministic guards; no native value is attached to the guarded operation | May open one canonical claim on another merchant's active sale | Reclassifies the exact deposit from buyer credit, links claim to sale, and freezes buyer identity |
| Eligible merchant or buyer | `appeal` | Normalized sender must be the losing-side merchant/buyer encoded by the standing verdict; exact appeal amount, window, and prepaid credit are required | Deterministic role, state, time, amount, and credit guards; no native value is attached | May request one second judgment; cannot choose the appeal outcome | Reclassifies the appeal bond from appellant credit and records appellant/original verdict |
| Any wallet | `judge_claim`, `judge_appeal` | Caller identity is not trusted or stored; only claim state selects eligibility | Frozen on-chain history plus fresh validator web access; strict payload validation and consensus determine verdict/confidence | Caller can trigger consensus but cannot supply or override a verdict | Advances `OPEN -> JUDGED` or `APPEALED -> FINAL`; appeal overturn requires the independently recomputed 7,500-bp rule |
| Any wallet | `finalize_unappealed`, `settle` | Caller identity is irrelevant; state and appeal-window guards are authoritative | `_now()` and deterministic state transition / `compute_settlement` arithmetic | Can advance a mature claim only; cannot redirect proceeds | Advances `JUDGED -> FINAL -> SETTLED`, applies bond slash/strike, and credits fixed pull-payment balances/pool |
| Balance owner | `withdraw` | Normalized sender indexes only its own `withdrawable` entry | Stored balance and zero-before-transfer order | Cannot select another beneficiary | Zeroes that sender’s ledger entry before native-value transfer |
| Read caller | all public views | Address arguments are normalized where present; no sender privilege | Finalized contract state | None | No storage or value change |

Any-caller lifecycle methods expose liveness, not judgment authority. The Root
upgrader is the only code override; neither owner nor registrar can directly
alter merchant bonds, frozen sale evidence, claim verdicts, or settlement
amounts.

## 2. Architecture

```text
Merchant / buyer / caller
           |
           v
  +-------------------+       product registration       +-------------------+
  |   MerchantBond    | --------------------------------> |    PriceLedger    |
  | bond + sale +     |                                   | append-only price |
  | claim + appeal +  | <-------------------------------- | evidence          |
  | pull settlement   |       synchronous public views    |                   |
  +-------------------+                                   +-------------------+
           |                                                        |
           +---------------- Root-slot upgrader --------------------+
```

Both contracts use the same exact runner header:

```python
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
```

`genvm-lint` currently emits informational warning `I200` for a newer runner.
This release intentionally retains the reviewed hash above: current official
upgradability documentation uses it and the live Studionet schema endpoint
accepts both contracts with it. A runner change is a runtime/source change and
must receive its own review, schema probe, rehearsal, and dual approval rather
than being silently bundled into this release.

Collections use `TreeMap` and `DynArray`; ordinary numeric storage is `u64` or `u256`. Map IDs use `u256` keys, while public IDs remain `u64`. Storage collections are declared as fields and are not reassigned in constructors.

Transaction time comes only from `_now()`, implemented as integer Unix seconds
derived from validator-pinned `datetime.now(timezone.utc)`. No contract reads
time from `gl.message`.

## 3. PriceLedger

### 3.1 Storage

```python
owner: Address
products: TreeMap[u256, Product]
product_count: u64
observations: TreeMap[u256, DynArray[Observation]]
registrars: TreeMap[Address, bool]
snapshot_cooldown_s: u64
max_observations: u64
```

`Product` contains `id`, `url`, `merchant`, `registered_at`, and `active`.

`Observation` contains `price_cents`, `currency`, `observed_at`, `watcher`, `ok`, and `note`.

Observation arrays are created only with
`self.observations.get_or_insert_default(product_id)`. User code never constructs
`DynArray()` or `TreeMap()`. A product with no observation entry returns `[]`.

### 3.2 Public API

| Method | Mode | Required behavior |
|---|---|---|
| `__init__(upgrader_address, snapshot_cooldown_s=300, max_observations=500)` | constructor | Reject zero upgrader; set owner; register the upgrader in Root |
| `is_upgrader(addr)` | view | Read Root upgrader membership |
| `add_registrar(addr)` / `remove_registrar(addr)` | write | Owner-only registrar administration |
| `register_product(url, merchant)` | write | Registrar-only; validate URL; reject duplicate active URL |
| `deactivate_product(product_id)` | write | Registrar-only; product must exist and be active |
| `get_product`, `get_observations`, `get_recent_observations` | view | Return canonical evidence state |
| `get_config()` | view | Return owner, cooldown, and observation cap |
| `get_product_count`, `is_registrar` | view | Return current registry state |
| `snapshot(product_id)` | nondeterministic write | Append one validator-agreed observation |
| `upgrade(new_code)` | write | Root-authorized code-slot replacement |

### 3.3 Snapshot flow

Every deterministic guard runs before web access:

1. product exists (`ERR_NO_PRODUCT`);
2. product is active (`ERR_INACTIVE`);
3. observation count is below the configured cap (`ERR_OBS_CAP`);
4. cooldown has elapsed (`ERR_COOLDOWN`).

Only primitive locals and module-level helpers/constants are captured by the
nondeterministic closure. The leader renders the URL as text, truncates the page
to 6,000 characters, and requests strict JSON price extraction. Comparative
consensus returns only after validator re-execution. Storage is written only
after that call returns.

`validate_extraction` is the deterministic firewall:

- at most 1,024 UTF-8 bytes;
- exactly one JSON object and the exact keys `found`, `price_cents`, `currency`, `note`;
- exact Python types, excluding boolean-as-integer;
- price `1..1_000_000_000` when found and `0` when not found;
- currency in `USD`, `EUR`, `GBP`, `JPY`, `VND`;
- note length at most 200 characters;
- one optional surrounding Markdown fence is stripped; there is no regex repair or fallback extraction.

A dead or unreadable page may produce a valid `found=false` observation with
`ok=false`; failure evidence remains append-only.

## 4. MerchantBond

### 4.1 Storage

```python
owner: Address
ledger: Address
merchants: TreeMap[Address, Merchant]
sales: TreeMap[u256, Sale]
sale_count: u64
claims: TreeMap[u256, Claim]
claim_count: u64
withdrawable: TreeMap[Address, u256]
pool_wei: u256
min_bond_wei: u256
claim_deposit_wei: u256
appeal_bond_wei: u256
appeal_window_s: u64
strike_limit: u64
```

`Merchant` records address, name, bond, lifetime strikes, active state, and
original join time.

`Sale` records merchant, product, claimed price/discount/currency, window,
frozen observation count, one canonical claim ID, and active state.

`Claim` records buyer deposit, state, verdict, confidence, reasoning, appellant,
appeal bond, original verdict, and timestamps.

### 4.2 Public API

| Method | Mode | Required behavior |
|---|---|---|
| `__init__(upgrader, ledger, min_bond, claim_deposit, appeal_bond, appeal_window, strike_limit)` | constructor | Reject zero upgrader, normalize ledger, store config, and register Root upgrader |
| `deposit()` | payable | Always credit positive incoming GEN to the normalized sender's reusable `withdrawable` balance; zero is a no-op |
| `register_merchant(name, bond_wei)` | write | New registration or voluntary-exit reactivation funded from sender credit; banned merchants cannot return |
| `top_up_bond(amount_wei)` | write | Active merchant only; positive amount funded from sender credit |
| `add_product(url)` | write | Active merchant only; finalized async call to PriceLedger |
| `announce_sale(product_id, reference, discount_bp, duration_s, currency)` | write | Active owner of active product; at least three eligible observations |
| `cancel_sale(sale_id)` | write | Sale merchant only; active and unclaimed |
| `file_claim(sale_id, deposit_wei)` | write | Exact configured amount funded from sender credit; non-merchant buyer; open sale; canonical first claim; bond coverage |
| `judge_claim(claim_id)` | nondeterministic write | `OPEN -> JUDGED` |
| `appeal(claim_id, appeal_bond_wei)` | write | Eligible losing party, exact configured amount funded from sender credit, inside window |
| `judge_appeal(claim_id)` | nondeterministic write | `APPEALED -> FINAL` |
| `finalize_unappealed(claim_id)` | write | Window expired; `JUDGED -> FINAL` |
| `settle(claim_id)` | write | Deterministic pull-payment bookkeeping; `FINAL -> SETTLED` |
| `withdraw()` | write | Zero ledger entry first, then emit transfer |
| `withdraw_bond()` | write | No unsettled claim and no still-open active sale |
| views | view | Counts, merchant, sale, claim, config, withdrawable, upgrader |
| `upgrade(new_code)` | write | Root-authorized code-slot replacement |

Inactive merchants cannot top up, register products, or announce sales.
Strike-limit deactivation is a permanent ban. A merchant who exited voluntarily
may re-register with the minimum bond; their strikes and `joined_at` remain,
while name and current bond are updated.

Native GEN receipt is deliberately separated from guarded business logic.
Studionet debits a sender at submission and credits the target at activation;
an execution error rolls back contract storage but does not reverse that native
credit. Therefore `deposit()` contains no business guard that can reject
positive value. Registration, top-up, claim, and appeal are nonpayable: they run
the existing business guards first, then require the sender's reusable credit
to cover the requested exact amount
(`ERR_INSUFFICIENT_CREDIT`), debit that credit, and perform the success
mutation. If a business operation fails, it carries no attached GEN and all
prepaid credit remains withdrawable.

Clients must persist the network, MerchantBond address, wallet, action, amount,
and submission stage before asking the wallet to send a deposit. A positive
deposit is submitted at most once per persisted intent. A missing transaction
hash, a terminal result other than `FINALIZED + SUCCESS`, or a successful
receipt whose finalized credit readback is still short is fail-closed: the
client retains the intent and never automatically submits another deposit.
Only a finalized successful deposit with sufficient finalized
`get_withdrawable` credit may advance to the nonpayable business call.

Raw value-only transfers and value attached to nonpayable methods are not a
supported protocol entry path. The pinned runner/schema rejects the documented
`__receive__` special method, so clients must send GEN only through `deposit()`.
Unsolicited raw transfers cannot create a user credit and are excluded from the
protocol-liability equality below.

### 4.3 Evidence binding

At sale announcement, the contract freezes `observation_count_at_announcement`.
Judgment and appeal consider only observations in that prefix which:

- have `ok is True`;
- use the sale's exact currency;
- have integer price in `1..1_000_000_000`;
- were recorded no later than announcement and within the preceding 30 days.

At least three eligible observations are required to announce. The deterministic
30-day minimum uses the complete eligible set. Only the final 50 chronological
eligible items enter the prompt, so prompt capping cannot discard the minimum
used by contract context.

The product URL and frozen sale fields come from contract state. A new snapshot
after announcement cannot alter evidence for that sale. Each sale accepts one
canonical claim, preventing duplicate adjudication, slash, or strike.

### 4.4 Judgment and appeal consensus

`judge_claim` has a deterministic insufficient-history branch. Otherwise the
closure captures primitives, renders the live URL, and produces the strict
verdict payload:

```json
{"verdict": "GENUINE|INFLATED_REFERENCE|DECEPTIVE|INSUFFICIENT_EVIDENCE",
 "confidence_bp": 0,
 "reasoning": "maximum 400 characters"}
```

`validate_verdict` enforces a 2,048-byte cap, exact key set, closed verdict set,
exact non-boolean integer confidence `0..10000`, and reasoning length. Storage
writes occur only after consensus returns.

Appeal uses a skeptical second prompt and a custom validator. The leader's
payload must include an exact boolean `should_overturn`. The validator:

1. validates the leader verdict payload;
2. recomputes `should_overturn = verdict != standing_verdict and confidence_bp >= 7500`;
3. independently re-runs the same evidence-bound judgment;
4. validates and recomputes the validator outcome;
5. requires exact verdict and exact outcome-region agreement;
6. permits at most 1,500 basis points of confidence difference.

This prevents two validators from agreeing loosely while crossing the 7,500-bp
settlement boundary. Values such as `7499/true` and integer `1` in place of
`true` are rejected.

### 4.5 State machine

```text
OPEN --judge_claim--> JUDGED --appeal--> APPEALED --judge_appeal--> FINAL
                         |
                         +--finalize_unappealed after window--------------> FINAL

FINAL --settle--> SETTLED
```

`TRANSITIONS` is the single transition table. Invalid/replayed transitions fail.
A consensus failure happens before state writes, leaving the claim retryable in
its prior state.

### 4.6 Economic rules

All value uses native GEN wei in `u256`; percentages use integer basis points.

| Final verdict | Buyer ledger | Merchant ledger | Pool | Bond / strike |
|---|---:|---:|---:|---|
| `GENUINE` | 0 | deposit // 2 | deposit remainder | no slash, no strike |
| `INFLATED_REFERENCE` | deposit + 5% of current bond | 0 | 0 | 5% slash, +1 strike |
| `DECEPTIVE` | deposit + 10% of current bond | 0 | 0 | 10% slash, +1 strike |
| `INSUFFICIENT_EVIDENCE` | deposit refund | 0 | 0 | no slash, no strike |

An upheld appeal bond enters the pool; an overturned appeal bond becomes
withdrawable by the appellant. `compute_settlement` is pure and settlement
checks solvency before mutation. New claims reserve worst-case liability against
the merchant's current bond. Pull payments make settlement independent of a
recipient callback; `withdraw()` zeroes the claimable balance before transfer.

For supported protocol calls, custody must reconcile exactly at every finalized
boundary:

```text
native MerchantBond balance
  = all merchant bond_wei
  + claim deposit_wei and appeal_bond_wei for non-SETTLED claims
  + all withdrawable/prepaid credit
  + pool_wei
```

Depositing increases native balance and sender credit equally. A successful
business action only reclassifies credit into a bond, claim deposit, or appeal
bond. Settlement reclassifies locked liabilities into bonds, withdrawable
balances, or pool value. Withdrawal decrements credit before emitting the equal
native transfer. A failed nonpayable business action changes neither side.

## 5. Root upgradability and recovery

Both contracts are classified `UPGRADABLE`, not immutable. The constructor
registers an external wallet in `gl.storage.Root.get().upgraders`. The upgrade
body is exactly:

```python
root = gl.storage.Root.get()
code = root.code.get()
code.truncate()
code.extend(new_code)
```

Root authorization is enforced by GenVM's locked code slot; ordinary owner logic
does not grant upgrade authority. Code replacement does not automatically
migrate ordinary storage. Every change must preserve the declared storage
layout unless an independently reviewed migration design exists.

Before release, a disposable Studionet pair must prove:

- an unregistered wallet cannot mutate the locked code slot;
- the registered wallet can install marker code;
- ordinary state survives;
- the registered wallet can restore the exact reviewed source;
- `gen_getContractCode` SHA-256 equals the reviewed local source afterward.

The operational procedure is in `docs/RECOVERY.md`.

## 6. Frontend

The React/Vite application uses `genlayer-js` against Studionet only for the
current reviewed release. Contract addresses are required environment values;
superseded or placeholder addresses are forbidden.

The UI provides:

- public overview, product history, merchant, sale, and claim reads;
- injected-wallet transactions;
- a Studionet-only development burner and faucet;
- pending, finalized, execution-success, error, and readback/reconciliation states;
- merchant registration/top-up/product/sale flows;
- watcher snapshot;
- buyer claim and eligible appeal;
- public judge/finalize/settle;
- pull-payment withdrawal.

The store reads `PriceLedger.get_config()` and displays the live snapshot
cooldown. A 60-second fallback is labeled “config unavailable” and is used only
when that view fails.

## 7. Verification gates

Local evidence is necessary but not deployment evidence:

1. `genvm-lint check` and `genvm-lint typecheck` on both contracts;
2. pure unit suite, including guards, lifecycle, settlement conservation,
   address forms, validators, storage layout, and Root stub behavior;
3. official `genlayer-test` Direct Mode suite with strict mocks, pickling, and
   real 7,499/7,500 consensus-boundary cases;
4. live schema probes against Studionet RPC;
5. frontend TypeScript, production build, Vitest, and headless render checks;
6. environment-gated read-only source/config integration check;
7. separately gated Root rehearsal on disposable contracts;
8. corrected contract deployment with FINALIZED status, a `mode="leader"`
   receipt whose execution result is `SUCCESS`, explicit `LATEST_FINAL`
   readbacks, and source parity;
9. multi-wallet live journeys covering the advertised primary and appeal paths;
10. live UI readback from the same corrected addresses;
11. Codex and anonymous co-review AI approval of the exact same commit and evidence package.

Skipped integration tests do not count as completed live evidence.

## 8. Deployment and evidence order

1. Freeze a clean reviewed commit and record both contract SHA-256 values.
2. Deploy corrected PriceLedger on Studionet with the designated upgrader.
3. Deploy corrected MerchantBond referencing that exact ledger.
4. Add MerchantBond as PriceLedger registrar.
5. Verify every setup transaction is FINALIZED with execution `SUCCESS`.
6. Read back both configs, upgrader membership, registrar membership, and source.
7. Run the disposable Root rehearsal and restore exact reviewed source.
8. Execute multi-wallet lifecycle and appeal evidence.
9. Fill `deployments/README.md` with exact addresses, transaction hashes, senders,
   constructor arguments, readbacks, hashes, and explorer links.
10. Set frontend production environment to those same addresses; build, deploy
    only with user authorization, and smoke-test all evidence-bearing routes.
11. Submit the immutable evidence package to both reviewers.

## 9. Edge cases and safe outcomes

| Case | Required outcome |
|---|---|
| Dead page during snapshot | Valid `ok=false` observation or failed transaction; no fabricated price |
| Malformed/oversized model output | Deterministic rejection; no storage write |
| Fewer than three eligible frozen observations at judgment | `INSUFFICIENT_EVIDENCE` |
| Wrong currency or post-sale observation | Excluded |
| Repeated claim or settlement | Rejected |
| Merchant self-claim | Rejected |
| Bond cannot cover worst case | New claim rejected |
| Inactive or banned merchant operation | Rejected |
| Missing/conflicting appeal consensus | Prior state remains; retry possible |
| Recipient transfer failure | Claimable ledger was zeroed before emitted transfer |
| Network reset or lost Studionet state | Redeploy both contracts and relink frontend using the recovery runbook |

## 10. Known limitations

- Studionet state can reset and has no production-value guarantee.
- Observation arrays and per-merchant coverage scans are unpaginated/O(n) demo-scale operations.
- Web extraction supports five currencies but does not perform FX conversion.
- SettlementCard back-derives a settled slash from the current bond, so it labels
  the amount approximate if other bond changes occurred after settlement.
- Direct Mode does not prove native Root locked-slot authorization; the gated
  disposable Studionet rehearsal is mandatory.

## 11. Out of scope

- Production mainnet value or legal-compliance certification;
- automatic crawling, watcher rewards, or off-chain verdict services;
- cross-currency normalization;
- schema migration without a separately reviewed migration plan;
- any network other than Studionet for this release;
- deployment, GitHub push, Vercel mutation, or submission without the required user authorization.
