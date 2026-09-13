"""Delivery Prediction Agent (Section 10.4).

Estimates preparation + delivery time windows from restaurant workload
and static heuristics. Always clearly labeled as an estimate.
"""
from app.schemas.ai import DeliveryEstimateResponse
from app.utils.json_store import orders_store, restaurants_store, users_store


def estimate_delivery(restaurant_id: str, delivery_area: str | None = None) -> DeliveryEstimateResponse:
    restaurant = restaurants_store.get(restaurant_id)
    base_prep = 20
    base_delivery_span = restaurant.get("estimated_delivery_time_minutes", 35) if restaurant else 35

    active_orders = orders_store.find_many(
        lambda o: o.get("restaurant_id") == restaurant_id
        and o.get("status") in ("pending", "accepted", "preparing")
    )
    workload_factor = min(len(active_orders) * 2, 20)

    online_riders = users_store.find_many(lambda u: u.get("role") == "rider" and u.get("rider_online"))
    rider_factor = 0 if len(online_riders) >= 3 else 5

    prep_minutes = base_prep + workload_factor
    delivery_min = base_delivery_span + rider_factor
    delivery_max = delivery_min + 15 + (5 if delivery_area else 0)

    factors = [
        f"Restaurant currently has {len(active_orders)} active order(s) in the kitchen.",
        f"{len(online_riders)} rider(s) online in the area.",
        "Estimate includes preparation time and typical travel time for this zone.",
    ]

    return DeliveryEstimateResponse(
        restaurant_id=restaurant_id,
        estimated_preparation_minutes=prep_minutes,
        estimated_delivery_minutes_min=delivery_min,
        estimated_delivery_minutes_max=delivery_max,
        factors=factors,
        source="fallback",
    )
