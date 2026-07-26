import pytest
from genlayer import gl
from contracts.price_ledger import PriceLedger, Observation

OWNER = "0x1111111111111111111111111111111111111111"
ALICE = "0x2222222222222222222222222222222222222222"
BOB = "0x3333333333333333333333333333333333333333"
MERCHANT = "0x4444444444444444444444444444444444444444"


@pytest.fixture(autouse=True)
def reset_gl():
    gl.message.sender_address = OWNER
    gl.message.timestamp = 1700000000


def test_1_constructor_sets_owner_and_params():
    gl.message.sender_address = OWNER
    ledger = PriceLedger(snapshot_cooldown_s=600, max_observations=1000)
    assert ledger.owner == OWNER
    assert ledger.snapshot_cooldown_s == 600
    assert ledger.max_observations == 1000
    assert ledger.get_product_count() == 0


def test_2_add_registrar_by_owner_and_non_owner():
    gl.message.sender_address = OWNER
    ledger = PriceLedger()

    # Owner can add registrar
    ledger.add_registrar(ALICE)
    assert ledger.is_registrar(ALICE) is True

    # Non-owner fails with ERR_NOT_OWNER
    gl.message.sender_address = BOB
    with pytest.raises(Exception) as exc_info:
        ledger.add_registrar(BOB)
    assert str(exc_info.value).startswith("ERR_NOT_OWNER")


def test_3_registrar_management_edge_cases():
    gl.message.sender_address = OWNER
    ledger = PriceLedger()
    ledger.add_registrar(ALICE)

    # Adding again raises ERR_ALREADY_REGISTRAR
    with pytest.raises(Exception) as exc_info:
        ledger.add_registrar(ALICE)
    assert str(exc_info.value).startswith("ERR_ALREADY_REGISTRAR")

    # Remove works
    ledger.remove_registrar(ALICE)
    assert ledger.is_registrar(ALICE) is False

    # Removing absent/false registrar raises ERR_NOT_REGISTRAR
    with pytest.raises(Exception) as exc_info:
        ledger.remove_registrar(ALICE)
    assert str(exc_info.value).startswith("ERR_NOT_REGISTRAR")


def test_4_register_product_by_non_registrar():
    gl.message.sender_address = OWNER
    ledger = PriceLedger()

    # Non-registrar attempts to register product
    gl.message.sender_address = BOB
    with pytest.raises(Exception) as exc_info:
        ledger.register_product("https://example.com/product", MERCHANT)
    assert str(exc_info.value).startswith("ERR_NOT_REGISTRAR")


def test_5_happy_path_register():
    gl.message.sender_address = OWNER
    ledger = PriceLedger()
    ledger.add_registrar(ALICE)

    gl.message.sender_address = ALICE
    gl.message.timestamp = 1710000000
    p_id = ledger.register_product("https://shop.com/item1", MERCHANT)
    assert p_id == 1

    prod = ledger.get_product(1)
    assert prod["id"] == 1
    assert prod["url"] == "https://shop.com/item1"
    assert prod["merchant"] == MERCHANT
    assert prod["registered_at"] == 1710000000
    assert prod["active"] is True

    obs = ledger.get_observations(1)
    assert obs == []


def test_6_url_guards():
    gl.message.sender_address = OWNER
    ledger = PriceLedger()
    ledger.add_registrar(ALICE)
    gl.message.sender_address = ALICE

    # Empty URL
    with pytest.raises(Exception) as exc1:
        ledger.register_product("", MERCHANT)
    assert str(exc1.value).startswith("ERR_URL_EMPTY")

    # Whitespace URL
    with pytest.raises(Exception) as exc1_ws:
        ledger.register_product("   ", MERCHANT)
    assert str(exc1_ws.value).startswith("ERR_URL_EMPTY")

    # Invalid scheme (ftp)
    with pytest.raises(Exception) as exc2:
        ledger.register_product("ftp://shop.com/item", MERCHANT)
    assert str(exc2.value).startswith("ERR_URL_SCHEME")

    # Too long (> 500 chars)
    long_url = "https://shop.com/" + ("x" * 490)
    assert len(long_url) == 507
    with pytest.raises(Exception) as exc3:
        ledger.register_product(long_url, MERCHANT)
    assert str(exc3.value).startswith("ERR_URL_TOO_LONG")


def test_7_duplicate_and_deactivate_product():
    gl.message.sender_address = OWNER
    ledger = PriceLedger()
    ledger.add_registrar(ALICE)
    gl.message.sender_address = ALICE

    url = "https://shop.com/deal"
    p_id1 = ledger.register_product(url, MERCHANT)
    assert p_id1 == 1

    # Duplicate active URL raises ERR_URL_DUPLICATE
    with pytest.raises(Exception) as exc_info:
        ledger.register_product(url, MERCHANT)
    assert str(exc_info.value).startswith("ERR_URL_DUPLICATE")

    # Deactivate product 1
    ledger.deactivate_product(1)
    prod = ledger.get_product(1)
    assert prod["active"] is False

    # Now same URL can be registered again (gets new ID)
    p_id2 = ledger.register_product(url, MERCHANT)
    assert p_id2 == 2
    prod2 = ledger.get_product(2)
    assert prod2["active"] is True


def test_8_get_recent_observations():
    gl.message.sender_address = OWNER
    ledger = PriceLedger()
    ledger.add_registrar(ALICE)
    gl.message.sender_address = ALICE

    p_id = ledger.register_product("https://shop.com/shoes", MERCHANT)

    # Seed observations directly via stub storage
    for i in range(1, 6):
        obs = Observation(
            price_cents=1000 * i,
            currency="USD",
            observed_at=1700000000 + i * 100,
            watcher=BOB,
            ok=True,
            note=f"obs {i}",
        )
        ledger.observations[p_id].append(obs)

    # get_recent_observations returns last k in order
    recent3 = ledger.get_recent_observations(p_id, 3)
    assert len(recent3) == 3
    assert recent3[0]["price_cents"] == 3000
    assert recent3[1]["price_cents"] == 4000
    assert recent3[2]["price_cents"] == 5000

    # k > len returns full log
    recent10 = ledger.get_recent_observations(p_id, 10)
    assert len(recent10) == 5


def test_9_get_product_unknown_id():
    gl.message.sender_address = OWNER
    ledger = PriceLedger()

    with pytest.raises(Exception) as exc_info:
        ledger.get_product(999)
    assert str(exc_info.value).startswith("ERR_NO_PRODUCT")

    with pytest.raises(Exception) as exc_info0:
        ledger.get_product(0)
    assert str(exc_info0.value).startswith("ERR_NO_PRODUCT")


def test_10_product_count_and_sequential_ids():
    gl.message.sender_address = OWNER
    ledger = PriceLedger()
    ledger.add_registrar(ALICE)
    gl.message.sender_address = ALICE

    id1 = ledger.register_product("https://shop.com/item1", MERCHANT)
    id2 = ledger.register_product("https://shop.com/item2", MERCHANT)
    id3 = ledger.register_product("https://shop.com/item3", MERCHANT)

    assert id1 == 1
    assert id2 == 2
    assert id3 == 3
    assert ledger.get_product_count() == 3


def test_11_get_recent_observations_k_zero():
    gl.message.sender_address = OWNER
    ledger = PriceLedger()
    ledger.add_registrar(ALICE)
    gl.message.sender_address = ALICE

    p_id = ledger.register_product("https://shop.com/hat", MERCHANT)
    obs = Observation(
        price_cents=1500,
        currency="USD",
        observed_at=1700000000,
        watcher=BOB,
        ok=True,
        note="Hat",
    )
    ledger.observations[p_id].append(obs)

    recent0 = ledger.get_recent_observations(p_id, 0)
    assert recent0 == []

