"""Restaurant + menu business logic."""
from typing import Optional

from app.utils.json_store import (
    categories_store,
    menu_items_store,
    restaurants_store,
    reviews_store,
)


def list_restaurants(
    cuisine: Optional[str] = None,
    min_rating: Optional[float] = None,
    open_now: Optional[bool] = None,
    max_delivery_fee: Optional[float] = None,
    search: Optional[str] = None,
) -> list[dict]:
    rows = restaurants_store.list_all()
    rows = [r for r in rows if r.get("approval_status") == "approved"]

    if cuisine:
        rows = [r for r in rows if cuisine.lower() in [c.lower() for c in r.get("cuisine_types", [])]]
    if min_rating is not None:
        rows = [r for r in rows if r.get("rating", 0) >= min_rating]
    if open_now:
        rows = [r for r in rows if r.get("is_open")]
    if max_delivery_fee is not None:
        rows = [r for r in rows if r.get("delivery_fee", 0) <= max_delivery_fee]
    if search:
        s = search.lower()
        rows = [
            r
            for r in rows
            if s in r.get("name", "").lower()
            or any(s in c.lower() for c in r.get("cuisine_types", []))
        ]
    return rows


def get_restaurant(restaurant_id: str) -> Optional[dict]:
    return restaurants_store.get(restaurant_id)


def get_menu(restaurant_id: str, available_only: bool = False, search: Optional[str] = None) -> list[dict]:
    items = menu_items_store.find_many(lambda m: m.get("restaurant_id") == restaurant_id)
    if available_only:
        items = [i for i in items if i.get("is_available")]
    if search:
        s = search.lower()
        items = [i for i in items if s in i.get("name", "").lower() or s in i.get("description", "").lower()]
    return items


def get_categories(restaurant_id: str) -> list[dict]:
    return sorted(
        categories_store.find_many(lambda c: c.get("restaurant_id") == restaurant_id),
        key=lambda c: c.get("display_order", 0),
    )


def get_menu_item(item_id: str) -> Optional[dict]:
    return menu_items_store.get(item_id)


def recalc_restaurant_rating(restaurant_id: str) -> None:
    reviews = reviews_store.find_many(
        lambda r: r.get("restaurant_id") == restaurant_id and r.get("moderation_status") == "visible"
    )
    if not reviews:
        return
    avg = sum(r["rating"] for r in reviews) / len(reviews)
    restaurants_store.update(restaurant_id, {"rating": round(avg, 1), "review_count": len(reviews)})
