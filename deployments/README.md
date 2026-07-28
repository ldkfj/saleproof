# SaleProof Studionet Release Manifest

## Current status

**No corrected release deployment is recorded yet.**

The active manifest must remain incomplete until every required transaction is
FINALIZED with execution `SUCCESS`, every readback matches, and deployed source
hashes match the exact reviewed commit. Blank fields are not evidence.

## Canonical network

| Field | Value |
|---|---|
| Network | Studionet |
| Chain ID | `61999` |
| RPC | `https://studio.genlayer.com/api` |
| Explorer | `https://explorer-studio.genlayer.com` |
| Value classification | Test GEN; no production-value claim |

## Reviewed revision

| Field | Required value |
|---|---|
| Git commit | PENDING |
| Clean tree verified | PENDING |
| PriceLedger SHA-256 | `61fccf91ef74ac0fd138aa6b56ee89fd957f299215266b3861b0c128cf96f392` |
| MerchantBond SHA-256 | `5b0fa27b724643680c776eab867aa124a2f5a381f7f8c676bf2157d9c27d66bb` |
| Runner | `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6` |
| Codex verdict | PENDING |
| Anonymous co-review AI verdict | PENDING |

Both reviewers must approve this exact revision and the same completed evidence
package. A later source, deployment, environment, or documentation change
invalidates those approvals.

## Contract deployment record

| Field | PriceLedger | MerchantBond |
|---|---|---|
| Address | PENDING | PENDING |
| Deployment transaction | PENDING | PENDING |
| Sender / owner | PENDING | PENDING |
| Registered Root upgrader | PENDING | PENDING |
| Final transaction status | PENDING | PENDING |
| Execution result | PENDING | PENDING |
| Explorer link | PENDING | PENDING |
| `gen_getContractCode` SHA-256 | PENDING | PENDING |
| Local/deployed source parity | PENDING | PENDING |
| Config readback | PENDING | PENDING |

### Constructor arguments

PriceLedger:

```text
upgrader_address: PENDING
snapshot_cooldown_s: PENDING
max_observations: PENDING
```

MerchantBond:

```text
upgrader_address: PENDING
ledger: PENDING
min_bond_wei: PENDING
claim_deposit_wei: PENDING
appeal_bond_wei: PENDING
appeal_window_s: PENDING
strike_limit: PENDING
```

## Pair wiring

| Check | Transaction / readback | Status |
|---|---|---|
| MerchantBond config points to the recorded PriceLedger | PENDING | PENDING |
| `PriceLedger.add_registrar(MerchantBond)` | PENDING | PENDING |
| `PriceLedger.is_registrar(MerchantBond) == true` | PENDING | PENDING |
| PriceLedger owner readback | PENDING | PENDING |
| MerchantBond owner readback | PENDING | PENDING |
| Root upgrader membership on both contracts | PENDING | PENDING |

The required order is:

1. deploy PriceLedger;
2. deploy MerchantBond with that exact ledger address;
3. authorize MerchantBond as registrar;
4. verify source, config, Root membership, and registrar membership;
5. only then run journeys or configure the frontend.

## Disposable Root rehearsal

Release contracts must never receive marker code. Record a separate disposable
pair:

| Evidence | PriceLedger rehearsal | MerchantBond rehearsal |
|---|---|---|
| Disposable address | PENDING | PENDING |
| Linked seeded record IDs | product + observation: PENDING | merchant + sale + claim: PENDING |
| Unauthorized upgrade tx | PENDING | PENDING |
| Unauthorized result is finalized failure | PENDING | PENDING |
| Code unchanged after denial | PENDING | PENDING |
| Authorized marker upgrade tx | PENDING | PENDING |
| Marker view/state-preservation readback | PENDING | PENDING |
| Exact-source restore tx | PENDING | PENDING |
| Restored source SHA/state readback | PENDING | PENDING |

The executable procedure is
`genvm_tests/integration/test_saleproof_network.py::test_studionet_root_upgrade_rehearsal`.
Skipped output does not satisfy this section.

## Live journey proof matrix

Every advertised actor/action needs a transaction hash and post-transaction
readback from the corrected pair.

| Actor / branch | Contract method | Transaction | FINALIZED + SUCCESS | Readback |
|---|---|---|---|---|
| Merchant registration/bond | `register_merchant` | PENDING | PENDING | PENDING |
| Product registration | `add_product` + triggered `register_product` | PENDING | PENDING | PENDING |
| Independent watcher snapshots | `snapshot` | PENDING | PENDING | PENDING |
| Sale announcement | `announce_sale` | PENDING | PENDING | PENDING |
| Buyer claim/deposit | `file_claim` | PENDING | PENDING | PENDING |
| Primary judgment | `judge_claim` | PENDING | PENDING | PENDING |
| Appeal bond | `appeal` | PENDING | PENDING | PENDING |
| Secondary judgment | `judge_appeal` | PENDING | PENDING | PENDING |
| Unappealed finalization branch | `finalize_unappealed` | PENDING | PENDING | PENDING |
| Permissionless settlement | `settle` | PENDING | PENDING | PENDING |
| Buyer/appellant/merchant withdrawal | `withdraw` | PENDING | PENDING | PENDING |
| Failed guard evidence | relevant methods | PENDING | expected failure | PENDING |

At minimum, evidence must include more than one wallet, the economic flow from
funding through final withdrawal, the canonical-claim guard, the primary verdict
path, the appeal path, exact settlement conservation, and withdrawal zeroing.

## Frontend evidence

| Field | Required value |
|---|---|
| `VITE_GL_NETWORK` | `studionet` |
| `VITE_LEDGER_ADDRESS` | PENDING; must equal this manifest |
| `VITE_BOND_ADDRESS` | PENDING; must equal this manifest |
| Frontend commit | PENDING; must equal reviewed revision |
| Production deployment URL | PENDING |
| `verify-live.mjs` output | PENDING |
| Render-check output and current screenshots | PENDING |
| Real write-check transaction/readback | PENDING |
| Post-deploy smoke check | PENDING |

Do not copy superseded addresses into `.env.example`. Runtime addresses are
filled only after this manifest's contract gates are complete.

## Historical superseded deployment

The following earlier Studionet pair predates the current contract correction
and must not be used as current source-parity, Root, frontend, or submission
evidence:

- PriceLedger `0x26aA8E0af993665e02A14408f75221e1951926C1`
- MerchantBond `0xDa121e6fF503eC2F13101df37Cf05aD38E93544F`

Historical journey details remain in `docs/BUILD-LOG.md` for audit continuity.
They do not close any pending field above.
