# SaleProof Studionet Release Manifest

## Current status

**PUBLIC GITHUB + VERCEL PASS; final exact-revision anonymous co-review is
pending.**

The release contracts were deployed from exact pre-deploy commit
`79001612d6126e809c2c17c47418bede1c8e64f4`, which received both Codex and
anonymous co-review approval. The contracts have not changed since that source
freeze. Deployment, wiring, disposable Root recovery rehearsal, multi-wallet
journeys, custody reconciliation, and local frontend render/write evidence are
complete.

The live write check exposed an eventually-consistent post-finalization UI
refresh defect. Its correction and evidence package received anonymous
`POST_DEPLOY_TEST` approval on exact commit
`6054c849cdf7e149eb278c63f5c284c56ce412ad`. The same source tree is now public
on GitHub and deployed to Vercel with the current Studionet pair. The remaining
gate is anonymous `POST_GITHUB_VERCEL_FINAL` review of the exact final evidence
revision.

## Canonical network

| Field | Value |
|---|---|
| Network | Studionet |
| GenLayer RPC | `https://studio.genlayer.com/api` |
| Chain ID | `61999` |
| Currency | Test GEN; no production-value claim |
| Explorer | `https://explorer-studio.genlayer.com` |
| Persistence warning | Studionet is temporary; reset recovery remains mandatory |

Bradbury addresses, RPCs, transactions, and Explorer links are not release
evidence for this project.

## Reviewed source and identity

| Field | Value |
|---|---|
| Exact deployed source commit | `79001612d6126e809c2c17c47418bede1c8e64f4` |
| PriceLedger SHA-256 | `61fccf91ef74ac0fd138aa6b56ee89fd957f299215266b3861b0c128cf96f392` |
| MerchantBond SHA-256 | `d7d20db98851ae3958bf810eac45b95bc796f1b942c4e7131992fa957bba753f` |
| GenVM dependency | `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6` |
| Classification | Both contracts are Root-slot `UPGRADABLE` |
| User-selected deployment owner and Root upgrader | `0x666d6A7dCA1319caDcC7fB6b10DAB55cD8e128Dc` |
| Pre-deploy Codex verdict | APPROVED |
| Pre-deploy anonymous co-review verdict | APPROVED on exact commit `7900161` |
| Post-live anonymous co-review | APPROVED on exact commit `6054c849cdf7e149eb278c63f5c284c56ce412ad` |
| Public source-tree commit | `3d4c7a7287b46133c63db47f44b53885d357606c` (history-only merge; zero tree diff from `6054c84`) |
| Final post-GitHub/Vercel anonymous co-review | PENDING on this final evidence package |

The selected wallet was derived from the configured local key without exposing
the key. The user explicitly authorized the deployments and test transactions.

## Release contracts

| Field | PriceLedger | MerchantBond |
|---|---|---|
| Address | `0xE14023EF575ce85Cd0a709DA3997483315BaEB40` | `0x6BaFf2C558F20147ECDEc3867E59A172B4995a5b` |
| Deploy tx | `0xee73c9e0eefdecbd6455501f4aba29be9fadb5296f68a1d1c7e2526bfe70868b` | `0x510166780d98e1ae3d1cb2b2acd7ff57dc7f9eb14aec899a50c7d99c10e76ebc` |
| Status / leader result | `FINALIZED` / `SUCCESS` | `FINALIZED` / `SUCCESS` |
| Owner | `0x666d...28Dc` | `0x666d...28Dc` |
| Root upgrader readback | `true` | `true` |
| Deployed source parity | exact SHA-256 match | exact SHA-256 match |

Explorer:

- [PriceLedger address](https://explorer-studio.genlayer.com/address/0xE14023EF575ce85Cd0a709DA3997483315BaEB40)
- [MerchantBond address](https://explorer-studio.genlayer.com/address/0x6BaFf2C558F20147ECDEc3867E59A172B4995a5b)
- [PriceLedger deploy transaction](https://explorer-studio.genlayer.com/transactions/0xee73c9e0eefdecbd6455501f4aba29be9fadb5296f68a1d1c7e2526bfe70868b)
- [MerchantBond deploy transaction](https://explorer-studio.genlayer.com/transactions/0x510166780d98e1ae3d1cb2b2acd7ff57dc7f9eb14aec899a50c7d99c10e76ebc)

Finalized constructor/config readback:

```text
PriceLedger:
  owner/upgrader: 0x666d6A7dCA1319caDcC7fB6b10DAB55cD8e128Dc
  snapshot_cooldown_s: 60
  max_observations: 500

MerchantBond:
  owner/upgrader: 0x666d6A7dCA1319caDcC7fB6b10DAB55cD8e128Dc
  ledger: 0xE14023EF575ce85Cd0a709DA3997483315BaEB40
  min_bond_wei: 2000000000000000000
  claim_deposit_wei: 100000000000000000
  appeal_bond_wei: 500000000000000000
  appeal_window_s: 300
  strike_limit: 3
  initial pool_wei: 0
```

Registrar transaction
`0xd0afe836c21603dcb6ddd97abbe8344a03b3e9e635a14df0c0a698b298207ef1`
is `FINALIZED` with leader `SUCCESS`; the finalized readback changed from
`false` to `true`.

## Disposable Root recovery rehearsal

The rehearsal used separate contracts and never installed marker code on the
release pair:

| Field | Rehearsal PriceLedger | Rehearsal MerchantBond |
|---|---|---|
| Address | `0xE9AEC28A0BD2A387a424e52A882177dE8054489F` | `0x8BADD9121209a4b4Db6Ee190F2C1Df36EC8CB69E` |
| Deploy tx | `0xd21a07060851d5e2b67d1a2d8c99ac1176013edd4d8708e7567c4bdad60fe4e1` | `0xbee2d532ffb3d5af9f397ba452a01f5ec081b798ae402a90435fbd6c6dc1aa96` |
| Unauthorized upgrade | `0xe8fb34df5fbb69a6dca64701ed8474fa6a5cb6b35f6a3a454d865df6a3ea5106` - execution `ERROR` | `0xff032eed05e14fa8261dd1351751470000ff98d050ec77a52050bf3cbb228f7a` - execution `ERROR` |
| Authorized marker | `0xdc2db87cb534288eb7bf5b736faaa1429133a62af7a1e29488770178ae8fc1a0` - `SUCCESS` | `0x968938e1c958fab7202884b1d4acdae9c9d2b6a4438eded221281dfe0f091458` - `SUCCESS` |
| Exact-source restore | `0x1553bd395db09142d001a241ec0b8f73f79de4a24b2196cf1cfe5212c7af394c` - `SUCCESS` | `0x6ae36fb9abdc005daa240a51c928805a4221ad089120caac619ac69076484f44` - `SUCCESS` |

Registrar wiring tx
`0x46d2fd2c6ead6316ae37650d8c9b0a3429221706d8f429608332699d3e3dc5ab`
also finalized successfully. The Root integration test passed:

```text
genvm_tests/integration/test_saleproof_network.py::test_studionet_root_upgrade_rehearsal PASSED
1 passed, 1 deselected in 404.62s
```

After restore, both rehearsal contracts matched the release source hashes,
their marker views were absent, Root membership/config were preserved, and the
seeded merchant/product/observation/sale/claim state matched its pre-upgrade
snapshot.

## Multi-wallet release journeys

Actors:

- merchant/owner: `0x666d6A7dCA1319caDcC7fB6b10DAB55cD8e128Dc`
- buyer/appellant: `0xa52A403Bb4fB8D79625bb8A3481e0e27a2428CC1`
- watcher/exit merchant: `0x6fe25379e202A6A7bdBBF85F0941CFc837BFDb92`
- second merchant/watcher: `0xf3246E8699cE88795c14E0044851c775d08a824C`

Every successful transaction below is `FINALIZED` with actual leader
`SUCCESS`. Guard probes are explicitly marked as execution errors.

| Branch | Key transaction evidence |
|---|---|
| Primary merchant deposit/register | `0xcd3323e8e470774ad321cd905476b04353ec60b64cdcdf49277ef3091f6606b7`, `0xf31cbaa72867cf2fe4c4a504ecc78355e0c067ab2d2d0608496a1b1aecf00843` |
| Primary product + triggered ledger registration | `0xe0c5e5df2922e023a3df02c85a98ad8d31be9bf1cf66cae09d0e82bef9796a58`, `0xb2931577cf9827c33a65115886b5854dad97967b9a80f44e99b6224c9ef8989d` |
| Primary snapshots (three independent callers) | `0x29114ea12517bd4243caca1f8853f94dcb3e4e9afc0c8408e8e1e3ea8611a4de`, `0x9dd83fd7e0330763198aa5fb530ed71479bc8684f51fb709f448dda3641c1bae`, `0x8e0cfa16e9d3e7076a700e9c2592e6d0c8cca7e2d78c0171b8e2185ce92ec551` |
| Primary sale | `0xed4da9432341f81f05d4a7d7566b35abc367c60ff14d09d9aa48b320cf9125a1` |
| Buyer deposit/file claim | `0xf6619f0073547350d848551505a6c4737ad05952ed8c06e3a85f651b76a79a5f`, `0x331dfe538dc84443f53d1d6710df2d27cbd672b2213e4cf31ce24a298cb38613` |
| Duplicate guard | deposit `0x120cd8de9b40b1675e0a88845a2e50a351429b8fbb275d2b6638be88ed495c85`; business call `0x052512ce6742a6011246de7fa7b68fdd191885ecc754ff92fd946fcaba485553` finalized with `ERR_SALE_ALREADY_CLAIMED`; unchanged state/credit then withdrawal `0x9692be1479e7fda785274fb15a40789be39f882a585f80b7ffb8e5f3d103b66b` |
| Primary judge/finalize/settle | `0x3af833d254eea048d34f0247bf4d25b3b5418496b5196cd3cf21a5ccf8e71e4f`, `0x610c1da227ddeeecd8ca661a4c1e9a8fbba3ccdc334d028ab77be0496ca8212e`, `0x8b17130bb426ea3f2fc5dd9c07c06f0ed3d3c069df18e3d429fac086863abdc3` |
| Primary buyer withdrawal | `0x40c5b1190633d7076a9124e785192be713752b0520409d8b7fe8d8b1cb52dee7`, exactly `0.2 GEN`, withdrawable becomes zero |
| Appeal merchant deposit/register | `0xdd7b717da6c792626e4d0a3416382bbc9ac1ef44467f21c035c16e8994188567`, `0x2581a29283d434bf671f1cde94dadbbedceabeea49a9cbd5d74299dcef93fcf8` |
| Appeal product + triggered ledger registration | `0x84636280147c343315a58e4420e38282871b54a3da8761ef8891af180d97c523`, `0xbbfcc601c1e79dbf6ebc83154723b224e2555fb4b8049ff9b0b13ca6d3dc2334` |
| Appeal snapshots | `0xa586cb8a9cb59dd630e870e4a4f656f46aa88d67904e7801a87a974f9cd89cf9`, `0x69f1edb6d98d9bd2018e8e34d99b9583515f60eaac85834dacdc774cc25a048f`, `0xa8965f4228532440020b5f35383377b6ad9352afe5bb08445fd7cf5b8c29c165` |
| Appeal sale/deposit/file/judge | `0xd1a2020b51c9008c580cf39e4e54e11c1b3685b994e74608b43aa3138d7eee21`, `0xcb26e964f213058e04c2424ffdf355a60f307f23f1e21ea2d87fee52b2d9c20d`, `0xa24b2ad9882415d1067c0aa10aba4ee2b5fcec0b863e266a2f0c0c9e769b29f6`, `0xb6cc9f28963fd071078298af8620272156116cf53ae21dc19a212f9d49cec168` |
| Appeal deposit/appeal/judge_appeal | `0x6478a2b70d1da0576b3da6a3bf3f77e472e267b9073dc156e4a401457e82a756`, `0x3c99c8c6fde1961ebb876f0bf893d9a1da4fb216d13b35c2aeea522c106f9d4e`, `0x8ee548428afc0113e654dbd5f997cbb6dd1eb1ff62fed1a3d71029a6fbeca944` |
| Appeal settlement/merchant withdrawal | `0x3b762a222cc988476d69ee90bed61f42e3c642d47f9f8ee2f1913d97addfca8b`, `0x217987428146aa9b2438882d522be4dfcb66348e885bff6b4a02dd367aed03c7` |
| Voluntary exit register/top-up/withdraw bond/pull payment | `0xd35bb44f867f5eda71af0bbc7ed5d77c7ed03aef23dc116e49c0e6bd3ac9bf73`, `0x54f5268aff317fefd687f2c4959a30a19aa048befddb2afbe593727cf559c15e`, `0x770e7c22abc9c85914666d452c82ee0311e0f4e1e023036c2b373ba6d5061db8`, `0x6b7733e9715ff872a29401399075c44a666c9bf53bcce59653331e9ad90d43d3` |

Final chain outcomes:

- primary claim #1: `SETTLED`, `INFLATED_REFERENCE`, confidence `9950 bp`;
  reasoning cites the frozen on-chain low `5177` against reference `6500`;
  merchant bond `1.9 GEN`, one strike, still active;
- deterministic primary settlement: buyer credit `0.1 GEN` deposit plus
  `0.1 GEN` bond slash = `0.2 GEN`; withdrawal zeroed the entry;
- appeal claim #2: original `GENUINE`, appeal exercised through
  `judge_appeal`, final `GENUINE`, confidence `9200 bp`, then `SETTLED`;
- voluntary-exit merchant ended inactive with bond zero and withdrew
  `2.1 GEN`;
- duplicate claim did not change native balance, credit, claim count, or sale
  claim ID; the preserved prepaid credit was withdrawn.

Custody reconciliation:

```text
total entered:                6.90 GEN
total withdrawn:             2.45 GEN
contract balance:            4.45 GEN
remaining merchant bonds:    3.90 GEN
pool:                        0.55 GEN
unsettled claim liabilities: 0.00 GEN
prepaid/withdrawable:         0.00 GEN
remaining custody:           4.45 GEN
verified:                    true
```

## Frontend evidence

Local ignored environment:

```text
VITE_GL_NETWORK=studionet
VITE_LEDGER_ADDRESS=0xE14023EF575ce85Cd0a709DA3997483315BaEB40
VITE_BOND_ADDRESS=0x6BaFf2C558F20147ECDEc3867E59A172B4995a5b
```

`verify-live.mjs` passes against the release pair and asserts product #1 URL,
`GBP 5177`, merchant `Demo Shop`, bond `1.9 GEN`, one strike, sale reference
`GBP 6500`, discount `2000 bp`, claim `SETTLED / INFLATED_REFERENCE /
9950 bp`, deposit `0.1 GEN`, slash `0.1 GEN`, and buyer total `0.2 GEN`.
Only Studio RPC capacity error `-32006` is retried, using the server's bounded
`retry_after_seconds`; all other errors fail immediately.

The final production-build render check passed all five routes:

- `docs/screenshots/current/01-overview.png`
- `docs/screenshots/current/02-product.png`
- `docs/screenshots/current/03-sale.png`
- `docs/screenshots/current/04-claim.png`
- `docs/screenshots/current/05-merchant.png`

The live write check first exposed a real post-finalization stale-read defect.
Two successful diagnostic snapshots
(`0x3fab646d21012ba1e243994cc7f59cdc29211e30ad045fc236b6b1d951f14b24`,
count `3 -> 4`, and
`0x09f9e65ff35e98742fd35f8511bcbda92932947bf74f1e53bfdc86a93c6cd0ab`,
count `4 -> 5`) finalized on-chain while the same-page count remained stale.
The corrected page retries finalized observation reads at most eight times with
a three-second interval. Two unit regressions cover eventual success and
bounded exhaustion.

Final write evidence:

```text
burner: 0xF9D00fEb42F350F8150723B963071294aa965f83
snapshot tx: 0xe0b77653052b8dc4bfbaa55c84814ff3fb20c2b74e5086d5a67653df6c93c0f0
pending UI: transaction hash + validator consensus message
final UI: FINALIZED + SUCCESS
observation count: 5 -> 6 without page reload
WRITE CHECK: PASS
```

Screenshots:

- `docs/screenshots/current/06-write-pending.png`
- `docs/screenshots/current/07-write-final.png`
- `docs/screenshots/current/08-public-production-overview.png` — SHA-256
  `cb9ce7a7ca4c0075ab8158eedbb51463753f8ba51553bc9b5fa793b903034b9c`

## Public GitHub and Vercel release

| Field | Verified value |
|---|---|
| GitHub account / repository | `ldkfj` / [ldkfj/saleproof](https://github.com/ldkfj/saleproof) |
| GitHub branch | `master` |
| Public commit count after this evidence commit | `112` |
| Vercel user / team | `hongcham819-3406` / `gam` (`gam9`) |
| Vercel project | `gam9/saleproof`; root `frontend`; framework Vite |
| Production deployment | `dpl_Frb4LzmiYSSSCjQFDmt6MbibyXEo` / `READY` |
| Immutable deployment URL | `https://saleproof-42efboiqb-gam9.vercel.app` |
| Public production alias | [saleproof.vercel.app](https://saleproof.vercel.app) |
| Production network | `VITE_GL_NETWORK=studionet` |
| Production ledger | `VITE_LEDGER_ADDRESS=0xE14023EF575ce85Cd0a709DA3997483315BaEB40` |
| Production bond | `VITE_BOND_ADDRESS=0x6BaFf2C558F20147ECDEc3867E59A172B4995a5b` |
| Remote build | PASS; TypeScript + Vite, 494 modules |
| Public smoke check | PASS; `books.toscrape.com`, product #1 `6 snapshots / £51.77`, claim #1 `SETTLED / INFLATED REF` |

The public Overview also displayed claim #2 as `SETTLED / GENUINE` during a
complete read. Studionet temporarily returned capacity error `-32006` during
verification, so some aggregate refreshes omitted individual rows until the
next read. The independent bounded-retry chain verifier passed the exact pair;
this RPC-capacity behavior did not change finalized contract state.

## Final release scorecard

| Category | Result |
|---|---|
| Contract source and deployed-code parity | PASS |
| Studionet addresses and finalized deployment receipts | PASS |
| Constructor config, Root membership, and registrar wiring | PASS |
| Disposable authorized/unauthorized Root recovery rehearsal | PASS |
| Primary judgment, appeal, guard, exit, and pull-payment journeys | PASS |
| Deterministic settlement and custody conservation | PASS |
| Contract, Direct GenVM, schema, and network verification | PASS |
| Frontend typecheck, build, unit tests, lint, and five-route render | PASS |
| Real finalized UI write and eventual-read correction | PASS |
| Public GitHub history and presentation boundary | PASS |
| Production Vercel environment, build, alias, and smoke check | PASS |
| Final anonymous `POST_GITHUB_VERCEL_FINAL` review | PENDING |

## Remaining release gates

| Gate | Status |
|---|---|
| Contract source/deployment parity | PASS |
| Wiring and config readback | PASS |
| Disposable Root rehearsal | PASS |
| Primary, appeal, guard, exit, settlement, and custody journeys | PASS |
| Local frontend typecheck/build/tests/lint | PASS; 10 files / 43 tests |
| Fresh render/write evidence | PASS |
| Post-live anonymous co-review on `6054c84` | APPROVED |
| GitHub Presentation Gate and public push | PASS |
| Production Vercel environment/update/smoke check | PASS |
| Final anonymous co-review on exact post-release revision | PENDING |

## Historical evidence - superseded, never current

Initial Phase 4 pair:

- PriceLedger `0x26aA8E0af993665e02A14408f75221e1951926C1`
- MerchantBond `0xDa121e6fF503eC2F13101df37Cf05aD38E93544F`

Custody-incident pair:

- PriceLedger `0x6a3E79C7F9ec2f11C355bd19fcc99ef87412BaD0`
- MerchantBond `0x18e8029FC7e8d217167100C2b9E6983722124E18`

Neither pair may be used as current source, journey, frontend, or submission
evidence.
