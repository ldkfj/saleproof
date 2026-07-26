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
