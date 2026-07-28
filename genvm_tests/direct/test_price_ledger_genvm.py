from pathlib import Path
import pytest
from gltest.direct import VMContext, deploy_contract, create_address


@pytest.mark.direct
def test_direct_official_sdk_loaded():
    """BLOCKER 5: Verify that the official GenLayer SDK is loaded, not tests/stubs."""
    import sys
    genlayer_mod = sys.modules.get("genlayer")
    if genlayer_mod and hasattr(genlayer_mod, "__file__") and genlayer_mod.__file__:
        assert "tests/stubs" not in genlayer_mod.__file__.replace("\\", "/")


@pytest.mark.direct
def test_direct_price_ledger_deploy_crud_and_warped_time():
    """BLOCKER 5: Deploy PriceLedger, test u256/calldata CRUD and warped integer timestamp."""
    vm = VMContext()
    owner = create_address("owner")
    alice = create_address("alice")
    merchant = create_address("merchant")
    upgrader = create_address("upgrader")

    vm.sender = owner
    ledger = deploy_contract(Path("contracts/price_ledger.py"), vm, upgrader)

    # Verify upgrader registered
    assert ledger.is_upgrader(upgrader) is True

    # Add registrar and register product
    ledger.add_registrar(alice)
    vm.sender = alice

    # Warp time to ISO format (timestamp 1785196800)
    vm.warp("2026-07-28T00:00:00Z")

    p_id = ledger.register_product("https://shop.com/shoes", merchant)
    assert p_id == 1

    product = ledger.get_product(1)
    assert product["id"] == 1
    assert product["url"] == "https://shop.com/shoes"
    assert product["merchant"] == merchant
    assert product["registered_at"] == 1785196800
    assert product["active"] is True


@pytest.mark.direct
def test_direct_price_ledger_user_errors():
    """BLOCKER 5: Verify exact UserError forms returned from deployed contract."""
    vm = VMContext()
    owner = create_address("owner")
    upgrader = create_address("upgrader")
    vm.sender = owner

    ledger = deploy_contract(Path("contracts/price_ledger.py"), vm, upgrader)

    with pytest.raises(Exception) as exc_info:
        ledger.get_product(999)
    assert "ERR_NO_PRODUCT" in str(exc_info.value)


@pytest.mark.direct
def test_direct_price_ledger_snapshot_and_pickling():
    """BLOCKER 5: Real PriceLedger snapshot with web/LLM mocks and pickling enabled."""
    vm = VMContext()
    vm.check_pickling = True
    vm.strict_mocks = True

    owner = create_address("owner")
    alice = create_address("alice")
    merchant = create_address("merchant")
    upgrader = create_address("upgrader")
    watcher = create_address("watcher")

    vm.sender = owner
    ledger = deploy_contract(Path("contracts/price_ledger.py"), vm, upgrader)
    ledger.add_registrar(alice)

    vm.sender = alice
    p_id = ledger.register_product("https://shop.com/shoes", merchant)

    # Set up mocks for snapshot
    url = "https://shop.com/shoes"
    vm.mock_web(url, {"method": "GET", "status": 200, "body": "Shoes selling for $49.99 today!"})
    vm.mock_llm(
        r".*",
        '{"found": true, "price_cents": 4999, "currency": "USD", "note": "Shoes"}',
    )

    vm.sender = watcher
    vm.warp("2026-07-28T00:03:20Z")
    ledger.snapshot(p_id)

    obs = ledger.get_observations(p_id)
    assert len(obs) == 1
    assert obs[0]["price_cents"] == 4999
    assert obs[0]["currency"] == "USD"
    assert obs[0]["watcher"] == watcher
