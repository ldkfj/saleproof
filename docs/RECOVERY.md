# SaleProof Recovery and Root-Upgrade Runbook

## Status and scope

Both contracts are classified **UPGRADABLE** through GenVM Root storage. This
runbook covers the current Studionet release only. It does not grant deployment
authority and must not be treated as evidence that a rehearsal occurred.

Code replacement preserves ordinary storage bytes; it does **not** perform an
automatic schema migration. A change that alters the existing storage layout
requires a separately designed and reviewed migration or a new contract pair.

## Authority model

Each constructor receives `upgrader_address`. The contract registers that
external address in:

```python
gl.storage.Root.get().upgraders
```

`owner` is the normalized deployment sender. Owner-only registrar administration
in PriceLedger does not imply Root upgrade authority. Owner and upgrader may be
different wallets.

Both upgrade methods use only:

```python
root = gl.storage.Root.get()
code = root.code.get()
code.truncate()
code.extend(new_code)
```

Authorization is enforced by GenVM's locked code slot. There is no contract
method to add/remove an upgrader and no on-chain rollback history.

## Required release record

Before any upgrade or recovery operation, create an evidence record containing:

- exact Git commit and clean-tree status;
- SHA-256 of both local UTF-8 source files;
- runner hash from the first source line;
- network name, chain ID `61999`, RPC, and explorer;
- current PriceLedger and MerchantBond addresses;
- original deployment and registrar transaction hashes;
- deployment sender/owner and registered upgrader address;
- constructor arguments and config readbacks;
- `gen_getContractCode` source and SHA-256 for both contracts;
- product/sale/claim counts and all material state needed for post-checking;
- wallet performing each authorized or unauthorized rehearsal step;
- every transaction hash, final status, execution result, and readback.

Never put a private key, seed phrase, `.env`, or CLI account file in this record
or repository.

## Preflight

1. Stop frontend writes and announce a maintenance window.
2. Confirm the repository and intended commit:

   ```powershell
   git status --short
   git rev-parse HEAD
   git diff --check
   ```

3. Re-run local gates:

   ```powershell
   genvm-lint check contracts/price_ledger.py --json
   genvm-lint check contracts/merchant_bond.py --json
   genvm-lint typecheck contracts/price_ledger.py
   genvm-lint typecheck contracts/merchant_bond.py
   python -m pytest tests -v
   python -m pytest genvm_tests/direct -v
   python scripts/schema_probe.py --rpc https://studio.genlayer.com/api
   ```

4. Compare the new class/storage annotations against the deployed revision.
   Stop if an existing field was removed, reordered, renamed, or retyped.
5. Confirm the active wallet is the recorded Root upgrader. Do not infer this
   from ownership.
6. Read and archive current configs, counts, registrar membership, material
   records, withdrawable balances, and `gen_getContractCode` for both contracts.
7. Verify no transaction is merely pending or accepted. Evidence requires
   FINALIZED status and an actual receipt with `mode="leader"` whose
   `execution_result` is `SUCCESS`. A validator receipt cannot substitute for
   the leader result. All state readbacks used as evidence must explicitly use
   `LATEST_FINAL`.

Current Studionet accepts the legacy source request
`gen_getContractCode([address])` but rejects the generic-node object form that
carries a finalized status. Therefore source parity is valid only when that
legacy read is coupled to the immediately verified FINALIZED, leader-`SUCCESS`
deploy/upgrade transaction, writes remain paused, and the evidence record proves
that no intervening upgrade occurred.

## Mandatory disposable Studionet rehearsal

Never rehearse marker code against release contracts. Deploy a dedicated,
disposable PriceLedger/MerchantBond pair using the same reviewed source and
upgrader arrangement, then wire its registrar.

Set only local process environment values:

```powershell
$env:SALEPROOF_RUN_STUDIONET_UPGRADE_REHEARSAL='1'
$env:SALEPROOF_STUDIONET_LEDGER_ADDRESS='<release ledger; exclusion guard>'
$env:SALEPROOF_STUDIONET_BOND_ADDRESS='<release bond; exclusion guard>'
$env:SALEPROOF_STUDIONET_REHEARSAL_LEDGER_ADDRESS='<disposable ledger>'
$env:SALEPROOF_STUDIONET_REHEARSAL_BOND_ADDRESS='<disposable bond>'
$env:SALEPROOF_STUDIONET_REHEARSAL_PRODUCT_ID='<seeded product with observation>'
$env:SALEPROOF_STUDIONET_REHEARSAL_MERCHANT_ADDRESS='<seeded merchant>'
$env:SALEPROOF_STUDIONET_REHEARSAL_SALE_ID='<seeded sale>'
$env:SALEPROOF_STUDIONET_REHEARSAL_CLAIM_ID='<seeded claim>'
$env:SALEPROOF_STUDIONET_UPGRADER_PRIVATE_KEY='<local secret; never record>'
$env:SALEPROOF_STUDIONET_UNAUTHORIZED_PRIVATE_KEY='<different local secret; never record>'
gltest genvm_tests/integration/test_saleproof_network.py -k root_upgrade_rehearsal -v --network studionet --rpc-url https://studio.genlayer.com/api
```

The private-key variables are consumed only from the process environment: the
first wallet must be the registered upgrader and the second must be a different,
unauthorized wallet. Never echo or persist either value. All four
release/rehearsal addresses are mandatory, nonzero, and pairwise distinct. The
rehearsal bond must reference the rehearsal ledger. Before running, seed the
disposable pair with a linked product observation, merchant, sale, and claim
(the sale must reference that product and merchant, and the claim must reference
that sale). The gated test performs this sequence for both contracts:

1. snapshot config, counts, product/observations, merchant, sale, claim, and
   relevant withdrawable records;
2. attempt marker-code replacement with the unauthorized wallet;
3. require a finalized failed execution and byte-identical deployed code;
4. replace code with the authorized wallet;
5. require FINALIZED + `SUCCESS`;
6. read a new marker view and re-read ordinary state;
7. replace marker code with the exact reviewed source;
8. require FINALIZED + `SUCCESS`;
9. compare deployed source bytes and state with the pre-rehearsal snapshot.

Record all four denied/authorized/restore transaction sequences. A skipped test
does not satisfy this gate.

## Release-contract upgrade procedure

Only proceed after the disposable rehearsal and dual approval of the exact new
source:

1. Re-read release source SHA and state snapshot.
2. Connect the recorded Root upgrader wallet.
3. Upgrade **PriceLedger first** with the exact reviewed
   `contracts/price_ledger.py` UTF-8 bytes.
4. Wait for FINALIZED and execution `SUCCESS`.
5. Read deployed code, config, count, representative products/observations, and
   registrar membership. Stop on any mismatch.
6. Upgrade **MerchantBond second** with the exact reviewed
   `contracts/merchant_bond.py` bytes.
7. Wait for FINALIZED and execution `SUCCESS`.
8. Read deployed code, config, counts, representative merchants/sales/claims,
   pool and withdrawable values. Stop on any mismatch.
9. Run the read-only integration gate:

   ```powershell
   $env:SALEPROOF_RUN_STUDIONET_INTEGRATION='1'
   $env:SALEPROOF_STUDIONET_LEDGER_ADDRESS='<release ledger>'
   $env:SALEPROOF_STUDIONET_BOND_ADDRESS='<release bond>'
   $env:SALEPROOF_STUDIONET_OWNER_ADDRESS='<deployment owner>'
   $env:SALEPROOF_STUDIONET_UPGRADER_ADDRESS='<Root upgrader>'
   gltest genvm_tests/integration/test_saleproof_network.py -k corrected_studionet_source_and_config -v --network studionet --rpc-url https://studio.genlayer.com/api
   ```

10. Resume frontend writes only after fresh end-to-end read and write smoke tests.

## Failure and rollback rules

- **Unauthorized upgrade succeeds:** stop immediately, mark the pair compromised,
  disconnect the frontend, preserve all evidence, and redeploy a reviewed pair.
- **Authorized transaction is not FINALIZED + `SUCCESS`:** do not retry blindly.
  inspect the receipt/trace, confirm deployed code did not change, then issue a
  separately reviewed retry.
- **Code changed but source hash mismatches:** disconnect frontend writes and use
  the registered upgrader to restore the last reviewed exact source. Re-read
  state before any other action.
- **State changed or cannot decode after upgrade:** do not layer another schema
  change on top. Preserve evidence and redeploy/migrate under a new reviewed plan.
- **Only one of the two contracts upgraded:** pause user writes. Restore that
  contract to the previous compatible pair or complete the reviewed second
  upgrade after determining compatibility.
- **Upgrader key unavailable:** the existing contracts cannot be recovered
  through owner methods. Deploy a new pair and relink.

Because Root stores no code history, “rollback” means submitting previously
reviewed exact source bytes and then repeating source/state verification.

## Studio/local workspace recovery without chain reset

Loss of browser storage, a Studio workspace entry, the local `.env`, or a local
checkout does not by itself mean the on-chain pair was lost. If both recorded
addresses still expose code and finalized state, recover the workspace instead
of redeploying:

1. stop frontend writes and leave production addresses unchanged;
2. restore the exact recorded Git commit in a clean checkout and recompute both
   source hashes;
3. reconnect the user-selected, recorded wallet and verify its active address
   against the manifest owner and Root-upgrader readbacks; never infer identity
   from the browser profile or place its key in the repository;
4. in Studio, reopen or import each contract by its recorded address when the UI
   supports that flow; otherwise reconstruct the read-only workspace through the
   recorded Studionet RPC and exact source without sending a transaction;
5. explicitly read `LATEST_FINAL` config, counts, representative state,
   `is_upgrader`, MerchantBond-to-ledger linkage, and registrar membership;
6. read deployed code using the Studio-compatible legacy request and apply the
   finalized/no-intervening-upgrade coupling defined in Preflight;
7. restore local frontend variables only from the verified manifest, then run
   `verify-live.mjs` and the render check before resuming writes.

If source differs but state is readable, do not redeploy or submit a blind
upgrade. Enter a maintenance window and use the release-contract upgrade
procedure after review, wallet verification, and the user's explicit deployment
confirmation. If code/state is actually absent or the pair cannot be verified,
follow the reset procedure below.

## Studionet reset or lost state

Studionet may reset. If either address loses code/state or the pair no longer
links correctly:

1. mark both addresses and all prior screenshots/journeys as superseded;
2. do not reuse one surviving contract with an unverified replacement;
3. deploy PriceLedger from the reviewed commit;
4. deploy MerchantBond with that new ledger address;
5. authorize MerchantBond as registrar;
6. read back configs, Root membership, registrar membership, and source hashes;
7. replay the required multi-wallet primary and appeal journeys;
8. create a new manifest section—never overwrite historical transaction facts;
9. update frontend environment only after all addresses are real and verified.

## Frontend relinking

For the current release, the production/runtime environment must contain:

```text
VITE_GL_NETWORK=studionet
VITE_LEDGER_ADDRESS=<verified corrected ledger>
VITE_BOND_ADDRESS=<verified corrected bond>
```

Then:

1. build from the same reviewed commit;
2. run `node scripts/verify-live.mjs` against those explicit environment values;
3. run the gated render check and inspect fresh screenshots;
4. confirm wallet network ID `61999`, explorer links, cooldown config, counts,
   and representative claim/settlement readbacks;
5. deploy only with the user's required authorization;
6. smoke-check the deployed site and repeat chain readback.

The previous `.env`, ignored `dist`, Vercel environment, or screenshot set is
never proof of relinking.
