# SaleProof Studionet Release Manifest

## Current status

**PRE-DEPLOY BLOCKED — corrected local revision verified; no current release
pair exists.**

The previously deployed pair is permanently superseded by the custody incident
recorded in `docs/BUILD-LOG.md`. It is not valid source, journey, frontend, or
submission evidence. No fresh contract address, deployment transaction, v2
release checkpoint, or frontend environment has been created.

The next permitted gate is anonymous co-review AI approval of the exact
pre-deploy revision. Only after that approval may Codex ask the user to select a
deployment/upgrader wallet, verify the active address, and explicitly confirm
each deployment action.

## Canonical network

Verified against the current official
[Networks documentation](https://docs.genlayer.com/developers/networks) on
2026-07-29.

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

## Reviewed pre-deploy revision

| Field | Value |
|---|---|
| Contract source freeze commit | `bccf236fb56cedb43715b753a0d48cc16ce50f87` |
| Frontend prepaid correction commit | `a0ce250` |
| Frontend anonymous-blocker correction commits | `5e29480` (implementation), `765f5d8` (core tests), `b8618e5` (page-level hardening) |
| Incident/spec evidence base | `8e3cf1a7ca8d4ed190910c6c2d3c64a8c9d84212` |
| Exact review-package commit | Supplied by `git rev-parse HEAD` after this manifest is committed; must have a clean tracked tree |
| PriceLedger SHA-256 | `61fccf91ef74ac0fd138aa6b56ee89fd957f299215266b3861b0c128cf96f392` |
| MerchantBond SHA-256 | `d7d20db98851ae3958bf810eac45b95bc796f1b942c4e7131992fa957bba753f` |
| SPEC SHA-256 | `db5df3cc0a4e9963b103ec028d6f4c177ad26cedb9e14ab7269c74940916d0e4` |
| GenVM dependency | `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6` |
| Contract classification | `UPGRADABLE` through the GenVM Root code slot |
| Recovery runbook | `docs/RECOVERY.md` |
| Codex pre-deploy verdict | APPROVED locally after correction; exact clean package commit must be supplied by `git rev-parse HEAD` |
| Anonymous co-review AI pre-deploy verdict | CHANGES REQUIRED on `b065863`; corrected exact-HEAD re-review PENDING |

The current official
[Upgradability documentation](https://docs.genlayer.com/developers/intelligent-contracts/features/upgradability)
still uses the pinned dependency and confirms that Root `upgraders` may replace
locked code while ordinary storage, locked slots, and the upgrader list persist.
The upgraded code must keep a compatible storage layout.

### Local verification

All checks below ran against the source hashes above:

| Check | Result |
|---|---|
| `py -3.13 -m pytest -q` | `97 passed` |
| `py -3.13 -m pytest genvm_tests/direct -q` | `8 passed` |
| `genvm-lint check` on both contracts | PASS; PriceLedger 13 methods, MerchantBond 22 |
| `genvm-lint typecheck` on both contracts | PASS; no type errors |
| Live Studio schema probe | PASS; constructor/method counts `3/13` and `7/22` |
| `npx tsc --noEmit` | PASS |
| `npm run build` | PASS; 494 modules, non-blocking chunk-size warning |
| `npx vitest run` | PASS; 10 files, 40 tests |
| `npm run lint` | Exit 0; three recorded pre-existing warnings |
| Release runner `node --check` and oxlint, both mirrors | PASS |

The prepaid frontend core hashes are:

- `frontend/src/lib/prepaid.ts`:
  `df3225e9c4360e33010b5e387499975800278077bf32c79598cdb7ccf4c6f02e`
- `frontend/src/lib/prepaid.test.ts`:
  `793626087ce344db6a0d2004ea215c3c1a5ccb910fdd7c0028ead27575d6138b`
- `frontend/src/components/PrepaidTxAction.tsx`:
  `c8e4ec896266662557b6a24786614291b59801a9bde53c2866a6ea10a59e41bf`

The anonymous-blocker correction frontend hashes are:

- `frontend/src/lib/contracts.ts`: `81a89902d5a7b09ac1ef467836a6c109b93820da1717c658ec36e4958cd3dbb6`
- `frontend/src/lib/sale.ts`: `f1230f05cd80b6fece02dc4c3f25752c1bf7e190d939f9a8195a1e0ed5103f6f`
- `frontend/src/lib/sale.test.ts`: `29aede1b69ec9c5b83baa1dd26b407e801ebf2a8e35fdc1f91557fab10d8ab91`
- `frontend/src/lib/contracts.test.ts`: `6628db309e53eded587645fe819178f1d88ea269550e506525e9a5611286e0a2`
- `frontend/src/lib/product.ts`: `0dccc773564a8a4a09eedace2d615101620c5427312c4614a839fabf6b59875f`
- `frontend/src/lib/product.test.ts`: `f4e72dfa55501020054ddeef4ff23b0b3569f08f3bd6bad303360f0842c7ab2d`
- `frontend/src/components/AnnounceSaleForm.tsx`: `98d658faed1fecca7f0653a5a65d5998f57f4510565ffec866b2f25e7f85387b`
- `frontend/src/components/AnnounceSaleForm.test.tsx`: `26d4b2408de167278742c16ea97be0b26fb7ea441347ed85592fa18678aabf27`
- `frontend/src/components/AddProductForm.tsx`: `0ad26395bda412ef59ec5a355bca120a43e2ad83f30d4f22773408983801427d`
- `frontend/src/components/MerchantSetupActions.tsx`: `7f4a4c6726be677a65d6dc32505893a644fdeafd3a3a6bd240168470cd3bcbd1`
- `frontend/src/components/MerchantSetupActions.test.tsx`: `ce1bd2dd5381ab390b4aef92e3bf471d10cc6eecca76e09d7edf2e44fb846763`
- `frontend/src/pages/Overview.tsx`: `c5f51f13baaa69a455903cafa0ab0fb6fdbcdf39effda30fb0b6a42fd13c0772`
- `frontend/src/pages/Overview.test.tsx`: `c7b60d867d7a9ae4487b864c6dad6e3a3b5a4fc93e5aa2c279fcf21d2d27bd37`
- `frontend/src/pages/SaleDetail.tsx`: `3d5be8ad4cbd6aade6f9685a18c37e6bb3e3d8c5af44dfb5967c90acf5e4ca5e`
- `frontend/src/pages/MerchantDetail.tsx`: `a9903a42c39d0bd66504a5a16eb5689b76ca6526fd262c1eb9e196bef7ad0fbe`

The two ignored local release-runner mirrors are byte-identical at SHA-256
`aea58bcc75860f80b9522b0cf2aed26452f05a405b2df12af57525e39fc3245d`.
They are opt-in, reject the superseded release addresses, and cannot send a
positive value through generic retry helpers. Only the dedicated
single-submission `depositStep` can send GEN.

## Pre-deploy authorization gate

| Requirement | Status / evidence |
|---|---|
| Explicit classification | PASS — both contracts are `UPGRADABLE` |
| Current official network/API/header check | PASS — rechecked 2026-07-29 |
| External user-controlled Root upgrader | PENDING user selection; no prior wallet choice is inferred |
| Public upgrade path | PASS — both contracts expose `upgrade(new_code: bytes)` |
| Storage compatibility plan | PASS — no field was removed, reordered, renamed, or retyped; existing `withdrawable` storage is reused as prepaid credit |
| Upgradability regression tests | PASS locally; disposable live rehearsal required again for the changed MerchantBond source before post-deploy acceptance |
| Secret-free draft manifest | PASS — this file contains no private key or placeholder address presented as real |
| Studio/local and Studionet reset recovery | PASS — `docs/RECOVERY.md` |
| Anonymous pre-deploy checkpoint | CHANGES REQUIRED on `b065863`; corrected exact-HEAD re-review PENDING |
| User-selected deployment wallet and explicit deployment confirmation | PENDING |

No deployment transaction is authorized while either of the last two rows is
pending.

## Required identity and authorization

| Field | Current value |
|---|---|
| User-selected deployment wallet / owner | PENDING — must be selected again for the fresh pair |
| Verified active deployment address | PENDING — derive from the configured key without printing the key |
| User-selected Root upgrader wallet | PENDING — may equal owner only if the user explicitly chooses it |
| Verified Root upgrader address | PENDING |
| Explicit PriceLedger deployment confirmation | PENDING |
| Explicit MerchantBond deployment confirmation | PENDING |
| Explicit registrar-write confirmation | PENDING if requested under the final action plan |

Approvals for any earlier pair do not carry over.

## Intended constructor arguments

PriceLedger:

```text
upgrader_address: PENDING — exact user-selected external wallet
snapshot_cooldown_s: 60
max_observations: 500
```

MerchantBond:

```text
upgrader_address: PENDING — exact user-selected external wallet
ledger: PENDING — the fresh verified PriceLedger address
min_bond_wei: 2000000000000000000
claim_deposit_wei: 100000000000000000
appeal_bond_wei: 500000000000000000
appeal_window_s: 300
strike_limit: 3
```

No fake address may be encoded or written to a real `.env`. MerchantBond may be
deployed only after the fresh PriceLedger address is real, finalized with
leader `SUCCESS`, source-matched, and config-read back.

## Fresh release deployment record

| Field | PriceLedger | MerchantBond |
|---|---|---|
| Address | PENDING | PENDING |
| Deployment transaction | PENDING | PENDING |
| Sender / owner | PENDING | PENDING |
| Registered Root upgrader | PENDING | PENDING |
| Final transaction status | PENDING | PENDING |
| Actual leader execution result | PENDING | PENDING |
| Explorer link | PENDING | PENDING |
| `gen_getContractCode` SHA-256 | must equal `61fccf...f392` | must equal `d7d20d...753f` |
| Local/deployed source parity | PENDING | PENDING |
| Constructor/config readback | PENDING | PENDING |

Every actual field must be filled from sanitized finalized evidence. Raw
receipts may contain sensitive node configuration and must not be printed or
committed.

## Pair wiring

| Check | Status |
|---|---|
| MerchantBond config points to the fresh PriceLedger | PENDING |
| `PriceLedger.add_registrar(fresh MerchantBond)` | PENDING |
| Registrar transaction is FINALIZED with actual leader `SUCCESS` | PENDING |
| `PriceLedger.is_registrar(fresh MerchantBond) == true` at `LATEST_FINAL` | PENDING |
| Both owners match the selected deployment wallet | PENDING |
| Both `is_upgrader(selected wallet) == true` | PENDING |

Required order:

1. deploy and verify PriceLedger;
2. deploy and verify MerchantBond with that exact ledger address;
3. wire and verify registrar membership;
4. complete the disposable Root rehearsal for the exact current source;
5. run the multi-wallet custody and adjudication journeys;
6. configure and verify the frontend only from the accepted manifest.

## Disposable Root rehearsal

Post-deploy acceptance requires a separate test deployment and cannot use the
release contracts for marker code. The earlier PriceLedger source is
byte-identical to the current source, but MerchantBond changed. Therefore the
prior rehearsal is preserved only as historical evidence below; it does not by
itself close the current pair's post-deploy rehearsal gate.

The current rehearsal must prove, for both exact source hashes:

1. unauthorized upgrade finalizes without execution success and code is
   byte-identical afterward;
2. authorized marker upgrade finalizes with leader `SUCCESS`;
3. marker view works and all snapshotted ordinary state is preserved;
4. exact reviewed source is restored with leader `SUCCESS`;
5. source bytes, Root membership, config, and ordinary state match the
   pre-rehearsal snapshot.

Current-source rehearsal addresses and all denied/marker/restore transactions:
PENDING.

## Live journey proof matrix

Every row must use the fresh pair, more than one wallet, sanitized transaction
evidence, `FINALIZED` plus actual leader `SUCCESS` for successful writes, and
`LATEST_FINAL` readback.

| Actor / branch | Required method sequence | Transaction/readback |
|---|---|---|
| Merchant registration/bond | `deposit` then nonpayable `register_merchant(name, bond_wei)` | PENDING |
| Merchant top-up recovery | `deposit` then nonpayable `top_up_bond(amount_wei)` | PENDING |
| Product registration | `add_product` and triggered ledger registration | PENDING |
| Independent watcher history | three or more `snapshot` writes | PENDING |
| Sale announcement | `announce_sale` | PENDING |
| Buyer canonical claim | `deposit` then nonpayable `file_claim(sale_id, deposit_wei)` | PENDING |
| Duplicate-claim guard | nonpayable duplicate fails with no native/credit/state delta | PENDING |
| Primary judgment | `judge_claim` | PENDING |
| Appeal funding and secondary judgment | `deposit`, nonpayable `appeal`, `judge_appeal` | PENDING |
| Unappealed terminal branch | separate claim and `finalize_unappealed` | PENDING |
| Permissionless settlement | third-party `settle` | PENDING |
| Pull payments | buyer/appellant/merchant `withdraw`; entries zero afterward | PENDING |
| Custody conservation | deposits = withdrawals + remaining bonds/claims/appeals/credits/pool = contract balance | PENDING |

No pending, failed, validator-only, or mismatched-source transaction may satisfy
a successful row.

## Frontend and public-release evidence

| Field | Required current value |
|---|---|
| `VITE_GL_NETWORK` | `studionet` |
| `VITE_LEDGER_ADDRESS` | PENDING fresh accepted ledger |
| `VITE_BOND_ADDRESS` | PENDING fresh accepted bond |
| Production Vercel URL | PENDING user-selected team and explicit confirmation |
| `verify-live.mjs` | PENDING fresh pair |
| Render/write checks and screenshots | PENDING fresh pair |
| GitHub exact public commit | PENDING user-selected account and explicit push confirmation |
| GitHub Presentation Gate | PENDING |
| Final anonymous co-review AI verdict | PENDING |

Existing Vercel data, `.env`, screenshots, or Explorer links for a superseded
pair are not current evidence.

## Historical evidence — superseded, never current

### Initial Phase 4 pair

- PriceLedger `0x26aA8E0af993665e02A14408f75221e1951926C1`
- MerchantBond `0xDa121e6fF503eC2F13101df37Cf05aD38E93544F`

### Custody-incident pair

- PriceLedger `0x6a3E79C7F9ec2f11C355bd19fcc99ef87412BaD0`
  - deploy tx
    `0x5245b07d5ecfee24f6c423a10d16398320918fdf75d993aec75d06b453884dcc`
  - source SHA-256
    `61fccf91ef74ac0fd138aa6b56ee89fd957f299215266b3861b0c128cf96f392`
- MerchantBond `0x18e8029FC7e8d217167100C2b9E6983722124E18`
  - deploy tx
    `0xe3cb5c67f52df04b173c160767228735a8d9a50f62b96baf82c3d05ea0dd77c9`
  - source SHA-256
    `5b0fa27b724643680c776eab867aa124a2f5a381f7f8c676bf2157d9c27d66bb`
- registrar tx
  `0xb01f8b1ddc27adb33374d16c5ec11e50c8f8ade3e730febaa496c9ed9d2f7166`
- duplicate payable claim tx
  `0x6d5d3f894ad38f2fa56a42ca3d13726ece95104f0404cd81d300612f9300abaf`
  finalized with `ERR_SALE_ALREADY_CLAIMED` while transferring an orphaned
  `0.1 GEN`.
- preserved incident checkpoint SHA-256
  `9ddd88620a026179dba0409b0c6dc5fa6cf70a9d3626728f65078258e80030d9`

### Prior disposable rehearsal for the superseded Bond source

| Evidence | PriceLedger rehearsal | MerchantBond rehearsal |
|---|---|---|
| Disposable address | `0xe6227B6C8305EEbdd6468cf4206C18e87bFB19f2` | `0xBAd98e2A9f116A330E6Da062397775752eFC60dE` |
| Unauthorized upgrade tx | `0xe2e05e55e90b1631ddd5f6c6c4918dc12a7b9980f26c28534f7ce10860f86bd5` | `0xf0ef12303f60215042d4b73b0adccf73276dd6d385d0e14fb9896ae2bfb98ed0` |
| Authorized marker tx | `0xe9c63c1f3fed16e9336c8148a5d0db25da7f9fc47520e205514acbcc10a753a9` | `0xcaae601663c29e7b84cdedbfbc54fd159a66842eacf8f78d3e8e92425fecfb4f` |
| Exact-source restore tx | `0xc2ab93448f4567f518d954fcea59c5e7e716356d24ed70ee69a8e530e65c5d0a` | `0x055a36e032895e355ba350739cbd9fb97f3bbaff4255b3b72440f21565322577` |
| Restored source SHA-256 | `61fccf...f392` | `5b0fa2...66bb` — not the current MerchantBond |

Full historical readbacks and incident analysis remain in
`docs/BUILD-LOG.md`; they are retained for audit continuity, not release claims.
