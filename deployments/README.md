# SaleProof Deployment Records & Status

## Deployment Status (Round A Reviewer Correction)

- **Active Network Deployment**: NONE performed in Round A.
- **Superseded Deployments**: The following prior Studionet contract deployments are recorded as **SUPERSEDED** by Round A contract changes:
  - `PriceLedger`: `0x26aA8E0af993665e02A14408f75221e1951926C1` (Superseded)
  - `MerchantBond`: `0xDa121e6fF503eC2F13101df37Cf05aD38E93544F` (Superseded)

---

## Future Deployment Procedure (When User-Authorized)

When user authorization for network deployment is granted:

1. Validate source using `genvm-lint check` and `python scripts/schema_probe.py --rpc <RPC_URL>`.
2. Deploy `PriceLedger` passing valid `upgrader_address`.
3. Deploy `MerchantBond` passing `upgrader_address` and `PriceLedger` contract address.
4. Authorize `MerchantBond` address as a registrar on `PriceLedger` via `PriceLedger.add_registrar(merchant_bond_address)`.
5. Update `deployments/README.md` with new live contract addresses and transaction hashes.
