"""Fraud and Risk Agent (Section 10.7).

Flags heuristic risk signals for human review. NEVER auto-punishes a
user — administrators must act on flags manually via the admin dashboard.
"""
from collections import Counter

from app.schemas.ai import RiskAnalysisResponse, RiskFlag
from app.utils.json_store import orders_store, reviews_store


def _analyze_customer(customer_id: str) -> RiskAnalysisResponse:
    orders = orders_store.find_many(lambda o: o.get("customer_id") == customer_id)
    flags: list[RiskFlag] = []

    cancelled = [o for o in orders if o["status"] in ("cancelled", "failed")]
    if len(orders) >= 3 and len(cancelled) / len(orders) > 0.5:
        flags.append(RiskFlag(
            type="repeated_cancellations",
            description=f"{len(cancelled)} of {len(orders)} orders were cancelled or failed.",
            severity="medium",
        ))

    # Duplicate order detection: same restaurant + same total placed within a short time window.
    signature_counter = Counter((o["restaurant_id"], o["final_total"]) for o in orders)
    duplicates = [sig for sig, count in signature_counter.items() if count >= 3]
    if duplicates:
        flags.append(RiskFlag(
            type="duplicate_orders",
            description=f"{len(duplicates)} order pattern(s) repeated 3+ times with identical restaurant and total.",
            severity="low",
        ))

    reviews = reviews_store.find_many(lambda r: r.get("customer_id") == customer_id)
    low_reviews = [r for r in reviews if r["rating"] <= 2]
    if len(reviews) >= 3 and len(low_reviews) / len(reviews) > 0.6:
        flags.append(RiskFlag(
            type="suspicious_review_pattern",
            description=f"{len(low_reviews)} of {len(reviews)} reviews are very low ratings.",
            severity="low",
        ))

    risk_score = min(100, len(flags) * 30)
    recommendation = (
        "Flagged for manual review by an administrator. No automatic action has been taken."
        if flags
        else "No action required. Continue monitoring."
    )

    return RiskAnalysisResponse(
        subject_id=customer_id,
        risk_score=risk_score,
        flags=flags,
        recommendation=recommendation,
        source="fallback",
    )


def analyze_risk(customer_id: str | None, order_id: str | None) -> RiskAnalysisResponse:
    if order_id and not customer_id:
        order = orders_store.get(order_id)
        if order:
            customer_id = order.get("customer_id")
    if not customer_id:
        return RiskAnalysisResponse(subject_id=None, risk_score=0, flags=[], recommendation="No subject provided.", source="fallback")
    return _analyze_customer(customer_id)
