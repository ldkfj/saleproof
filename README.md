# SaleProof

SaleProof is a two-contract GenLayer demonstration for testing whether an
advertised discount is supported by a product's prior price history.

Merchants stake a native-GEN bond, independent callers record product-page
prices in an on-chain evidence log, and a buyer may challenge a sale. GenLayer
validators read the live page and judge it against the frozen evidence. The
contract then applies a closed verdict set and deterministic pull-payment rules.

## Release status

The current source has passed its local correction gates, but live release
review remains pending. It is **not yet the source of the previous public
Studionet deployment**. Those earlier addresses, screenshots, and journeys are
historical evidence only and are explicitly superseded.

A current release requires all of the following to refer to one exact revision:

- corrected PriceLedger and MerchantBond deployments on Studionet;
- FINALIZED + `SUCCESS` deployment/setup receipts;
- deployed-source SHA-256 parity with the reviewed commit;
- a disposable Root-upgrade authorization/state-preservation rehearsal;
- multi-wallet primary and appeal journeys;
- frontend environment and render evidence using the same contract pair;
- approval from Codex and the anonymous co-review AI.

Until those gates are complete, no contract address or live site is presented
here as current release evidence.

## Why GenLayer

No participant is a neutral source of truth: a merchant can inflate a reference
price, a buyer can make a self-serving complaint, and a marketplace can benefit
from promotion volume. A centralized scraper or AI operator could also change
the evidence or verdict.

SaleProof makes the contract authoritative. Validator-replicated web access
collects and rechecks real-world evidence; subjective consensus classifies the
sale; deterministic guards constrain evidence, state transitions, and money
movement. The caller cannot submit the verdict or payout tier.

Studionet GEN is test value. SaleProof does not claim production settlement or
legal-compliance certification.

## Contracts

### PriceLedger

[`contracts/price_ledger.py`](contracts/price_ledger.py) stores registered
products and bounded, append-only observation arrays. `snapshot(product_id)` is
permissionless after product, cap, and cooldown guards. It renders the product
page, extracts strict JSON, reaches comparative consensus, and only then appends
an observation. Dead-page evidence may be recorded as `ok=false`.

### MerchantBond

[`contracts/merchant_bond.py`](contracts/merchant_bond.py) owns merchant bonds,
sales, claims, appeals, deterministic settlement, and withdrawable balances.
Each sale has one canonical claim:

```text
OPEN -> JUDGED -> APPEALED -> FINAL -> SETTLED
          |
          +-- finalize after the appeal window --> FINAL
```

Verdicts are `GENUINE`, `INFLATED_REFERENCE`, `DECEPTIVE`, and
`INSUFFICIENT_EVIDENCE`. Appeal consensus recomputes the 7,500-bp overturn
boundary for both leader and validator outputs, so confidence tolerance cannot
cross into a different economic outcome.

Both contracts are Root-slot upgradable. Code replacement uses the current
`truncate()`/`extend()` API and does not automatically migrate storage.

The complete, current behavior is specified in
[`docs/SPEC.md`](docs/SPEC.md). Operational recovery is documented in
[`docs/RECOVERY.md`](docs/RECOVERY.md).

## Repository

```text
contracts/            Intelligent contracts
tests/                Pure unit tests and the local GenLayer stub
genvm_tests/direct/   Official genlayer-test Direct Mode checks
genvm_tests/integration/
                      Opt-in Studionet parity and Root rehearsal
frontend/             React, Vite, TypeScript, genlayer-js
scripts/              Live schema probe
deployments/          Release manifest and evidence checklist
docs/                 Specification, engineering log, recovery, evidence
```

## Local verification

Install the pinned development dependencies, then run:

```powershell
python -m pip install -r requirements-dev.txt
genvm-lint check contracts/price_ledger.py --json
genvm-lint check contracts/merchant_bond.py --json
genvm-lint typecheck contracts/price_ledger.py
genvm-lint typecheck contracts/merchant_bond.py
python -m pytest tests -v
python -m pytest genvm_tests/direct -v
python scripts/schema_probe.py --rpc https://studio.genlayer.com/api
```

Frontend checks:

```powershell
cd frontend
npm install
npx tsc --noEmit
npm run build
npx vitest run
```

`frontend/.env.example` intentionally contains blank contract addresses. Fill
them only from a completed corrected deployment recorded in
[`deployments/README.md`](deployments/README.md). The application otherwise
shows a configuration error instead of silently using stale or placeholder
contracts.

The integration and live-render scripts are opt-in. A skipped integration test
or an old screenshot is not live release evidence.

## Current limitations

- Studionet may reset and has no production-value guarantee.
- Observation reads and coverage scans are demo-scale and unpaginated.
- Five currencies are parsed, but there is no FX conversion.
- Direct Mode cannot prove native Root locked-slot authorization; the disposable
  Studionet rehearsal remains mandatory.
- Current deployment, journey, and frontend evidence are pending.
