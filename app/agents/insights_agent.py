"""Restaurant Insights Agent (Section 10.6).

Computes real aggregates from orders.json — never fabricates numbers.
An optional AI pass can phrase the insights, but the underlying figures
always come from actual backend data.
"""
from collections import Counter
from datetime import datetime

from app.agents.base import call_json_agent
from app.schemas.ai import InsightItem, RestaurantInsightsResponse
from app.utils.json_store import orders_store


def _compute_aggregates(restaurant_id: str) -> dict:
    orders = orders_store.find_many(lambda o: o.get("restaurant_id") == restaurant_id)
    completed = [o for o in orders if o["status"] == "delivered"]
    cancelled = [o for o in orders if o["status"] in ("cancelled", "failed", "rejected")]

    total_orders = len(orders)
    total_revenue = round(sum(o["final_total"] for o in completed), 2)
    average_order_value = round(total_revenue / len(completed), 2) if completed else 0.0
    cancellation_rate = round((len(cancelled) / total_orders) * 100, 1) if total_orders else 0.0

    item_counter = Counter()
    for o in orders:
        for item in o.get("items", []):
            item_counter[item["name"]] += item["quantity"]

    popular = [name for name, _ in item_counter.most_common(5)]
    low_performing = [name for name, _ in item_counter.most_common()[-5:]] if len(item_counter) > 5 else []

    hour_counter = Counter()
    for o in orders:
        try:
            hour = datetime.fromisoformat(o["created_at"]).hour
            hour_counter[hour] += 1
        except Exception:
            continue
    peak_hours = [f"{h:02d}:00-{h+1:02d}:00" for h, _ in hour_counter.most_common(3)]

    return {
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "average_order_value": average_order_value,
        "cancellation_rate": cancellation_rate,
        "popular_items": popular,
        "low_performing_items": low_performing,
        "peak_hours": peak_hours,
    }


def generate_insights(restaurant_id: str) -> RestaurantInsightsResponse:
    agg = _compute_aggregates(restaurant_id)

    fallback_insights = []
    if agg["popular_items"]:
        fallback_insights.append(InsightItem(
            title="Top performing dishes",
            detail=f"Your best sellers are: {', '.join(agg['popular_items'])}. Consider promoting these further.",
        ))
    if agg["low_performing_items"]:
        fallback_insights.append(InsightItem(
            title="Low-performing dishes",
            detail=f"These items order less frequently: {', '.join(agg['low_performing_items'])}. Consider a promotion or menu redesign.",
        ))
    if agg["cancellation_rate"] > 15:
        fallback_insights.append(InsightItem(
            title="High cancellation rate",
            detail=f"Cancellation rate is {agg['cancellation_rate']}%. Review preparation times and order acceptance speed.",
        ))
    if agg["peak_hours"]:
        fallback_insights.append(InsightItem(
            title="Peak ordering times",
            detail=f"Most orders arrive during: {', '.join(agg['peak_hours'])}. Ensure adequate staffing during these windows.",
        ))
    if not fallback_insights:
        fallback_insights.append(InsightItem(
            title="Not enough data yet",
            detail="Once more orders come in, FoodFlow will generate tailored business insights here.",
        ))

    ai_result = call_json_agent(
        "You are a restaurant business analyst for FoodFlow. Given real aggregate order "
        "statistics (already computed, do not invent numbers), respond ONLY with a JSON object "
        "with key 'insights': an array of objects {title, detail} giving concise, actionable "
        "business insights and promotion suggestions based ONLY on the provided numbers.",
        f"Aggregates: {agg}",
    )
    insights = fallback_insights
    source = "fallback"
    if ai_result and isinstance(ai_result.get("insights"), list):
        try:
            insights = [InsightItem(**i) for i in ai_result["insights"]]
            source = "ai"
        except Exception:
            insights = fallback_insights

    return RestaurantInsightsResponse(
        restaurant_id=restaurant_id,
        total_orders=agg["total_orders"],
        total_revenue=agg["total_revenue"],
        average_order_value=agg["average_order_value"],
        popular_items=agg["popular_items"],
        low_performing_items=agg["low_performing_items"],
        peak_hours=agg["peak_hours"],
        insights=insights,
        source=source,
    )
