from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from app.agents import risk_agent
from app.dependencies import require_role
from app.schemas.delivery import RestaurantApprovalRequest, RiderApprovalRequest
from app.utils.json_store import (
    complaints_store,
    deliveries_store,
    orders_store,
    restaurants_store,
    reviews_store,
    users_store,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/overview")
def overview(user: dict = Depends(require_role("admin"))):
    users = users_store.list_all()
    restaurants = restaurants_store.list_all()
    riders = [u for u in users if u["role"] == "rider"]
    customers = [u for u in users if u["role"] == "customer"]
    orders = orders_store.list_all()
    active_statuses = {"pending", "accepted", "preparing", "ready_for_pickup", "rider_assigned", "picked_up", "out_for_delivery"}
    active_orders = [o for o in orders if o["status"] in active_statuses]
    delivered = [o for o in orders if o["status"] == "delivered"]
    cancelled = [o for o in orders if o["status"] in ("cancelled", "failed", "rejected")]
    total_revenue = round(sum(o["final_total"] for o in delivered), 2)
    cancellation_rate = round((len(cancelled) / len(orders)) * 100, 1) if orders else 0.0

    deliveries = deliveries_store.list_all()
    durations = []
    for d in deliveries:
        if d.get("assigned_at") and d.get("delivered_at"):
            try:
                start = datetime.fromisoformat(d["assigned_at"])
                end = datetime.fromisoformat(d["delivered_at"])
                durations.append((end - start).total_seconds() / 60)
            except Exception:
                continue
    avg_delivery_time = round(sum(durations) / len(durations), 1) if durations else None

    return {
        "total_customers": len(customers),
        "total_restaurants": len(restaurants),
        "total_riders": len(riders),
        "total_orders": len(orders),
        "total_revenue": total_revenue,
        "active_orders": len(active_orders),
        "pending_restaurant_approvals": len([r for r in restaurants if r.get("approval_status") == "pending"]),
        "pending_rider_approvals": len([u for u in riders if not u.get("rider_approved", True)]),
        "average_delivery_time_minutes": avg_delivery_time,
        "cancellation_rate": cancellation_rate,
    }


@router.get("/customers")
def list_customers(search: Optional[str] = None, user: dict = Depends(require_role("admin"))):
    customers = [u for u in users_store.list_all() if u["role"] == "customer"]
    if search:
        s = search.lower()
        customers = [c for c in customers if s in c["name"].lower() or s in c["email"].lower()]
    return [{k: v for k, v in c.items() if k != "password_hash"} for c in customers]


@router.patch("/customers/{customer_id}/status")
def update_customer_status(customer_id: str, payload: dict, user: dict = Depends(require_role("admin"))):
    customer = users_store.get(customer_id)
    if not customer or customer["role"] != "customer":
        raise HTTPException(status_code=404, detail="Customer not found.")
    new_status = payload.get("status")
    if new_status not in ("active", "suspended"):
        raise HTTPException(status_code=422, detail="Invalid status.")
    updated = users_store.update(customer_id, {"status": new_status})
    return {k: v for k, v in updated.items() if k != "password_hash"}


@router.get("/restaurants")
def list_restaurants(approval_status: Optional[str] = None, user: dict = Depends(require_role("admin"))):
    rows = restaurants_store.list_all()
    if approval_status:
        rows = [r for r in rows if r.get("approval_status") == approval_status]
    return rows


@router.get("/riders")
def list_riders(user: dict = Depends(require_role("admin"))):
    riders = [u for u in users_store.list_all() if u["role"] == "rider"]
    return [{k: v for k, v in r.items() if k != "password_hash"} for r in riders]


@router.get("/orders")
def list_orders(status_filter: Optional[str] = None, search: Optional[str] = None, user: dict = Depends(require_role("admin"))):
    rows = orders_store.list_all()
    if status_filter:
        rows = [o for o in rows if o["status"] == status_filter]
    if search:
        rows = [o for o in rows if search.lower() in o["id"].lower()]
    return sorted(rows, key=lambda o: o["created_at"], reverse=True)


@router.patch("/restaurants/{restaurant_id}/approval")
def update_restaurant_approval(restaurant_id: str, payload: RestaurantApprovalRequest, user: dict = Depends(require_role("admin"))):
    if not restaurants_store.get(restaurant_id):
        raise HTTPException(status_code=404, detail="Restaurant not found.")
    if payload.approval_status not in ("approved", "rejected", "suspended", "pending"):
        raise HTTPException(status_code=422, detail="Invalid approval status.")
    return restaurants_store.update(restaurant_id, {"approval_status": payload.approval_status})


@router.patch("/riders/{rider_id}/approval")
def update_rider_approval(rider_id: str, payload: RiderApprovalRequest, user: dict = Depends(require_role("admin"))):
    rider = users_store.get(rider_id)
    if not rider or rider["role"] != "rider":
        raise HTTPException(status_code=404, detail="Rider not found.")
    status_value = "active" if payload.approved else "suspended"
    return users_store.update(rider_id, {"rider_approved": payload.approved, "status": status_value})


@router.get("/complaints")
def list_complaints(user: dict = Depends(require_role("admin"))):
    return complaints_store.list_all()


@router.get("/risk-alerts")
def list_risk_alerts(user: dict = Depends(require_role("admin"))):
    customers = [u for u in users_store.list_all() if u["role"] == "customer"]
    alerts = []
    for c in customers:
        result = risk_agent.analyze_risk(c["id"], None)
        if result.flags:
            alerts.append(result.model_dump())
    return alerts
