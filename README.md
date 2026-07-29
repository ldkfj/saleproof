# SaleProof

SaleProof is a GenLayer protocol that tests whether a merchant's advertised
discount is supported by an independently recorded on-chain price history.

## Verified links

- [PriceLedger on Studionet](https://explorer-studio.genlayer.com/address/0xE14023EF575ce85Cd0a709DA3997483315BaEB40)
- [MerchantBond on Studionet](https://explorer-studio.genlayer.com/address/0x6BaFf2C558F20147ECDEc3867E59A172B4995a5b)
- [Release manifest and transaction evidence](deployments/README.md)
- [Current render/write screenshots](docs/screenshots/current/)
- [Production web app](https://saleproof.vercel.app) — live on Vercel with the
  current Studionet release pair.
- [Public GitHub repository](https://github.com/ldkfj/saleproof)
- [Final exact-revision deployment record](https://github.com/ldkfj/saleproof/releases/tag/studionet-final)

Both contracts were deployed from dual-approved commit `7900161`. Their
deployed source, configuration, registrar wiring, recovery rehearsal, primary
and appeal journeys, pull payments, custody conservation, and current local
frontend evidence have been independently read back on Studionet.

## Trust problem

A merchant may inflate a reference price, a buyer may file a self-serving
complaint, and a marketplace may benefit from promotion volume. A centralized
scraper or AI operator could also alter the evidence or verdict.

SaleProof does not trust any one of those parties. Merchants put test GEN behind
their claims, independent watchers append product-page observations, and a
buyer can challenge one canonical sale claim. The caller never supplies the
verdict or payout tier.

## Why GenLayer is essential

The disputed fact is partly subjective and partly outside the chain: what price
the product page shows, and whether the advertised reference is genuine under
the frozen 30-day-low standard.

GenLayer validators:

1. execute replicated web access from the Intelligent Contract;
2. validate strict structured price evidence;
3. compare a live page read with the frozen on-chain observation prefix;
4. reach comparative consensus on a closed verdict and confidence;
5. let deterministic contract code apply the corresponding settlement.

A conventional deterministic contract cannot fetch and interpret the live web
page. A single off-chain oracle would reintroduce the trust dependency that the
protocol is designed to remove.

## How it works

1. A merchant deposits prepaid credit, registers with a bond, and registers a
   product URL.
2. Independent watchers call `snapshot(product_id)`. Validators fetch the
   product page and append bounded observations to PriceLedger.
3. The merchant announces a sale with a currency, reference price, discount,
   duration, and frozen observation count.
4. A buyer deposits the claim amount and files the sale's one canonical claim.
5. Validators judge the live page against the eligible frozen history.
6. The unappealed branch becomes final after the appeal window, or an eligible
   party funds an appeal and triggers `judge_appeal`.
7. Anyone may settle a final claim. Deterministic rules update bond, strikes,
   pool, and pull-payment balances; recipients withdraw separately.

The fresh release proves both an unappealed `INFLATED_REFERENCE` settlement and
an exercised appeal that ends `GENUINE`. Full hashes and readbacks are in the
[release manifest](deployments/README.md).

## Architecture

| Layer | Responsibility | Source of truth |
|---|---|---|
| PriceLedger | Product registry, registrar authorization, bounded observation history, validator web extraction | Studionet contract storage |
| MerchantBond | Merchant bonds, sales, canonical claims, appeals, settlement, prepaid credit, pull payments | Studionet contract storage |
| React/Vite frontend | Finalized reads, wallet UX, transaction lifecycle, evidence visualization | Contract views; never a local verdict |
| Evidence scripts | Fail-closed chain assertions, production render captures, one real UI write check | Explicit release addresses and finalized reads |
| Local tests | Guard, state-machine, serialization, custody, SDK, and UI regressions | Reviewed source revision |

The frontend has no backend database. It uses `genlayer-js` directly against
Studionet and displays a configuration error when real contract addresses are
absent.

## Intelligent Contracts

### PriceLedger

[`contracts/price_ledger.py`](contracts/price_ledger.py) stores registered
products and bounded append-only observation arrays. `snapshot(product_id)` is
the only nondeterministic method. Product existence, active status, observation
cap, and cooldown are checked before validator web access; storage is written
only after comparative consensus returns validated extraction data.

### MerchantBond

[`contracts/merchant_bond.py`](contracts/merchant_bond.py) owns merchant bonds,
sales, claims, appeals, deterministic settlement, prepaid credit, and
withdrawable balances. Each sale has one canonical claim:

```text
OPEN -> JUDGED -> APPEALED -> FINAL -> SETTLED
          |
          +-- finalize after appeal window --> FINAL
```

Verdicts are `GENUINE`, `INFLATED_REFERENCE`, `DECEPTIVE`, and
`INSUFFICIENT_EVIDENCE`. Appeal consensus validates exact types and recomputes
the 7,500-bp overturn outcome for both leader and validator results before
applying confidence tolerance.

### Value and upgrade model

`deposit()` is the sole payable business entry point. Funded actions are
nonpayable and consume prepaid credit only after deterministic guards pass.
Settlement uses pull payments, and `withdraw()` zeros storage before transfer.

Both contracts are Root-slot upgradable. Only the registered external upgrader
may replace code; storage layout compatibility remains mandatory. Recovery is
documented in [`docs/RECOVERY.md`](docs/RECOVERY.md).

## Transaction lifecycle

The frontend:

1. binds network, contract, wallet, action, and amount before funding;
2. submits at most one deposit for a persisted funding intent;
3. waits for `FINALIZED` and actual leader execution `SUCCESS`;
4. reconciles prepaid credit before sending the nonpayable business call;
5. waits for that call to finalize successfully;
6. refreshes finalized contract state and wallet balance.

Ambiguous deposit submission is never blindly retried. A failed nonpayable
business call leaves prepaid credit withdrawable. Snapshot transactions persist
their hash for resume; after finalization, ProductDetail performs a bounded
retry because Studionet finalized reads can be briefly stale.

## Run locally

Prerequisites:

- Python 3.13
- Node.js 22
- the dependencies in `requirements-dev.txt`

Install and verify contracts:

```powershell
cd E:\Genlayer-Projects\saleproof
py -3.13 -m pip install -r requirements-dev.txt
py -3.13 -m pytest -v
py -3.13 -m pytest genvm_tests\direct -v
$env:PYTHONIOENCODING='utf-8'
genvm-lint check contracts\price_ledger.py --json
genvm-lint typecheck contracts\price_ledger.py
genvm-lint check contracts\merchant_bond.py --json
genvm-lint typecheck contracts\merchant_bond.py
py -3.13 scripts\schema_probe.py --rpc https://studio.genlayer.com/api
```

Run the frontend:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
# Fill only the real Studionet addresses from deployments/README.md.
npm run dev
```

Required environment values:

```text
VITE_GL_NETWORK=studionet
VITE_LEDGER_ADDRESS=0xE14023EF575ce85Cd0a709DA3997483315BaEB40
VITE_BOND_ADDRESS=0x6BaFf2C558F20147ECDEc3867E59A172B4995a5b
```

The committed `.env.example` intentionally leaves address values blank. Never
put placeholder, superseded, or private values in a real environment.

## Tests and verification

Current results:

| Check | Result |
|---|---|
| Python unit/harness | `97 passed` |
| Official Direct Mode | `8 passed` |
| PriceLedger lint/typecheck/schema | PASS; 13 methods; constructor 3 |
| MerchantBond lint/typecheck/schema | PASS; 22 methods; constructor 7 |
| Read-only live source/config parity | `1 passed, 1 deselected` |
| Disposable Root rehearsal | `1 passed, 1 deselected` |
| TypeScript | PASS |
| Vite production build | PASS; 494 modules |
| Vitest | `10 files / 43 tests` |
| Oxlint | exit 0; three known Fast Refresh warnings |
| Five-route local production-build render evidence | PASS |
| Real UI snapshot write | PASS; `5 -> 6` observations without reload |
| Public Vercel smoke check | PASS; books row, `£51.77`, `SETTLED`, `INFLATED REF` |
| Public deep-route direct load/reload | PASS; see the final deployment record |

The opt-in network and browser scripts fail closed unless explicit release
addresses and opt-in flags are supplied. A default skip, an old screenshot, a
pending transaction, or validator votes without leader `SUCCESS` are not
release evidence.

## Deployment

| Field | PriceLedger | MerchantBond |
|---|---|---|
| Address | `0xE14023EF575ce85Cd0a709DA3997483315BaEB40` | `0x6BaFf2C558F20147ECDEc3867E59A172B4995a5b` |
| Deploy transaction | `0xee73c9e0eefdecbd6455501f4aba29be9fadb5296f68a1d1c7e2526bfe70868b` | `0x510166780d98e1ae3d1cb2b2acd7ff57dc7f9eb14aec899a50c7d99c10e76ebc` |
| Source SHA-256 | `61fccf91...f392` | `d7d20db9...753f` |
| Owner / Root upgrader | `0x666d...28Dc` | `0x666d...28Dc` |
| Final status | `FINALIZED + SUCCESS` | `FINALIZED + SUCCESS` |

PriceLedger is configured with a 60-second snapshot cooldown and 500-observation
cap. MerchantBond links that exact ledger, requires a 2 GEN merchant bond,
0.1 GEN claim deposit, 0.5 GEN appeal bond, 300-second appeal window, and three
strikes. Registrar membership, deployed-source parity, config, and Root
membership all pass finalized readback.

Studionet may reset. The recovery runbook requires source/config parity and a
new disposable Root rehearsal before a replacement pair is accepted.

## Security and trust boundaries

- Contract inputs use strict address normalization and bounded integer/string
  validation.
- Nondeterministic calls occur only after deterministic guards and do not write
  storage until validated consensus returns.
- Sale evidence uses the frozen observation prefix, exact currency, inclusive
  30-day window, valid integer prices, and pre-announcement timestamps.
- Business calls never attach value after their guards; prepaid credit prevents
  failed-call value loss in the current Studio runtime.
- Pull payments isolate settlement from recipient transfer behavior.
- The frontend treats only `FINALIZED + SUCCESS` as a successful write and uses
  finalized reads for displayed state.
- Deployment keys and local checkpoints remain ignored; no credential, private
  receipt payload, or private key belongs in the repository.
- Root upgrade authority is operational trust, not governance decentralization.

## Known limitations

- Studionet GEN is test value; SaleProof is not a production payment or legal
  compliance system.
- Studionet is temporary and may reset.
- Observation reads and bond-coverage scans are demo-scale and unpaginated.
- Five currencies are parsed, but there is no FX conversion.
- Product-page extraction depends on validator web reachability and page
  stability; unreadable pages are recorded as `ok=false`.
- The Root upgrader is one user-controlled wallet.
- Studionet RPC capacity exhaustion can make an aggregate table temporarily
  incomplete; refreshing after capacity recovers restores the finalized rows.
