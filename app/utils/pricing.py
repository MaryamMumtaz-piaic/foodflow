"""Server-side price and total recalculation.

Section 18: Never trust prices sent from the frontend — always recompute
subtotal, delivery fee, discount, tax, and final total on the backend from
authoritative menu-item data.
"""
from dataclasses import dataclass

TAX_RATE = 0.05  # 5% service/tax fee applied to subtotal


@dataclass
class PriceBreakdown:
    subtotal: float
    delivery_fee: float
    discount: float
    tax: float
    final_total: float


def compute_item_total(unit_price: float, quantity: int, add_on_prices: list[float]) -> float:
    add_on_total = sum(add_on_prices)
    return round((unit_price + add_on_total) * quantity, 2)


def compute_breakdown(
    subtotal: float,
    delivery_fee: float,
    discount: float = 0.0,
    tax_rate: float = TAX_RATE,
) -> PriceBreakdown:
    subtotal = round(subtotal, 2)
    discount = round(min(discount, subtotal), 2)
    taxable = max(subtotal - discount, 0)
    tax = round(taxable * tax_rate, 2)
    final_total = round(subtotal - discount + tax + delivery_fee, 2)
    return PriceBreakdown(
        subtotal=subtotal,
        delivery_fee=round(delivery_fee, 2),
        discount=discount,
        tax=tax,
        final_total=final_total,
    )


def format_pkr(amount: float) -> str:
    return f"Rs. {amount:,.0f}"
