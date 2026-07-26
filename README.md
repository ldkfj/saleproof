# SaleProof

SaleProof is a discount-authenticity protocol on GenLayer: merchants stake a bond promising their sales are genuine; the chain itself accumulates price evidence over time by reading product pages, and when a buyer challenges a sale, validators read the live page, weigh it against the on-chain price history, and deliver a graduated AI verdict that pays out from the merchant's bond.

## Repository Structure

```
saleproof/
├── contracts/
│   └── price_ledger.py        # PriceLedger intelligent contract (deterministic core)
├── scripts/                   # Deploy scripts and helpers
├── tests/
│   ├── conftest.py            # Pytest configuration and stub injection
│   ├── stubs/
│   │   └── genlayer/          # GenLayer runtime stub for unit testing
│   └── test_price_ledger.py   # Unit tests for PriceLedger logic
├── docs/
│   └── SPEC.md                # Full technical specification
└── README.md
```

## Phase 1 Implementation

- **PriceLedger Contract**: Implemented deterministic storage schema, constructor, registrar management (`add_registrar`, `remove_registrar`), product registration with strict URL validation, deactivation, and view methods (`get_product`, `get_observations`, `get_recent_observations`, `get_product_count`, `is_registrar`).
- **GenLayer Stub**: Pure-Python runtime stub in `tests/stubs/genlayer/` for isolated unit testing.
- **Unit Suite**: Pure-Python unit test suite covering all deterministic logic and guard error messages.

## Running Tests

To run the unit tests with pytest:

```bash
python -m pytest -v
```

