"""Coupon validation service — never trust discount amounts from the client."""
from datetime import datetime
from typing import Optional

from app.utils.json_store import coupons_store


class CouponError(Exception):
    pass


def get_coupon_by_code(code: str) -> Optional[dict]:
    return coupons_store.find_one(lambda c: c.get("code", "").lower() == code.lower())


def validate_coupon(code: str, subtotal: float, restaurant_id: Optional[str] = None) -> tuple[dict, float]:
    """Returns (coupon_record, discount_amount) or raises CouponError."""
    coupon = get_coupon_by_code(code)
    if not coupon:
        raise CouponError("Coupon code not found.")
    if not coupon.get("is_active", False):
        raise CouponError("This coupon is no longer active.")

    expiry = coupon.get("expiry_date")
    if expiry:
        try:
            if datetime.fromisoformat(expiry) < datetime.utcnow():
                raise CouponError("This coupon has expired.")
        except ValueError:
            pass

    if coupon.get("used_count", 0) >= coupon.get("usage_limit", 0):
        raise CouponError("This coupon has reached its usage limit.")

    if subtotal < coupon.get("minimum_order_value", 0):
        raise CouponError(
            f"Minimum order value of Rs. {coupon.get('minimum_order_value', 0):,.0f} required for this coupon."
        )

    if coupon.get("restaurant_id") and restaurant_id and coupon["restaurant_id"] != restaurant_id:
        raise CouponError("This coupon is not valid for this restaurant.")

    if coupon.get("discount_type") == "percentage":
        discount = subtotal * (coupon.get("discount_value", 0) / 100)
    else:
        discount = coupon.get("discount_value", 0)

    max_discount = coupon.get("maximum_discount")
    if max_discount is not None:
        discount = min(discount, max_discount)

    discount = min(discount, subtotal)
    return coupon, round(discount, 2)


def mark_coupon_used(code: str) -> None:
    coupon = get_coupon_by_code(code)
    if coupon:
        coupons_store.update(coupon["id"], {"used_count": coupon.get("used_count", 0) + 1})
