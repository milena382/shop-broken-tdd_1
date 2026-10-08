VALID_PROMOS = {"HAPPY2026": 20, "SUPER30": 30}
VALID_CITIES = {"Moscow", "StPetersburg"}


def _validate_item_structure(item: dict[str, str]) -> bool:
    if not isinstance(item, dict):
        return False
    return "sku" in item and "qty" in item and "unit_price_kopecks" in item


def _validate_item_values(item: dict[str, str]) -> str | None:
    try:
        if int(item["qty"]) <= 0:
            return "invalid_quantity"
    except ValueError:
        return "invalid_quantity"
    try:
        if int(item["unit_price_kopecks"]) < 0:
            return "invalid_price"
    except ValueError:
        return "invalid_price"
    return None


def validate_order(items: list[dict[str, str]], promo_code: str | None = None, city: str | None = None) -> str | None:
    if not items:
        return "empty_order"
    skus = set()
    for item in items:
        if not _validate_item_structure(item):
            return "invalid_structure"
        sku = item["sku"]
        if not sku or sku in skus:
            return "invalid_sku" if not sku else "duplicate_sku"
        skus.add(sku)
        err = _validate_item_values(item)
        if err:
            return err
    if promo_code and promo_code not in VALID_PROMOS:
        return "invalid_promo"
    if city and city not in VALID_CITIES:
        return "invalid_city"
    return None


def _get_delivery_cost(city: str | None, subtotal: int) -> int:
    if city == "Moscow" and subtotal < 2000:
        return 500
    if city == "StPetersburg" and subtotal < 5000:
        return 300
    return 0


def calculate_order_total(
    items: list[dict[str, str]], promo_code: str | None = None, city: str | None = None
) -> int | None:
    if validate_order(items, promo_code, city) is not None:
        return None
    subtotal = sum(int(item["qty"]) * int(item["unit_price_kopecks"]) for item in items)
    tier_discount = 15 if subtotal >= 20000 else (5 if subtotal >= 5000 else 0)
    promo_discount = VALID_PROMOS.get(promo_code, 0) if promo_code else 0
    final_discount_pct = min(max(tier_discount, promo_discount), 30)
    discount_amount = (subtotal * final_discount_pct + 50) // 100
    discounted_subtotal = subtotal - discount_amount
    delivery_cost = _get_delivery_cost(city, discounted_subtotal)
    total_before_vat = discounted_subtotal + delivery_cost
    vat_amount = (total_before_vat * 20 + 50) // 100
    return total_before_vat + vat_amount
