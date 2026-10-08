from datetime import UTC, datetime

from shop.inventory import low_stock_items
from shop.money import format_kopecks

REPORT_HEADER = "Stock report"
DEFAULT_LOW_STOCK_THRESHOLD = 10


def build_stock_report(
    stock: dict[str, int],
    prices: dict[str, int],
    threshold: int = DEFAULT_LOW_STOCK_THRESHOLD,
) -> str:
    generated_at = datetime.now(UTC).isoformat()
    lines = [REPORT_HEADER, f"generated_at={generated_at}"]

    total_value: int = 0
    for sku, count in sorted(stock.items()):
        price = prices.get(sku, 0)
        item_cost = count * price
        total_value += item_cost

        formatted_price = format_kopecks(price)
        formatted_cost = format_kopecks(item_cost)
        lines.append(f"{sku}: {count} x {formatted_price} = {formatted_cost}")

    low_items = low_stock_items(stock, threshold)
    low_text = ", ".join(low_items) if low_items else "none"

    lines.append(f"low stock: {low_text}")
    lines.append(f"total value: {format_kopecks(total_value)}")
    return "\n".join(lines)


def stock_health(
    count: int,
    incoming: int,
    sold_last_week: int,
    threshold: int = DEFAULT_LOW_STOCK_THRESHOLD,
) -> str:
    daily = sold_last_week // 7 if sold_last_week else 0
    if count <= 0:
        return "out_of_stock"
    if count < threshold:
        if incoming > 0:
            return "incoming_low"
        return "low"
    if count < threshold * 3:
        if daily == 0:
            return "unknown_demand"
        if count < daily * 3:
            return "reorder_soon"
        return "ok"
    return "ok"
