import sys

import pytest


LEDGER_PATH = "contracts/price_ledger.py"


@pytest.mark.direct
def test_direct_price_ledger_uses_official_sdk_and_warped_time(
    direct_vm,
    direct_deploy,
    direct_owner,
    direct_alice,
    direct_bob,
    direct_charlie,
):
    """Deploy through official fixtures and round-trip Address/u256 calldata."""
    direct_vm.warp("2026-07-28T00:00:00Z")
    direct_vm.sender = direct_owner
    ledger = direct_deploy(LEDGER_PATH, direct_charlie, 600, 1000)

    genlayer_mod = sys.modules["genlayer"]
    assert genlayer_mod.__file__ is not None
    assert "tests/stubs" not in genlayer_mod.__file__.replace("\\", "/")
    assert ledger.is_upgrader(direct_charlie) is True

    ledger.add_registrar(direct_alice)
    direct_vm.sender = direct_alice
    product_id = ledger.register_product(
        "https://shop.com/shoes", direct_bob
    )

    product = ledger.get_product(product_id)
    assert product["merchant"].as_bytes == direct_bob
    assert {k: v for k, v in product.items() if k != "merchant"} == {
        "id": 1,
        "url": "https://shop.com/shoes",
        "registered_at": 1785196800,
        "active": True,
    }


@pytest.mark.direct
def test_direct_price_ledger_user_error(
    direct_vm, direct_deploy, direct_owner, direct_charlie
):
    direct_vm.sender = direct_owner
    ledger = direct_deploy(LEDGER_PATH, direct_charlie)

    with direct_vm.expect_revert("ERR_NO_PRODUCT"):
        ledger.get_product(999)


@pytest.mark.direct
def test_direct_price_ledger_snapshot_pickling_and_cooldown(
    direct_vm,
    direct_deploy,
    direct_owner,
    direct_alice,
    direct_bob,
    direct_charlie,
):
    direct_vm.check_pickling = True
    direct_vm.strict_mocks = True
    direct_vm.warp("2026-07-28T00:00:00Z")
    direct_vm.sender = direct_owner
    ledger = direct_deploy(LEDGER_PATH, direct_charlie, 60, 1000)
    ledger.add_registrar(direct_alice)

    direct_vm.sender = direct_alice
    product_id = ledger.register_product(
        "https://shop.com/shoes", direct_bob
    )

    direct_vm.mock_web(
        "https://shop.com/shoes",
        {
            "method": "GET",
            "status": 200,
            "body": "Shoes selling for $49.99 today!",
        },
    )
    direct_vm.mock_llm(
        r"^You are a price extractor\.",
        '{"found": true, "price_cents": 4999, "currency": "USD", "note": "Shoes"}',
    )

    direct_vm.sender = direct_charlie
    direct_vm.warp("2026-07-28T00:01:00Z")
    ledger.snapshot(product_id)

    observations = ledger.get_observations(product_id)
    assert len(observations) == 1
    assert observations[0]["watcher"].as_bytes == direct_charlie
    assert {
        k: v for k, v in observations[0].items() if k != "watcher"
    } == {
        "price_cents": 4999,
        "currency": "USD",
        "observed_at": 1785196860,
        "ok": True,
        "note": "Shoes",
    }

    with direct_vm.expect_revert("ERR_COOLDOWN"):
        ledger.snapshot(product_id)


@pytest.mark.direct
def test_direct_root_code_vla_truncate_extend_compatibility(
    direct_vm, direct_deploy, direct_owner, direct_alice
):
    """Direct Mode checks the byte-VLA operation, not native Root authorization."""
    direct_vm.sender = direct_owner
    ledger = direct_deploy(LEDGER_PATH, direct_alice)

    direct_vm.sender = direct_alice
    ledger.upgrade(b"new_code_bytes")
