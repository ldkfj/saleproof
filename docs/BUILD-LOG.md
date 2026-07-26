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
