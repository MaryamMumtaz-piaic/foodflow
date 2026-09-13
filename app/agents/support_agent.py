"""Customer Support Agent (Section 10.5).

Answers order-related questions using real backend order data. Never
claims a refund/cancellation/account change happened unless the backend
actually confirms it (status is read directly from orders.json).
"""
from app.agents.base import call_json_agent
from app.schemas.ai import SupportResponse
from app.utils.json_store import orders_store

SYSTEM_PROMPT = (
    "You are FoodFlow's customer support assistant. You are given the customer's message and, "
    "if available, their order's real current status from the backend. Respond ONLY with a JSON "
    "object with keys: answer (string), order_status (string or null), escalate (bool), "
    "suggested_actions (array of short strings). NEVER claim a refund, cancellation, or account "
    "change has been completed — only report the actual order_status provided to you. If the "
    "request needs a human (e.g. a dispute, safety issue, or something the data can't confirm), "
    "set escalate to true."
)

STATUS_EXPLANATIONS = {
    "pending": "Your order has been placed and is waiting for the restaurant to accept it.",
    "accepted": "The restaurant has accepted your order and will begin preparing it shortly.",
    "preparing": "The restaurant is currently preparing your food.",
    "ready_for_pickup": "Your food is ready and waiting for a rider to pick it up.",
    "rider_assigned": "A rider has been assigned to your order.",
    "picked_up": "Your order has been picked up by the rider.",
    "out_for_delivery": "Your order is on its way to you.",
    "delivered": "Your order has been delivered.",
    "cancelled": "Your order was cancelled.",
    "failed": "Delivery of this order was unsuccessful.",
    "rejected": "Unfortunately, the restaurant rejected this order.",
}

ESCALATE_KEYWORDS = ["human", "agent", "manager", "unacceptable", "safety", "unsafe", "fraud", "legal"]


def _fallback_support(message: str, order: dict | None) -> SupportResponse:
    msg = message.lower()
    suggested = []
    escalate = any(k in msg for k in ESCALATE_KEYWORDS)

    if order:
        status = order["status"]
        explanation = STATUS_EXPLANATIONS.get(status, "Status information is unavailable.")
        if "cancel" in msg:
            can_cancel_now = status in ("pending", "accepted", "preparing", "ready_for_pickup", "rider_assigned")
            if can_cancel_now:
                answer = (
                    f"{explanation} You can still cancel this order from the order tracking page — "
                    "cancellation has not been performed yet; please confirm there to cancel it."
                )
                suggested.append("Cancel order from tracking page")
            else:
                answer = f"{explanation} This order can no longer be cancelled because of its current status."
        elif "refund" in msg:
            answer = (
                f"{explanation} No refund has been processed on your order yet. "
                "Refund requests for delivered or cancelled orders are reviewed by our team; "
                "you can escalate this for a human agent to check eligibility."
            )
            suggested.append("Escalate to support team")
            escalate = True
        elif "delay" in msg or "late" in msg or "where" in msg:
            answer = f"{explanation} If it is taking longer than expected, our delivery agent estimates may help; you can also contact the rider once assigned."
            suggested.append("Check order tracking page")
        else:
            answer = explanation
        order_status = status
    else:
        answer = (
            "I couldn't find that order in our system. Please double-check the order ID, "
            "or ask a general question about FoodFlow (delivery times, coupons, payments, etc.)."
        )
        order_status = None
        escalate = escalate or True if "order" in msg else escalate

    if not suggested:
        suggested = ["View order tracking", "Contact restaurant", "Browse FAQs"]

    return SupportResponse(
        answer=answer,
        order_status=order_status,
        escalate=escalate,
        suggested_actions=suggested,
        source="fallback",
    )


def get_support_response(message: str, order_id: str | None, customer_id: str | None) -> SupportResponse:
    order = orders_store.get(order_id) if order_id else None
    if order and customer_id and order.get("customer_id") != customer_id:
        # Never leak another customer's order details.
        order = None

    context = f"Customer message: {message}\n"
    if order:
        context += f"Real order status from backend: {order['status']}\nPayment status: {order.get('payment_status')}\n"
    else:
        context += "No matching order found in backend for this customer.\n"

    ai_result = call_json_agent(SYSTEM_PROMPT, context)
    if ai_result:
        try:
            ai_result.setdefault("source", "ai")
            if order:
                ai_result["order_status"] = order["status"]  # never trust AI's own claim
            return SupportResponse(**ai_result)
        except Exception:
            pass

    return _fallback_support(message, order)
