"""Rider / delivery lifecycle business logic."""
from datetime import datetime
from typing import Optional

from app.models.delivery import DeliveryStatus
from app.utils.json_store import deliveries_store, orders_store, users_store
from app.utils.validation import new_id

# Delivery status -> the order status it should drive (Section 13 mapping)
DELIVERY_TO_ORDER_STATUS = {
    DeliveryStatus.assigned: "rider_assigned",
    DeliveryStatus.accepted: "rider_assigned",
    DeliveryStatus.arrived_at_restaurant: "rider_assigned",
    DeliveryStatus.picked_up: "picked_up",
    DeliveryStatus.out_for_delivery: "out_for_delivery",
    DeliveryStatus.delivered: "delivered",
    DeliveryStatus.failed: "failed",
}

ALLOWED_DELIVERY_TRANSITIONS = {
    DeliveryStatus.assigned: {DeliveryStatus.accepted, DeliveryStatus.failed},
    DeliveryStatus.accepted: {DeliveryStatus.arrived_at_restaurant, DeliveryStatus.failed},
    DeliveryStatus.arrived_at_restaurant: {DeliveryStatus.picked_up, DeliveryStatus.failed},
    DeliveryStatus.picked_up: {DeliveryStatus.out_for_delivery, DeliveryStatus.failed},
    DeliveryStatus.out_for_delivery: {DeliveryStatus.delivered, DeliveryStatus.failed},
    DeliveryStatus.delivered: set(),
    DeliveryStatus.failed: set(),
}


class DeliveryError(Exception):
    pass


def create_delivery_for_order(order: dict, restaurant: dict) -> dict:
    delivery = {
        "id": new_id("dlv_"),
        "order_id": order["id"],
        "rider_id": None,
        "restaurant_id": order["restaurant_id"],
        "pickup_address": restaurant.get("address", ""),
        "drop_off_address": order.get("delivery_address", {}).get("street_address", ""),
        "status": DeliveryStatus.assigned.value,
        "estimated_distance_km": 3.5,
        "assigned_at": datetime.utcnow().isoformat(),
        "picked_up_at": None,
        "delivered_at": None,
        "issues": [],
    }
    deliveries_store.create(delivery)
    return delivery


def assign_rider(delivery_id: str, rider_id: str) -> dict:
    delivery = deliveries_store.get(delivery_id)
    if not delivery:
        raise DeliveryError("Delivery not found.")
    rider = users_store.get(rider_id)
    if not rider or rider.get("role") != "rider":
        raise DeliveryError("Rider not found.")
    return deliveries_store.update(delivery_id, {"rider_id": rider_id})


def list_rider_deliveries(rider_id: str, status: Optional[str] = None) -> list[dict]:
    rows = deliveries_store.find_many(lambda d: d.get("rider_id") == rider_id)
    if status:
        rows = [r for r in rows if r.get("status") == status]
    return rows


def list_unassigned_deliveries() -> list[dict]:
    return deliveries_store.find_many(lambda d: d.get("rider_id") is None and d.get("status") != "delivered")


def update_delivery_status(delivery_id: str, target: DeliveryStatus) -> dict:
    delivery = deliveries_store.get(delivery_id)
    if not delivery:
        raise DeliveryError("Delivery not found.")
    current = DeliveryStatus(delivery["status"])
    allowed = ALLOWED_DELIVERY_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise DeliveryError(f"Cannot transition delivery from '{current.value}' to '{target.value}'.")

    patch = {"status": target.value}
    if target == DeliveryStatus.picked_up:
        patch["picked_up_at"] = datetime.utcnow().isoformat()
    if target == DeliveryStatus.delivered:
        patch["delivered_at"] = datetime.utcnow().isoformat()
    updated = deliveries_store.update(delivery_id, patch)

    # Propagate to order status
    order_status = DELIVERY_TO_ORDER_STATUS.get(target)
    if order_status:
        orders_store.update(delivery["order_id"], {"status": order_status, "updated_at": datetime.utcnow().isoformat()})

    return updated


def report_issue(delivery_id: str, issue_type: str, description: Optional[str]) -> dict:
    delivery = deliveries_store.get(delivery_id)
    if not delivery:
        raise DeliveryError("Delivery not found.")
    issues = delivery.get("issues", [])
    issues.append({
        "type": issue_type,
        "description": description,
        "reported_at": datetime.utcnow().isoformat(),
    })
    return deliveries_store.update(delivery_id, {"issues": issues})
