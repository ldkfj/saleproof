# SaleProof Studionet Release Manifest

## Current status

**Corrected PriceLedger deployed; MerchantBond and pair wiring remain pending.**

The active manifest must remain incomplete until every required transaction is
FINALIZED and its `mode="leader"` receipt has execution result `SUCCESS`, every
evidence readback explicitly uses `LATEST_FINAL`, and deployed source hashes
match the exact reviewed commit. Blank fields are not evidence; validator
success cannot substitute for a failed or missing leader result.

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
| Source freeze commit | `ad056635af3411e2e3aab5fb7f22ecf37e72a530` |
| Completed evidence-package commit | PENDING; recorded after live evidence is committed |
| Clean tree verified | YES immediately before PriceLedger deployment at `c89da7d8eff9c562f05a4ad9721bc6ae51f2c333` |
| PriceLedger SHA-256 | `61fccf91ef74ac0fd138aa6b56ee89fd957f299215266b3861b0c128cf96f392` |
| MerchantBond SHA-256 | `5b0fa27b724643680c776eab867aa124a2f5a381f7f8c676bf2157d9c27d66bb` |
| Runner | `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6` |
| Contract classification | `UPGRADABLE` (both contracts; GenVM Root code slot) |
| Runner advisory review | `I200` reviewed: retain pinned runner for this release; newer runner requires separate schema/rehearsal/dual review |
| Recovery runbook | `docs/RECOVERY.md` |
| Codex verdict | PENDING |
| Anonymous co-review AI verdict | PENDING |

Both reviewers must approve this exact revision and the same completed evidence
package. A later source, deployment, environment, or documentation change
invalidates those approvals.

## Required identity and authorization gate

| Field | Required value |
|---|---|
| User-selected deployment wallet / owner | `0x666d6A7dCA1319caDcC7fB6b10DAB55cD8e128Dc` |
| Verified active deployment address | `0x666d6A7dCA1319caDcC7fB6b10DAB55cD8e128Dc` derived from the configured key immediately before deployment |
| User-selected Root upgrader wallet | `0x666d6A7dCA1319caDcC7fB6b10DAB55cD8e128Dc` |
| Verified active Root upgrader address | `0x666d6A7dCA1319caDcC7fB6b10DAB55cD8e128Dc` |
| Explicit confirmation for PriceLedger deployment | YES — user replied “Xác nhận” after the exact wallet, network, constructor values, and source hash were presented |
| Explicit confirmation for MerchantBond deployment | PENDING |
| Explicit confirmation for registrar write | PENDING |

Account or wallet history does not satisfy this table. Codex must ask which
wallet to use, verify the active address and target, then obtain explicit
confirmation before each release network write.

## Contract deployment record

| Field | PriceLedger | MerchantBond |
|---|---|---|
| Address | `0x6a3E79C7F9ec2f11C355bd19fcc99ef87412BaD0` | PENDING |
| Deployment transaction | `0x5245b07d5ecfee24f6c423a10d16398320918fdf75d993aec75d06b453884dcc` | PENDING |
| Sender / owner | `0x666d6A7dCA1319caDcC7fB6b10DAB55cD8e128Dc` | PENDING |
| Registered Root upgrader | `0x666d6A7dCA1319caDcC7fB6b10DAB55cD8e128Dc` | PENDING |
| Final transaction status | `FINALIZED` | PENDING |
| Execution result | actual leader `SUCCESS` | PENDING |
| Explorer link | https://explorer-studio.genlayer.com/transactions/0x5245b07d5ecfee24f6c423a10d16398320918fdf75d993aec75d06b453884dcc | PENDING |
| `gen_getContractCode` SHA-256 | `61fccf91ef74ac0fd138aa6b56ee89fd957f299215266b3861b0c128cf96f392` | PENDING |
| Local/deployed source parity | PASS — exact UTF-8 bytes | PENDING |
| Coupled FINALIZED leader-success receipt / no intervening upgrade | PASS — code/config read immediately after the recorded deployment receipt | PENDING |
| Config readback | owner `0x666d6A7dCA1319caDcC7fB6b10DAB55cD8e128Dc`; cooldown `60`; cap `500`; `is_upgrader == true` | PENDING |

### Constructor arguments

Approved intended release calldata (actual encoded calldata and readback remain
pending until deployment):

PriceLedger:

```text
upgrader_address: 0x666d6A7dCA1319caDcC7fB6b10DAB55cD8e128Dc
snapshot_cooldown_s: 60
max_observations: 500
```

MerchantBond:

```text
upgrader_address: PENDING USER-SELECTION / VERIFIED ADDRESS
ledger: PENDING ACTUAL PRICELEDGER ADDRESS FROM THIS MANIFEST
min_bond_wei: 2000000000000000000
claim_deposit_wei: 100000000000000000
appeal_bond_wei: 500000000000000000
appeal_window_s: 300
strike_limit: 3
```

No placeholder address may be encoded. The actual transaction calldata, sender,
contract address, and finalized config readback must be added to the deployment
record before this section is complete.

## Pair wiring

| Check | Transaction / readback | Status |
|---|---|---|
| MerchantBond config points to the recorded PriceLedger | PENDING | PENDING |
| `PriceLedger.add_registrar(MerchantBond)` | PENDING | PENDING |
| `PriceLedger.is_registrar(MerchantBond) == true` | PENDING | PENDING |
| PriceLedger owner readback | `LATEST_FINAL get_config.owner == 0x666d6A7dCA1319caDcC7fB6b10DAB55cD8e128Dc` | PASS |
| MerchantBond owner readback | PENDING | PENDING |
| Root upgrader membership on both contracts | PriceLedger `is_upgrader(0x666d6A7dCA1319caDcC7fB6b10DAB55cD8e128Dc) == true`; MerchantBond pending | PARTIAL |

On current Studionet, `gen_getContractCode` must use the legacy `[address]`
request shape. Its parity result is accepted only when coupled to the recorded
FINALIZED leader-`SUCCESS` deployment/upgrade receipt, a paused write window,
and proof that no intervening upgrade occurred.

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
| Disposable address | `0xe6227B6C8305EEbdd6468cf4206C18e87bFB19f2` | `0xBAd98e2A9f116A330E6Da062397775752eFC60dE` |
| Linked seeded record IDs | product `1`; `3` observations | merchant `0x666d6A7dCA1319caDcC7fB6b10DAB55cD8e128Dc`; product `1`; sale `1`; claim `1` |
| Unauthorized upgrade tx | `0xe2e05e55e90b1631ddd5f6c6c4918dc12a7b9980f26c28534f7ce10860f86bd5` | `0xf0ef12303f60215042d4b73b0adccf73276dd6d385d0e14fb9896ae2bfb98ed0` |
| Unauthorized result is finalized failure | `FINALIZED`; actual leader `NON_SUCCESS` | `FINALIZED`; actual leader `NON_SUCCESS` |
| Code unchanged after denial | PASS; exact pre-attempt source bytes | PASS; exact pre-attempt source bytes |
| Authorized marker upgrade tx | `0xe9c63c1f3fed16e9336c8148a5d0db25da7f9fc47520e205514acbcc10a753a9` | `0xcaae601663c29e7b84cdedbfbc54fd159a66842eacf8f78d3e8e92425fecfb4f` |
| Marker view/state-preservation readback | PASS; marker plus config/count/product/observations matched | PASS; marker plus config/counts/merchant/sale/claim/withdrawables matched |
| Exact-source restore tx | `0xc2ab93448f4567f518d954fcea59c5e7e716356d24ed70ee69a8e530e65c5d0a` | `0x055a36e032895e355ba350739cbd9fb97f3bbaff4255b3b72440f21565322577` |
| Restored source SHA/state readback | `61fccf91ef74ac0fd138aa6b56ee89fd957f299215266b3861b0c128cf96f392`; exact state equality | `5b0fa27b724643680c776eab867aa124a2f5a381f7f8c676bf2157d9c27d66bb`; exact state equality |

The executable procedure is
`genvm_tests/integration/test_saleproof_network.py::test_studionet_root_upgrade_rehearsal`.
It passed at source freeze `ad056635af3411e2e3aab5fb7f22ecf37e72a530`
(`1 passed, 1 deselected`, exit code `0`). The authorized rehearsal upgrader was
`0x666d6A7dCA1319caDcC7fB6b10DAB55cD8e128Dc`; the denied caller was
`0xa52A403Bb4fB8D79625bb8A3481e0e27a2428CC1`. The harness required all four
release/rehearsal addresses to be nonzero and pairwise distinct, used
`LATEST_FINAL` for every state read, required exactly one actual leader receipt,
and restored both contracts before returning success. These disposable
addresses are not release addresses.

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
