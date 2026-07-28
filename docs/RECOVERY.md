# SaleProof Contract Recovery & Upgrade Procedures

## Overview

Both `PriceLedger` and `MerchantBond` implement GenVM **Root Slot Upgradability** under the standard `Contract Recoverability and Upgradability Gate`.

- **Upgrader Authorization**: Authorized upgrader addresses are registered in the contract's Root storage slot (`gl.storage.Root.get().upgraders`) during `__init__`.
- **Method Signature**: Upgrades are executed via `@gl.public.write def upgrade(self, new_code: bytes) -> None`.
- **Root Security Model**: Upgrades can only be submitted by an address registered in `gl.storage.Root.get().upgraders`. Normal contract owner or admin keys cannot bypass or overwrite Root authorization.

---

## Constructor Requirements

When deploying either contract, the constructor's **first parameter** must be `upgrader_address: Address`:

1. **PriceLedger**:
   ```python
   def __init__(self, upgrader_address: Address, snapshot_cooldown_s: u64 = 300, max_observations: u64 = 500)
   ```
2. **MerchantBond**:
   ```python
   def __init__(self, upgrader_address: Address, ledger: Address, min_bond_wei: u256, claim_deposit_wei: u256, appeal_bond_wei: u256, appeal_window_s: u64, strike_limit: u64)
   ```

Passing the zero address (`0x0000000000000000000000000000000000000000`) is rejected with `ERR_BAD_UPGRADER`.

---

## Step-by-Step Contract Upgrade Procedure

In the event of a bug fix, schema migration, or contract logic update:

1. **Prepare New Bytecode**: Compile or prepare the updated `.py` source file. Ensure exact storage layout preservation for pre-existing storage slots.
2. **Authenticate as Upgrader**: Connect using the private key / wallet matching the registered `upgrader_address`.
3. **Invoke Upgrade Method**: Send a write transaction calling `upgrade(new_code)` on the contract address.
4. **Verification**: Confirm transaction success and verify the upgraded schema using `scripts/schema_probe.py`.
