from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import require_role
from app.models.delivery import DeliveryStatus
from app.schemas.auth import UserPublic
from app.schemas.delivery import DeliveryIssueRequest, DeliveryStatusUpdateRequest, RiderStatusUpdate
from app.services import auth_service, delivery_service
from app.utils.json_store import deliveries_store, orders_store, restaurants_store, users_store

router = APIRouter(prefix="/api/riders", tags=["riders"])


@router.get("/profile")
def get_profile(user: dict = Depends(require_role("rider"))):
    return {**auth_service.public_user(user), "rider_online": user.get("rider_online", False), "rider_approved": user.get("rider_approved", True)}


@router.patch("/status")
def update_status(payload: RiderStatusUpdate, user: dict = Depends(require_role("rider"))):
    updated = users_store.update(user["id"], {"rider_online": payload.online})
    return {"rider_online": updated["rider_online"]}


@router.get("/deliveries")
def list_deliveries(status: Optional[str] = None, user: dict = Depends(require_role("rider"))):
    return delivery_service.list_rider_deliveries(user["id"], status)


@router.get("/deliveries/{delivery_id}")
def get_delivery(delivery_id: str, user: dict = Depends(require_role("rider"))):
    delivery = deliveries_store.get(delivery_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found.")
    if delivery.get("rider_id") not in (None, user["id"]):
        raise HTTPException(status_code=403, detail="This delivery is assigned to another rider.")
    order = orders_store.get(delivery["order_id"])
    restaurant = restaurants_store.get(delivery["restaurant_id"])
    return {"delivery": delivery, "order": order, "restaurant": restaurant}


@router.patch("/deliveries/{delivery_id}/status")
def update_delivery_status(delivery_id: str, payload: DeliveryStatusUpdateRequest, user: dict = Depends(require_role("rider"))):
    delivery = deliveries_store.get(delivery_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found.")
    if delivery.get("rider_id") is None and payload.status == DeliveryStatus.accepted:
        delivery_service.assign_rider(delivery_id, user["id"])
    elif delivery.get("rider_id") != user["id"]:
        raise HTTPException(status_code=403, detail="This delivery is not assigned to you.")
    try:
        return delivery_service.update_delivery_status(delivery_id, payload.status)
    except delivery_service.DeliveryError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/deliveries/{delivery_id}/issue")
def report_issue(delivery_id: str, payload: DeliveryIssueRequest, user: dict = Depends(require_role("rider"))):
    delivery = deliveries_store.get(delivery_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found.")
    if delivery.get("rider_id") != user["id"]:
        raise HTTPException(status_code=403, detail="This delivery is not assigned to you.")
    return delivery_service.report_issue(delivery_id, payload.type.value, payload.description)
