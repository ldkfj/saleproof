---
date: 2026-07-27
description: "Submission notes for SaleProof — what it does, the trust problem, why GenLayer is required, and a 5-minute reviewer walkthrough with live addresses."
tags:
  - submission
  - genlayer
  - saleproof
---

# SaleProof — Submission Notes

## What it does

SaleProof checks whether a merchant's advertised discount is real. Merchants put a GEN bond behind their sales. Anyone can snapshot a product page's price into an on-chain history. When a buyer challenges a sale as fake, GenLayer validators read the live product page, compare it with the recorded price history, and reach consensus on a verdict that pays the buyer from the merchant's bond.

## The problem it solves

Fake sales — raising the "original" price right before a promotion so the discount looks bigger — are illegal in much of the world (the EU requires discounts to be measured against the lowest price of the prior 30 days) but almost never enforced. Buyers lose money, honest merchants lose trust, and marketplaces earn from sale events, so none of them can be the referee.

## Why GenLayer is required

The verdict needs two things at once: trustless reading of a live web page (at snapshot time and again at judgment time), and a subjective call — "is this discount materially honest given the price history?" — that no single party should make. Ordinary smart contracts can do neither; an off-chain AI service would just be another party you have to trust. In SaleProof both the evidence gathering and the judgment run inside Intelligent Contracts under validator consensus.

## The concrete build

- **Contracts (in this repo):** [`contracts/price_ledger.py`](../contracts/price_ledger.py) — append-only price-observation log; anyone can `snapshot(product_id)`; validators render the page (`gl.nondet.web.render`), an LLM extracts the price to strict JSON, and a deterministic firewall rejects anything malformed. [`contracts/merchant_bond.py`](../contracts/merchant_bond.py) — bonds, sales, claims, appeals, settlements in an explicit state machine (`OPEN → JUDGED → (APPEALED →) FINAL → SETTLED`).
- **Key nondeterministic decision:** `judge_claim` — validators fetch the live page, receive the serialized on-chain history, and judge the merchant's claimed reference price against the 30-day-low standard, returning one of four graduated verdicts (`GENUINE`, `INFLATED_REFERENCE` → 5% bond slash, `DECEPTIVE` → 10% slash, `INSUFFICIENT_EVIDENCE`) with written reasoning stored on-chain.
- **Consensus method:** comparative equivalence principle (`gl.eq_principle.prompt_comparative`) with strict deterministic validation of every LLM output (closed verdict set, numeric ranges, length caps), so prompt injection in page content cannot widen the decision space. Appeals re-judge under a skeptical persona and only overturn deterministically at ≥75% confidence.
- **Deployed contracts (GenLayer Studionet):** PriceLedger `0x26aA8E0af993665e02A14408f75221e1951926C1`, MerchantBond `0xDa121e6fF503eC2F13101df37Cf05aD38E93544F` — explorer: https://explorer-studio.genlayer.com
- **Live app:** https://saleproof.vercel.app (React + genlayer-js; reads and writes; ships a dev wallet with faucet so a reviewer needs no setup)
- **Repository:** https://github.com/ldkfj/saleproof — 66+ incremental commits, 66 unit tests including adversarial LLM-output suites, full engineering journal in `docs/BUILD-LOG.md`.

## How to use it (reviewer walkthrough, ~5 minutes)

1. Open https://saleproof.vercel.app — the dashboard shows real on-chain products, sales, and claims.
2. Open **Claim #1**: a real completed case. The on-chain history shows £51.77; the merchant announced a "£65.00 reference, −20%" sale; a buyer challenged it; validators returned `INFLATED_REFERENCE` at 100% confidence — their written reasoning is displayed verbatim from the chain — and settlement paid the buyer 0.2 GEN from the bond and struck the merchant.
3. Click any product to see its accumulated price history chart (every point is an on-chain observation with its watcher address).
4. To act yourself: press **Connect** → **Dev wallet**, tap **Fund 1 GEN**, then trigger a snapshot on any product and watch the transaction go through validator consensus to `FINALIZED · SUCCESS` — the UI only updates when both hold.
5. Everything the UI shows can be re-derived from the chain: run `node frontend/scripts/verify-live.mjs`.

## Roadmap (not part of the current build)

Migration to Testnet Bradbury is in progress (the PriceLedger deploy transaction has already finalized there; the app is network-switchable via one env var). Planned next: indexed coverage accounting and watcher incentives.

Design spec: [[SPEC]] · Engineering journal: [[BUILD-LOG]]
