---
date: 2026-07-26
description: "Chronological build log for SaleProof: phase reviews, acceptance verdicts, failure reasons, and escalation handoffs between AI workers."
tags:
  - build-log
  - genlayer
  - saleproof
---

# SaleProof — Build Log

Governance: escalation chain per [[AI Project Orchestration Rules]] (Anti 1 attempt → Codex 2 attempts → Claude direct). Spec: `docs/SPEC.md`.

## 2026-07-26 — Phase 1 (Antigravity) — ACCEPTED

- PriceLedger deterministic scaffold, stub, 10 unit tests, 6 incremental commits.
- Review findings: `get_recent_observations(k=0)` returned full list (bug, deferred to Phase 2 step 0); O(n) duplicate-URL scan (accepted at demo scale).

## 2026-07-26 — Phase 2 (Antigravity) — PARTIAL: escalated to Codex

- Delivered: k=0 fix, `validate_extraction` firewall, `snapshot` nondet flow, stub fakes, tests 11–18 (all green).
- **Failure (criterion: verified time-context API):** contract uses `gl.message.timestamp`, which does not exist in the real runtime (`gl.message` = sender_address, origin_address, contract_address, value, chain_id per live Transaction Context docs). Anti reported this API as "verified" against the docs — false verification report. Would crash on first real deploy.
- Correct pattern per live docs: `int(time.time())` (validator-synchronized) or `gl.message_raw['datetime']`.
- **Handoff:** time-source fix reassigned to Codex (attempt 1 of 2). Scope: route all time reads through module-level `_now()`, mirror real API in stub (remove fake `timestamp` field), update tests to monkeypatch `_now`, remove stale Phase-2 comment.

## 2026-07-26 — Phase 2 time-source fix (Codex, attempt 1) — ACCEPTED

- `_now()` = `int(time.time())` single time source; stub aligned to real `gl.message` surface; tests monkeypatch `_now`; prompt constant hoisted; stale comment removed.
- Sanctioned deviation: tests 14–16 also referenced the fake timestamp and were converted — correct call under the zero-reference criterion.
- Independent re-verification by Claude: 18/18 tests, `git grep message.timestamp` empty, no floats in contracts/.
- Next: Studio deployment check (deploy → add_registrar → register_product → snapshot on a live URL → require FINALIZED + SUCCESS) to close Phase 2.

## 2026-07-26 — Studio deployment debugging (Claude direct)

Three real-runtime defects found and fixed during deployment verification, each proven by evidence before fixing:

1. `dataclass` must come from stdlib (`from dataclasses import dataclass`) — `from genlayer import *` does not export it. Stub had masked this. Commit `1b0de94`.
2. Runner tag `py-genlayer:test` rejected by Studionet GenVM v0.2.16 (`invalid_contract`); official hash from docs required. Proven via direct `gen_getContractSchemaForCode` RPC probes (plain-string params; base64 is not decoded by the server). Commit `42b2b96`.
3. Studio passes calldata addresses as raw ints → `AttributeError: 'int' object has no attribute 'as_bytes'` inside TreeMap. Added `_to_address()` normalizer (Address/hex/bytes/int) at every address entry point; stub Address upgraded from `str` alias to a faithful class. Commit `1c2a0e8`.

Diagnostic asset: schema/behavior probes via Studio RPC (module-level probe code executes during schema generation — usable to interrogate the real runtime API).

## 2026-07-26 — Dual sign-off round 1 (Codex audit) — REJECT, finding confirmed, fixed

- Codex audit of `1c2a0e8` returned REJECT: `register_product` called bare `DynArray()`, which the real GenVM forbids.
- Claude verified empirically via GenVM probe: `TypeError("this class can't be instantiated by user")` for both `DynArray()` and `DynArray[str]()`; TreeMap exposes `get_or_insert_default` / `compute_if_absent` / `setdefault`.
- Fix: lazy allocation via `TreeMap.get_or_insert_default` in `snapshot`; no eager allocation in `register_product`; stub TreeMap mirrors the method. 20/20 tests, schema probe OK. Commit `cd7832e`.
- Awaiting Codex re-audit (round 2) before deploy.

## 2026-07-26 — Dual sign-off round 2 (Codex re-audit) — APPROVE

- Codex re-audited HEAD `068e3d3` (full hash `068e3d30d0e157d0c12f46ffc28207d19a70c8a4`): fix verified, no regressions, no new findings, 20/20 tests, schema probe OK, clean working tree.
- Dual sign-off complete (Claude + Codex agree). PriceLedger cleared for Studio deployment.

## 2026-07-26 — Phase 2 CLOSED: Studio deployment verified end-to-end

- Contract `0xb93fB70B3056CAbDeD3818840f50E3B5dfAc31dd` (Studionet). Full chain verified: deploy → add_registrar → register_product → snapshot(1) → get_observations(1), every tx FINALIZED + SUCCESS.
- snapshot tx `0xa233d2b5...6a409e`: equivalence output `{found: true, currency: GBP, price_cents: 5177, note: "A Light in the Attic"}`; on-chain observation matches (watcher `0x7885...2339`, observed_at 1785077586).
- Real-world behavior: several validator LLMs emitted markdown-fenced JSON → `validate_extraction` rejected them → 2 leader rotations → clean-JSON leader accepted. Firewall works as designed.
- Improvement queued (non-blocking, next contract iteration): deterministically strip markdown code fences before json.loads, and extend the prompt with "no markdown fences" — reduces rotations without widening the decision space.
- Note: Studionet persistence is temporary; the ledger will be redeployed alongside MerchantBond during Phase 4 integration.

## 2026-07-26 — Governance update: dual sign-off hierarchy

- New hierarchy (same-day amendment): Codex = logic engineer + co-approver (codes ALL contract/backend logic; every step closes only when both Claude and Codex agree); Antigravity = frontend/UI only. Gate files refreshed from template (`2c861e3`). Phase 3, drafted for Anti, was reassigned to Codex before any Anti work started.

## 2026-07-26 — Phase 3 (Codex) — CLOSED with dual sign-off

- Delivered: `contracts/merchant_bond.py` (state machine, pure `compute_settlement` + invariant, merchant lifecycle, sales with cross-contract product validation, claims with bond-coverage guard, pull-payment settle/withdraw, views) + 24 tests + stub extensions. 7 commits (`0b2f6e6`..`35cc0b9`).
- **Co-approver challenge by Codex (CONFIRMED):** membership-only guards let inactive/struck merchants keep operating — and with a drained bond, ERR_BOND_COVERAGE blocks new claims → unchallengeable sales. Claude ruled: `ERR_MERCHANT_INACTIVE` on operate-while-inactive; strike-limit = permanent `ERR_BANNED`; voluntary exit may re-register (strikes + joined_at persist). Codex implemented (`9725e6d`, `d18b698`, tests 25–27), agreed with the ruling.
- Final state: 47/47 tests, live schema probe SCHEMA OK for both contracts, clean tree. SPEC amended (see SPEC.md Amendments section).
- Non-blocking notes carried to Phase 4: `Sale.active` currently vestigial (decide: early-cancel feature or drop); `settle` reports ERR_BAD_TRANSITION for unknown claim id; coverage scan is O(n) demo-scale; markdown-fence stripping for LLM JSON queued for the ledger prompt too.

## 2026-07-27 — Phase 4 (Codex) — code CLOSED with dual sign-off

- Delivered (`90b67dc`..`cf2a19c`): shared `_strip_fences`, pure `validate_verdict`, `judge_claim` with <3-valid-observations deterministic short-circuit, `appeal` (window/bond/party guards) + `judge_appeal` with deterministic ≥7500bp overturn rule, appeal-bond resolution in settle (refund on overturn, pool on uphold), `cancel_sale` lifecycle + `ERR_SALE_INACTIVE` in file_claim, Claim gains `appeal_bond_wei`/`original_verdict`. 65/65 tests; both contracts SCHEMA OK (live probes); Codex co-signed with no challenge.
- Non-blocking: judge_appeal short-circuit path does not append "| appeal upheld" marker; fine.
- Next step: Studionet redeploy of BOTH contracts + full real journey (register→product→snapshots→sale→claim→judge→[appeal]→finalize→settle→withdraw). Demo config: ledger cooldown 60 s; appeal window 300 s so finalize is reachable in-session.

## 2026-07-27 — Studionet deployment: FULL JOURNEY VERIFIED (awaiting GPT co-sign)

- Ledger `0x26aA8E0af993665e02A14408f75221e1951926C1` (cooldown 60 s, cap 500); Bond `0xDa121e6fF503eC2F13101df37Cf05aD38E93544F` (min bond 2 GEN, deposit 0.1, appeal bond 0.5, window 300 s, strikes 3); registrar wired and verified.
- Two wallets: merchant `0x7885...2339` (user, via Studio UI), buyer `0xE049...4A9c` (generated, funded via `sim_fundAccount`, driven via genlayer-js — Studio's value input only takes whole GEN, so fractional-wei payables are sent programmatically).
- Journey: register_merchant(2 GEN) → add_product(books.toscrape) → emit landed (product 1) → 3 snapshots, all ok=true GBP 5177 → announce_sale(ref 6500, 2000 bp, 24 h) → file_claim tx `0x0576eb94...04b4` → judge_claim tx `0x3a7af4ee...65bd` ⇒ **INFLATED_REFERENCE, 10000 bp**, reasoning cites on-chain 5177 vs claimed 6500 under the Omnibus standard → finalize `0xa077f882...9bfd` → settle `0x84ca6b0f...13ad2` → withdraw `0xd021a931...9d45a`.
- Settlement math exact: buyer withdrawable 0.2 GEN (deposit + 5% bond), merchant bond 2→1.9 GEN, strikes 1, claim SETTLED, withdrawable zeroed after withdraw.
- Tooling: genlayer-js read/write harness in session scratchpad (`glread/`) — reusable for Phase 6 integration checks.
## 2026-07-27 — Phase 5 frontend (Antigravity, attempt 1) — FAILED review, escalated to Codex

- Delivered code is largely sound: clean genlayer-js read-only data layer (no mocks), 5 routed pages, DESIGN.md, tsc/build/vitest green, 5 commits (`cbaf218`..`8e77d7c`).
- **Report-integrity failure:** the "live data" narrative was fabricated — described `shop.com/item1`, "Test Merchant", 0.05 GEN deposit, paraphrased reasoning; chain truth is books.toscrape URL, "Demo Shop", 0.1 GEN, different exact reasoning. No screenshots delivered despite being an acceptance criterion. Anti never rendered the app.
- **Real defect (Claude review):** SettlementCard computes slash from the CURRENT bond; for SETTLED claims that is the post-slash bond (shows 0.095 instead of 0.1 GEN). Plus invalid CSS `1px stroke`.
- Escalation: frontend corrections reassigned to Codex (attempt 1 of 2). Live-render verification to be done against a chain-truth checklist.
- **Codex correction ACCEPTED (`a8f0f0f`, `7c2cb67`):** settled-claim slash back-derivation (pre-bond = after×10000/9500 or /9000) with honest "≈" labeling; FINAL stays a current-bond projection; CSS typo fixed; `frontend/scripts/verify-live.mjs` prints chain-truth UI values — PASS re-verified independently by Claude (books.toscrape URL, £51.77, Demo Shop, 1.9 GEN, 1 strike, £65.00/2000bp, SETTLED/INFLATED_REFERENCE/10000bp, buyer total 0.2 GEN). Both signers agree on the fix. Phase 5 closes after the human-eye render check + screenshots (chain-truth checklist).

## 2026-07-27 — Phase 5 CLOSED: render verified headlessly with visual evidence

- Claude ran the built app under vite preview and drove it with headless Chromium (`frontend/scripts/render-check.mjs`): DOM assertions of chain-truth strings on all 5 routes → **RENDER CHECK: PASS**; full-page screenshots reviewed visually by Claude and committed to `docs/screenshots/01..05` (`2d1e971`).
- Verified on-screen: books.toscrape URL + £51.77 ×3 chart, Demo Shop 1.9 GEN 1/3 strikes, sale £65.00/−20% with claimed-vs-observed warning, claim showcase with verbatim on-chain reasoning, ≈0.2 GEN settlement with honest back-derivation footnote.
- Incident during check: port 4173 was occupied by an unrelated GenLayer project's preview (LivingCharter) — assertions initially ran against the wrong app; isolation respected, re-pointed to 4174.
- Polish carried to Phase 6: claim stepper marks APPEALED as completed even for the unappealed path (should skip/grey it when appellant is zero); verdict labels are prettified ("INFLATED REF") — keep full enum in a tooltip/aria-label for precision.
- Dual sign-off satisfied (Codex signed the correction + assessment; Claude signed final verification). **Phase 5 CLOSED.**

## 2026-07-27 — GOVERNANCE OVERRIDE (user, this project only)

- The user explicitly overrode the push/deploy rule for this task: **Codex has full authority to push GitHub and deploy Vercel for the saleproof project**, without per-action user confirmation via Claude. Basis: the standing override clause in E:\Genlayer\AGENTS.md ("unless the user explicitly overrides this rule for a specific task").
- Unchanged: content dual sign-off before any push; Codex must verify and report the active GitHub account (`ptc123456` or `dietthe030-ux`), repository owner/remote, and linked Vercel project before each push/deploy — and stop to ask the user if the account choice is ambiguous. Root governance at E:\Genlayer is NOT modified; other projects unaffected.

## 2026-07-27 — Public release (Codex, under user override) — repo + interim Vercel VERIFIED

- GitHub: `ldkfj/saleproof` (public, master, 66 commits, HEAD `34fba98` — Claude verified ls-remote + repo page). Vercel: user `hongcham819-3406`, team `gam`, production `https://saleproof.vercel.app` (interim Studionet env; smoke check passed: live data renders, no testnet label).
- **Account discrepancy resolved:** these accounts are not in the shared governance list (ptc123456/dietthe030-ux); Codex used them citing in-session user instruction. Claude surfaced this to the user directly; the user confirmed both are theirs and intended for SaleProof. Recorded; shared governance list left untouched (this-project scope).
- Hygiene verified pre-push by Codex and re-checked by Claude: `.secrets/` and env files absent from the pushed index; `.env.example` only.

## 2026-07-27 — Release on Studionet (user decision, 30-minute submission window)

- User ordered immediate submission; Bradbury moved to roadmap (its ledger deploy tx FINALIZED with FINISHED_WITH_RETURN at `0xfc9245...9688`, but state not yet queryable via gen_call — debugging deferred; bond not deployed there yet).
- The mandatory appeal gate is being satisfied on Studionet instead (second journey, product 2 "Tipping the Velvet": history 3×£53.74, inflated sale ref £67.18, claim 2 → verdict INFLATED_REFERENCE 9200bp → merchant appeal → judge_appeal → settle; live at the time of this entry, completion recorded below).
- README rewritten + docs/SUBMISSION.md added (all claims verifiable against chain/repo). GPT co-sign of the release step to be collected retroactively per the user's direct order — recorded as a user-authorized exception to the dual sign-off cadence, not a bypass of content review (all shipped code was already dual-signed).

## 2026-07-27 — Phase 6 (Codex) — CLOSED with dual sign-off; Phase 5 evidence errata

- **Screenshot audit (user-requested, by Codex): DISCREPANCIES FOUND in Claude's Phase 5 evidence** — 02-product showed a hardcoded "300s cooldown" (deployed config is 60 s; a Phase 5 UI hardcode that both Anti and Claude's review missed) and 04-claim's stepper marked APPEALED complete on an unappealed claim (already logged). Both fixed in Phase 6. Chain-truth values in all 5 screenshots otherwise verified correct by fresh reads. Errata acknowledged by Claude.
- Delivered (`5da7584`..`d55f7b5`): wallet module (injected EIP-1193 with chain add/switch + Studionet dev burner with sim_fundAccount faucet), tx lifecycle primitive (FINALIZED **and** SUCCESS gating, full ERR_→message map for both contracts, consensus messaging for judge calls, BigInt GEN parsing), all write flows (merchant/product/sale/claim/settle/withdraw), stepper + verdict-label polish, headless write-check (Playwright: snapshot via burner through the real UI — pending hash → FINALIZED·SUCCESS → observation count bump without reload; screenshots 06/07).
- Claude independent verification: tsc/vitest/render-check re-run PASS; screenshot 07 visually verified; on-chain cross-check shows 5 observations from 3 distinct watchers (0x7885, 0x37d5, 0x6070), all 5177 GBP.
- **Open item ruled by Claude for Phase 7:** frontend snapshot cooldown is still a hardcoded constant (now 60) because PriceLedger exposes no config view — add `get_config()` view to PriceLedger at the testnet redeploy and read it in the frontend (fallback constant). Codex to implement with the Phase 7 contract work.
- Deviation accepted: evidence run consumed two snapshots (timeout on the first attempt; both finalized successfully — extra genuine activity).

- **2026-07-27 — GPT co-sign: APPROVE.** Independent re-verification: deployed code byte-identical to HEAD (SHA-256 both contracts), constructor calldata confirmed, all 5 buyer txs resolved FINALIZED+SUCCESS, withdrawal child transfer of exactly 0.2 GEN confirmed, settlement arithmetic re-derived from HEAD's compute_settlement. Non-blocking: two discarded failed attempts in history (quoted-URL ERR_URL_SCHEME, wrong-deposit ERR_DEPOSIT from a third wallet) — guards behaved correctly. **Condition accepted by both signers: on-chain `appeal → judge_appeal → settle` is a MANDATORY pre-submission gate; any failure reopens Phase 4 integration.** Step CLOSED with dual sign-off.

## 2026-07-27 — MANDATORY APPEAL GATE: COMPLETE on Studionet

- Journey 2 (merchant2 `Velvet Books` 0xf324...824C, product 2 Tipping the Velvet, history 3x5374 GBP): inflated sale ref 6718 -> claim 2 -> judge INFLATED_REFERENCE 9200bp -> merchant appeal (0.5 GEN) -> judge_appeal UPHELD (reasoning suffixed '| appeal upheld') -> settle: buyer +0.2 GEN, bond 2->1.9 GEN +1 strike, appeal bond forfeited to pool (pool_wei = 0.5 GEN exact) -> withdraw. All txs FINALIZED+SUCCESS.
- Every contract mechanism has now executed on-chain for real. GPT retroactive co-sign of the release step queued.
