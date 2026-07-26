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

## Running Tests

To run the unit tests with pytest:

```bash
python -m pytest -v
```
