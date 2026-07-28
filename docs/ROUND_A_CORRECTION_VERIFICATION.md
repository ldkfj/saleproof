# SaleProof Round A Correction — Codex Verification

## Status

**LOCAL CORRECTION VERIFIED — NOT YET A DEPLOYMENT/DUAL-REVIEW PACKAGE**

Attempt 2 at commit
`14d755ddbd58fa1d64ecd699afba79b3bf3112cf` was independently rejected by
Codex. The user limited Antigravity to two attempts, so Codex took over the
correction.

This document separates:

- checks that can be proved from local source and test execution;
- network checks that remain impossible until the corrected contracts are
  deployed on Studionet;
- historical evidence from the superseded contract pair.

No skipped integration test, historical transaction, or previous screenshot is
counted as evidence for the corrected release.

## Attempt 2 rejection findings

| Finding | Severity | Evidence at rejected revision | Correction |
|---|---|---|---|
| Leader could fabricate appeal `should_overturn` (`7499/true` or `7499/1`) | Blocking | Captured validator closure accepted an outcome inconsistent with the leader confidence/type | Validate leader payload, require exact bool, recompute both leader and validator outcomes |
| Direct consensus test did not exercise claimed mock responses | Blocking | Broad `.*` mocks were retained in insertion order; first response always won | Narrow mocks, clear between cases, strict mock use and pickling |
| Studionet integration test was not runnable | Blocking | Nonexistent imports, unused client, wrong factory/deploy assumptions | Real installed `gltest`/`genlayer-py` APIs; no automatic release deployment |
| Root stub modeled wrong failure class | Blocking | Unauthorized locked code mutation raised a user error | Unit stub raises VM-level failure |
| PriceLedger carried broken dead helper / dirty fix | Blocking | Undefined `hashlib` at committed HEAD, then an uncommitted import | Remove helper and import |
| Documentation/evidence mixed revisions and networks | Release blocking | Truncated spec; old addresses and different-network claims used as current context | Full spec/runbook/manifest; corrected Studionet-only release remains pending |

## Corrected local design

### Appeal consensus

The custom appeal validator now:

1. accepts only `gl.vm.Return`;
2. requires exact keys and an exact boolean `should_overturn`;
3. validates the leader verdict/confidence/reasoning;
4. recomputes the leader outcome from the 7,500-bp rule;
5. independently reruns, validates, and recomputes the validator result;
6. requires exact verdict and exact outcome agreement;
7. applies the 1,500-bp tolerance only after outcome agreement.

The downstream state transition branches only on the validated outcome.

### Time and dead code

Both contracts use one `_now()` helper:

```python
return int(datetime.now(timezone.utc).timestamp())
```

The validator-pinned datetime remains integer Unix seconds. The unused
`_url_key`/`hashlib` workaround is removed.

### Unit and Direct evidence

The local suite now covers:

- all settlement verdicts and exact conservation/bookkeeping;
- replayed settlement rejection;
- withdrawable zeroing before transfer;
- inactive, banned, voluntary-exit, and reactivation merchant paths;
- malformed/oversized/wrong-type verdict payloads;
- integer/address public-boundary representations;
- Root code replacement and ordinary-state persistence in the unit stub;
- real 7,499/7,500 appeal consensus cases, fabricated booleans, wrong types, and
  same-outcome-region tolerance under official Direct Mode fixtures.

The Direct suite has one documented, narrow private call hook for synchronous
cross-contract views because `genlayer-test==0.29.2` exposes no public equivalent.
It does not patch the loader, VM execution, time, file descriptors, or consensus
mock selection.

### Network evidence harness

`genvm_tests/integration/test_saleproof_network.py` contains two distinct gates:

- a read-only corrected-release check for Studionet chain/RPC, exact deployed
  source hashes, configs, Root membership, ledger link, and registrar link;
- an explicitly destructive Root rehearsal restricted to separate disposable
  addresses, proving unauthorized denial, marker upgrade, state preservation,
  and exact-source restore.

Both gates require explicit environment opt-in. Their default `SKIPPED` status
is safe behavior, not completed live evidence.

## Local verification results

Implementation HEAD at the time of the recorded run:
`5005cde0b331bccd0cdb5bacd77564bae734687e`.

| Gate | Result |
|---|---|
| PriceLedger lint/typecheck | `ok:true`; 13 methods; no type errors |
| MerchantBond lint/typecheck | `ok:true`; 21 methods; no type errors |
| Unit tests | `80 passed in 0.13s` |
| Direct Mode tests | `7 passed in 0.25s` |
| Integration default skip | `2 skipped in 0.02s` (expected: no corrected addresses/opt-in) |
| Studionet schema probes | both `SCHEMA OK` |
| Frontend typecheck | passed with no output |
| Frontend build | Vite production build passed; non-blocking chunk-size warning |
| Frontend Vitest | `2` files, `11` tests passed |
| Live script syntax | all three Node scripts passed `node --check` |
| Prohibited contract patterns | no message timestamp field, `message_raw`, `time.time`, `_url_key`, bare `DynArray()`, or bare `TreeMap()` |
| Final clean commit | recorded externally after the documentation-only commit |
| PriceLedger Git-blob SHA-256 | `61fccf91ef74ac0fd138aa6b56ee89fd957f299215266b3861b0c128cf96f392` |
| MerchantBond Git-blob SHA-256 | `5b0fa27b724643680c776eab867aa124a2f5a381f7f8c676bf2157d9c27d66bb` |

## Network and release evidence still required

- corrected Studionet contract pair;
- deployment/setup transaction hashes with FINALIZED + `SUCCESS`;
- constructor calldata and owner/upgrader readbacks;
- `gen_getContractCode` SHA-256 parity;
- disposable Root rehearsal transaction set;
- multi-wallet primary and appeal journeys;
- settlement and withdrawal conservation/readbacks;
- frontend environment, live-chain verifier, current screenshots, real write
  check, production deployment, and smoke check using the same pair;
- completed `deployments/README.md`;
- Codex approval and anonymous co-review AI approval of that same immutable
  package.

## Current verdict

**CHANGES REQUIRED for release.**

The code correction may become locally verified, but release approval is
withheld until the missing live evidence exists. The anonymous co-review AI
must not be sent placeholder addresses, superseded transactions, or this
in-progress revision as if it were a complete deployment package.
