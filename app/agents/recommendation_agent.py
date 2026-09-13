"""Food Recommendation Agent (Section 10.2).

Ranks available menu items against extracted preferences. Always filters
out unavailable items and constrains recommendations to real mock data
(hallucination prevention).
"""
from app.schemas.ai import PreferenceCriteria, RecommendationResponse, RecommendedItem
from app.utils.json_store import menu_items_store, restaurants_store


def _score_item(item: dict, restaurant: dict, criteria: PreferenceCriteria) -> float:
    score = restaurant.get("rating", 3.0) * 2 + item.get("rating", 3.0)

    price = item.get("promotional_price") or item["price"]
    if criteria.budget:
        if price <= criteria.budget:
            score += 3
        else:
            score -= 5

    if criteria.dietary_preference:
        labels = [str(l) for l in item.get("dietary_labels", [])]
        if criteria.dietary_preference in labels:
            score += 4

    if criteria.spice_preference:
        if item.get("spice_level") == criteria.spice_preference:
            score += 2

    if criteria.cuisine:
        cuisines = [c.lower() for c in restaurant.get("cuisine_types", [])]
        if criteria.cuisine.lower() in cuisines:
            score += 3

    if criteria.max_delivery_minutes:
        if restaurant.get("estimated_delivery_time_minutes", 999) <= criteria.max_delivery_minutes:
            score += 2
        else:
            score -= 3

    if criteria.keywords:
        text = f"{item.get('name', '')} {item.get('description', '')}".lower()
        if any(k in text for k in criteria.keywords):
            score += 1

    return score


def _reason_for(item: dict, restaurant: dict, criteria: PreferenceCriteria) -> str:
    bits = []
    if restaurant.get("rating", 0) >= 4.3:
        bits.append(f"highly rated restaurant ({restaurant['rating']}/5)")
    price = item.get("promotional_price") or item["price"]
    if criteria.budget and price <= criteria.budget:
        bits.append(f"fits your Rs. {criteria.budget:,.0f} budget")
    if criteria.dietary_preference and criteria.dietary_preference in [str(l) for l in item.get("dietary_labels", [])]:
        bits.append(f"matches your {criteria.dietary_preference} preference")
    if criteria.max_delivery_minutes and restaurant.get("estimated_delivery_time_minutes", 999) <= criteria.max_delivery_minutes:
        bits.append(f"delivers within {restaurant['estimated_delivery_time_minutes']} minutes")
    if not bits:
        bits.append("popular choice based on rating and availability")
    return "; ".join(bits).capitalize()


def recommend(criteria: PreferenceCriteria, restaurant_id: str | None = None, limit: int = 6) -> RecommendationResponse:
    items = menu_items_store.find_many(lambda m: m.get("is_available", True))
    if restaurant_id:
        items = [i for i in items if i["restaurant_id"] == restaurant_id]

    restaurants_by_id = {r["id"]: r for r in restaurants_store.list_all()}

    scored = []
    for item in items:
        restaurant = restaurants_by_id.get(item["restaurant_id"])
        if not restaurant or restaurant.get("approval_status") != "approved":
            continue
        score = _score_item(item, restaurant, criteria)
        scored.append((score, item, restaurant))

    scored.sort(key=lambda t: t[0], reverse=True)
    top = scored[:limit]

    recommendations = [
        RecommendedItem(
            menu_item_id=item["id"],
            name=item["name"],
            restaurant_id=restaurant["id"],
            restaurant_name=restaurant["name"],
            price=item.get("promotional_price") or item["price"],
            rating=item.get("rating", restaurant.get("rating", 0)),
            reason=_reason_for(item, restaurant, criteria),
        )
        for _, item, restaurant in top
    ]

    return RecommendationResponse(criteria=criteria, recommendations=recommendations, source=criteria.source)
