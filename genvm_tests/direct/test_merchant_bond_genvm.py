import pytest
from genlayer import gl, Address
import contracts.merchant_bond as bond_mod
from contracts.merchant_bond import MerchantBond

UPGRADER = "0x9999999999999999999999999999999999999999"
OWNER = "0x1111111111111111111111111111111111111111"
MERCHANT = "0x2222222222222222222222222222222222222222"
LEDGER = "0x5555555555555555555555555555555555555555"


@pytest.mark.direct
def test_direct_merchant_bond_deploy_and_merchant_crud(direct_vm, monkeypatch):
    monkeypatch.setattr(bond_mod, "_now", lambda: direct_vm.timestamp)
    gl.message.sender_address = OWNER
    gl.storage.Root.reset()

    bond = MerchantBond(
        upgrader_address=UPGRADER,
        ledger=LEDGER,
        min_bond_wei=1000,
        claim_deposit_wei=100,
        appeal_bond_wei=200,
        appeal_window_s=300,
        strike_limit=3,
    )
    assert bond.is_upgrader(UPGRADER) is True

    gl.message.sender_address = MERCHANT
    gl.message.value = 1500
    bond.register_merchant("Direct Merchant")

    m = bond.get_merchant(MERCHANT)
    assert m["addr"] == Address(MERCHANT)
    assert m["name"] == "Direct Merchant"
    assert m["bond_wei"] == 1500
    assert m["joined_at"] == 1785196800

    gl.message.value = 500
    bond.top_up_bond()
    assert bond.get_merchant(MERCHANT)["bond_wei"] == 2000


@pytest.mark.direct
def test_direct_merchant_bond_user_errors(direct_vm):
    gl.message.sender_address = OWNER
    gl.storage.Root.reset()
    bond = MerchantBond(
        upgrader_address=UPGRADER,
        ledger=LEDGER,
        min_bond_wei=1000,
        claim_deposit_wei=100,
        appeal_bond_wei=200,
        appeal_window_s=300,
        strike_limit=3,
    )

    with pytest.raises(gl.vm.UserError) as exc_info:
        bond.get_merchant("0x8888888888888888888888888888888888888888")
    assert str(exc_info.value) == "ERR_NO_MERCHANT"
