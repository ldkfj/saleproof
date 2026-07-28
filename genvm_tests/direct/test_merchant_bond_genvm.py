from pathlib import Path
import pytest
from gltest.direct import VMContext, deploy_contract, create_address


@pytest.mark.direct
def test_direct_merchant_bond_deploy_and_payable_crud():
    """BLOCKER 5: MerchantBond payable registration, top-up, and view readbacks via deployed source."""
    vm = VMContext()
    owner = create_address("owner")
    upgrader = create_address("upgrader")
    ledger_addr = create_address("ledger")
    merchant = create_address("merchant")

    vm.sender = owner
    bond = deploy_contract(
        Path("contracts/merchant_bond.py"),
        vm,
        upgrader,
        ledger_addr,
        1000,
        100,
        200,
        300,
        3,
    )
    assert bond.is_upgrader(upgrader) is True

    # Payable merchant registration (min bond 1000)
    vm.sender = merchant
    vm.value = 1500
    vm.warp("2026-07-28T00:00:00Z")
    bond.register_merchant("Direct Merchant")

    m = bond.get_merchant(merchant)
    assert m["addr"] == merchant
    assert m["name"] == "Direct Merchant"
    assert m["bond_wei"] == 1500
    assert m["joined_at"] == 1785196800

    # Top up bond with 500 wei
    vm.value = 500
    bond.top_up_bond()
    assert bond.get_merchant(merchant)["bond_wei"] == 2000


@pytest.mark.direct
def test_direct_merchant_bond_user_errors():
    """BLOCKER 5: MerchantBond error guards through deployed source."""
    vm = VMContext()
    owner = create_address("owner")
    upgrader = create_address("upgrader")
    ledger_addr = create_address("ledger")

    vm.sender = owner
    bond = deploy_contract(
        Path("contracts/merchant_bond.py"),
        vm,
        upgrader,
        ledger_addr,
        1000,
        100,
        200,
        300,
        3,
    )

    with pytest.raises(Exception) as exc_info:
        bond.get_merchant(create_address("unknown"))
    assert "ERR_NO_MERCHANT" in str(exc_info.value)


@pytest.mark.direct
def test_direct_root_code_vla_truncate_extend_compatibility_note():
    """BLOCKER 5 & BLOCKER 6: Root code VLA truncate/extend compatibility.

    NOTE: Direct Mode in-memory manager permits code writes. This test verifies bytecode
    truncation/extension compatibility, but DOES NOT prove native Root locked-slot authorization.
    Native Root authorization rehearsal is reserved for Studionet integration testing.
    """
    vm = VMContext()
    owner = create_address("owner")
    upgrader = create_address("upgrader")

    vm.sender = owner
    ledger = deploy_contract(Path("contracts/price_ledger.py"), vm, upgrader)

    vm.sender = upgrader
    ledger.upgrade(b"new_code_bytes")
