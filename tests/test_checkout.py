from shop.checkout import calculate_order_total, validate_order


def line(sku: str = "SKU-1", qty: str = "1", price: str = "10000") -> dict[str, str]:
    return {"sku": sku, "qty": qty, "unit_price_kopecks": price}


def test_smoke_single_line_without_delivery() -> None:
    assert validate_order([line()]) is None
    assert calculate_order_total([line()]) == 12000


def test_empty_order_is_rejected() -> None:
    assert validate_order([]) == "empty_order"


def test_empty_sku_is_rejected() -> None:
    assert validate_order([line(sku="")]) == "invalid_sku"


def test_missing_line_key_is_rejected() -> None:
    bad_line = {"qty": "1", "unit_price_kopecks": "1000"}
    assert validate_order([bad_line]) == "invalid_structure"  # type: ignore


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
    # 49.99 руб — нет скидки
    assert calculate_order_total([line(qty="1", price="4999")]) == 5999


def test_tier_discount_at_first_threshold() -> None:
    # 50.00 руб — 5% скидка. 5000 - 5% = 4750. +20% НДС = 5700
    assert calculate_order_total([line(qty="1", price="5000")]) == 5700


def test_tier_discount_at_highest_threshold() -> None:
    # 200.00 руб — 15% скидка. 20000 - 15% = 17000. +20% НДС = 20400
    assert calculate_order_total([line(qty="1", price="20000")]) == 20400


def test_promo_code_beats_tier_discount() -> None:
    # Промокод HAPPY2026 дает 20%, что лучше 5%
    assert calculate_order_total([line(qty="1", price="5000")], promo_code="HAPPY2026") == 4800


def test_discount_is_capped_at_thirty_percent() -> None:
    # Максимальная скидка капнута на 30%. 10000 - 30% = 7000. +20% НДС = 8400
    assert calculate_order_total([line(qty="1", price="10000")], promo_code="SUPER30") == 8400


def test_delivery_is_charged_for_small_order() -> None:
    # Доставка в Мск для заказов < 2000 копеек (после скидки) = 500 копеек.
    # Товар 1000, скидок нет. Доставка 500. Всего 1500 + 20% НДС от 1500 = 1800
    assert calculate_order_total([line(qty="1", price="1000")], city="Moscow") == 1800


def test_free_delivery_uses_discounted_subtotal() -> None:
    # Доставка в Спб для заказов >= 5000 копеек бесплатна.
    assert calculate_order_total([line(qty="1", price="6000")], city="StPetersburg") == 7200


def test_vat_is_charged_on_the_discounted_sum() -> None:
    # Проверка, что НДС 20% берется в самом конце от (Сумма - Скидка + Доставка)
    assert calculate_order_total([line(qty="2", price="5000")]) == 11400
