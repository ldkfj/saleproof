import pytest


BOND_PATH = "contracts/merchant_bond.py"


@pytest.mark.direct
def test_direct_merchant_bond_payable_crud_and_warped_time(
    direct_vm,
    direct_deploy,
    direct_owner,
    direct_alice,
    direct_bob,
    direct_charlie,
):
    direct_vm.warp("2026-07-28T00:00:00Z")
    direct_vm.sender = direct_owner
    bond = direct_deploy(
        BOND_PATH,
        direct_charlie,
        direct_bob,
        1000,
        100,
        200,
        300,
        3,
    )
    assert bond.is_upgrader(direct_charlie) is True

    direct_vm.sender = direct_alice
    direct_vm.value = 1500
    bond.deposit()
    direct_vm.value = 0
    bond.register_merchant("Direct Merchant", 1500)
    merchant = bond.get_merchant(direct_alice)
    assert merchant["addr"].as_bytes == direct_alice
    assert {k: v for k, v in merchant.items() if k != "addr"} == {
        "name": "Direct Merchant",
        "bond_wei": 1500,
        "strikes": 0,
        "active": True,
        "joined_at": 1785196800,
    }

    direct_vm.value = 500
    bond.deposit()
    direct_vm.value = 0
    bond.top_up_bond(500)
    assert bond.get_merchant(direct_alice)["bond_wei"] == 2000


@pytest.mark.direct
def test_direct_prefunded_credit_survives_failing_nonpayable_guard(
    direct_vm,
    direct_deploy,
    direct_owner,
    direct_alice,
    direct_bob,
):
    direct_vm.sender = direct_owner
    bond = direct_deploy(
        BOND_PATH,
        direct_alice,
        direct_bob,
        1000,
        100,
        200,
        300,
        3,
    )

    direct_vm.sender = direct_alice
    direct_vm.value = 1500
    bond.deposit()
    direct_vm.value = 0
    bond.register_merchant("Direct Merchant", 1000)
    assert bond.get_withdrawable(direct_alice)["amount_wei"] == 500

    with direct_vm.expect_revert("ERR_ALREADY_MERCHANT"):
        bond.register_merchant("Duplicate Merchant", 500)
    assert bond.get_withdrawable(direct_alice)["amount_wei"] == 500


@pytest.mark.direct
def test_direct_merchant_bond_user_error(
    direct_vm, direct_deploy, direct_owner, direct_alice, direct_bob
):
    direct_vm.sender = direct_owner
    bond = direct_deploy(
        BOND_PATH,
        direct_alice,
        direct_bob,
        1000,
        100,
        200,
        300,
        3,
    )

    with direct_vm.expect_revert("ERR_NO_MERCHANT"):
        bond.get_merchant(direct_owner)
