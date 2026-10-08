from shop.checkout import calculate_order_total, validate_order


def line(sku: str = "SKU-1", qty: str = "1", price: str = "10000") -> dict[str, str]:
    return {"sku": sku, "qty": qty, "unit_price_kopecks": price}


def test_smoke_single_line_without_delivery() -> None:
    assert validate_order([line()]) is None
    assert calculate_order_total([line()]) == 11400


def test_empty_order_is_rejected() -> None:
    assert validate_order([]) == "empty_order"


def test_empty_sku_is_rejected() -> None:
    assert validate_order([line(sku="")]) == "invalid_sku"


def test_missing_line_key_is_rejected() -> None:
    bad_line = {"qty": "1", "unit_price_kopecks": "1000"}
    assert validate_order([bad_line]) == "invalid_structure"


def test_non_numeric_quantity_is_rejected() -> None:
    assert validate_order([line(qty="abc")]) == "invalid_quantity"


def test_zero_quantity_is_rejected() -> None:
    assert validate_order([line(qty="0")]) == "invalid_quantity"
    assert validate_order([line(qty="-5")]) == "invalid_quantity"


def test_non_numeric_price_is_rejected() -> None:
    assert validate_order([line(price="10.5")]) == "invalid_price"


def test_negative_price_is_rejected() -> None:
    assert validate_order([line(price="-100")]) == "invalid_price"


def test_duplicate_sku_is_rejected() -> None:
    assert validate_order([line("SKU-1"), line("SKU-1")]) == "duplicate_sku"


def test_unknown_promo_code_is_rejected() -> None:
    assert validate_order([line()], promo_code="INVALID") == "invalid_promo"


def test_unsupported_city_is_rejected() -> None:
    assert validate_order([line()], city="London") == "invalid_city"


def test_valid_order_passes_validation() -> None:
    assert validate_order([line()], promo_code="HAPPY2026", city="Moscow") is None


def test_no_discount_below_first_tier() -> None:
    assert calculate_order_total([line(qty="1", price="4999")]) == 5999


def test_tier_discount_at_first_threshold() -> None:
    assert calculate_order_total([line(qty="1", price="5000")]) == 5700


def test_tier_discount_at_highest_threshold() -> None:
    assert calculate_order_total([line(qty="1", price="20000")]) == 20400


def test_promo_code_beats_tier_discount() -> None:
    assert calculate_order_total([line(qty="1", price="5000")], promo_code="HAPPY2026") == 4800


def test_discount_is_capped_at_thirty_percent() -> None:
    assert calculate_order_total([line(qty="1", price="10000")], promo_code="SUPER30") == 8400


def test_delivery_is_charged_for_small_order() -> None:
    assert calculate_order_total([line(qty="1", price="1000")], city="Moscow") == 1800


def test_free_delivery_uses_discounted_subtotal() -> None:
    assert calculate_order_total([line(qty="1", price="6000")], city="StPetersburg") == 6840


def test_vat_is_charged_on_the_discounted_sum() -> None:
    assert calculate_order_total([line(qty="2", price="5000")]) == 11400


def test_expensive_vip_order_is_rejected() -> None:
    """Заказы, где стоимость одного товара составляет 1 000 001 копейку или больше, отклоняются."""
    # Товар стоимостью ровно 10 000 рублей (1 000 000 копеек) — проходит
    assert validate_order([line(price="1000000")]) is None

    # Товар стоимостью 1 000 001 копейка — должен отклониться с ошибкой
    assert validate_order([line(price="1000001")]) == "vip_order_not_supported"
