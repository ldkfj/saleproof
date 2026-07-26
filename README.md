# SaleProof

**Live app:** https://saleproof.vercel.app · **Contracts (GenLayer Studionet):** [`PriceLedger`](https://explorer-studio.genlayer.com/address/0x26aA8E0af993665e02A14408f75221e1951926C1) `0x26aA8E0af993665e02A14408f75221e1951926C1` · [`MerchantBond`](https://explorer-studio.genlayer.com/address/0xDa121e6fF503eC2F13101df37Cf05aD38E93544F) `0xDa121e6fF503eC2F13101df37Cf05aD38E93544F`

SaleProof proves whether a merchant's advertised discount is real. Merchants stake a GEN bond behind their sales. Anyone can snapshot a product page's price into an append-only on-chain history. When a buyer challenges a sale as fake, GenLayer validators independently read the live product page, weigh it against the accumulated price history, and reach consensus on a graduated verdict that pays out from the merchant's bond.

**Why this cannot exist without GenLayer:** the verdict needs (a) trustless reads of a live web page at many points in time and (b) a subjective judgment — *"is this discount materially honest given the observed price history?"* — that neither the merchant, the marketplace, nor the buyer can be trusted to make alone. Remove the on-chain web reading or the consensus AI judgment and there is no product left.

## The trust problem

"Fake sales" — inflating a reference price right before a promotion — are illegal in many jurisdictions (the EU Omnibus Directive requires advertised discounts to be measured against the lowest price of the prior 30 days) but almost never enforced. Buyers lose real money; honest merchants lose the trust premium; marketplaces profit from sale events and are conflicted. No single party should decide.

## Architecture — two cooperating contracts

```
┌──────────────────┐  register_product (async emit)  ┌──────────────────┐
│  MerchantBond    │ ───────────────────────────────►│   PriceLedger    │
│  bonds, sales,   │                                 │  append-only     │
│  claims, appeals,│ ◄─────────────────────────────  │  price-observation│
│  settlements     │  get_product / get_observations │  log, queryable  │
└──────────────────┘         (sync views)            │  by any contract │
                                                     └──────────────────┘
```

- **[`contracts/price_ledger.py`](contracts/price_ledger.py)** — an event-sourced evidence log. Anyone may call `snapshot(product_id)`: validators render the product page (`gl.nondet.web.render`), an LLM extracts the price into strict JSON, a deterministic firewall (`validate_extraction`) rejects anything malformed, and consensus is reached through the comparative equivalence principle. Dead pages are recorded as `ok=false` evidence. Deterministic guards (cooldown, caps, URL rules) run before any nondeterministic call.
- **[`contracts/merchant_bond.py`](contracts/merchant_bond.py)** — holds the money and runs an explicit claim state machine `OPEN → JUDGED → (APPEALED →) FINAL → SETTLED` with a single transition table. `judge_claim` serializes the on-chain price history, has validators read the live page, and judges against the 30-day-low standard with a **graduated verdict**: `GENUINE`, `INFLATED_REFERENCE` (5% bond slash), `DECEPTIVE` (10% slash), or `INSUFFICIENT_EVIDENCE`. Appeals re-judge under a skeptical persona and only overturn deterministically at ≥75% confidence. Settlements are pull-payments (`withdraw()`), never pushed.

Security posture: every LLM output passes a pure, deterministic validator (exact key set, closed verdict set, numeric ranges, length caps — prompt-injected instructions in page content cannot widen the decision space); every address input is normalized (`Address`/hex/bytes/int); all money is integer wei, all ratios basis points — no floats anywhere.

## The full journey (all real, on-chain today)

1. Merchant registers with a staked bond and lists a product URL.
2. Watchers snapshot the price over time — the chain accumulates evidence.
3. Merchant announces a sale with a claimed reference price and discount.
4. A buyer who smells a fake sale files a claim with a small deposit.
5. Anyone triggers `judge_claim`: validators fetch the live page, compare with history, and deliver a verdict with written reasoning stored on-chain.
6. The losing side may appeal within the window (appeal bond at stake); a skeptical re-judge decides; settlement pays buyers from the bond, strikes the merchant (3 strikes = permanent ban), and `withdraw()` releases funds.

Claim #1 on the live contracts shows a complete real case: history of £51.77 vs a claimed £65.00 reference — verdict `INFLATED_REFERENCE` at 100% confidence, with the validators' reasoning readable on-chain and in the app.

## Repository layout

```
contracts/        price_ledger.py, merchant_bond.py   (GenLayer Intelligent Contracts, Python)
frontend/         React + Vite + TypeScript dApp using genlayer-js (read + write, wallet + dev burner)
tests/            66 unit tests: guards, payout math, state machine, adversarial LLM-output suites
frontend/scripts/ verify-live.mjs, render-check.mjs, write-check.mjs  (chain-truth + headless UI evidence)
docs/             SPEC.md (design), BUILD-LOG.md (full engineering journal), screenshots/, SUBMISSION.md
```

## Run it yourself

```bash
# contract unit tests (pure Python, stubbed runtime)
python -m pytest -v

# frontend against the live Studionet contracts
cd frontend
cp .env.example .env
npm install && npm run dev
# verify every value the UI shows against the chain:
node scripts/verify-live.mjs
```

The app ships a **dev burner wallet** (Studionet only) with a one-click faucet, so you can register a merchant, snapshot prices, announce sales, file claims, trigger judgments, appeal, settle, and withdraw — end to end — without installing anything.

## Roadmap

- Testnet Bradbury migration is in progress (the PriceLedger deploy transaction has finalized there); the app is network-switchable via `VITE_GL_NETWORK` and the production site will be repointed once the full pair is live.
- Indexed coverage-reservation accounting (current scan is O(n), fine at demo scale).
- Watcher incentives for snapshot contributions.
