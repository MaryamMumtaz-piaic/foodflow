from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_current_user, require_role
from app.schemas.restaurant import RestaurantCreate, RestaurantUpdate
from app.services import restaurant_service
from app.utils.json_store import restaurants_store
from app.utils.validation import new_id, sanitize_text

router = APIRouter(prefix="/api/restaurants", tags=["restaurants"])


@router.get("")
def list_restaurants(
    cuisine: Optional[str] = None,
    min_rating: Optional[float] = None,
    open_now: Optional[bool] = None,
    max_delivery_fee: Optional[float] = None,
    search: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
):
    rows = restaurant_service.list_restaurants(cuisine, min_rating, open_now, max_delivery_fee, search)
    total = len(rows)
    start = (page - 1) * page_size
    page_rows = rows[start : start + page_size]
    return {"items": page_rows, "total": total, "page": page, "page_size": page_size}


@router.get("/{restaurant_id}")
def get_restaurant(restaurant_id: str):
    restaurant = restaurant_service.get_restaurant(restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found.")
    return restaurant


@router.post("", status_code=status.HTTP_201_CREATED)
def create_restaurant(payload: RestaurantCreate, user: dict = Depends(require_role("restaurant", "admin"))):
    record = payload.model_dump()
    record["id"] = new_id("res_")
    record["name"] = sanitize_text(record["name"])
    record["description"] = sanitize_text(record.get("description", ""))
    record["logo"] = record.get("logo") or ("https://picsum.photos/seed/" + record["id"] + "-logo/200/200")
    record["cover_image"] = record.get("cover_image") or ("https://picsum.photos/seed/" + record["id"] + "-cover/800/500")
    record["rating"] = 0.0
    record["review_count"] = 0
    record["is_open"] = True
    record["availability_status"] = True
    record["approval_status"] = "pending" if user["role"] == "restaurant" else "approved"
    record["owner_user_id"] = user["id"]
    record["opening_hours"] = {"open": "09:00", "close": "23:00"}
    record["price_range"] = "$$"
    record["popular_dish"] = None
    restaurants_store.create(record)
    return record


@router.put("/{restaurant_id}")
def update_restaurant(restaurant_id: str, payload: RestaurantUpdate, user: dict = Depends(require_role("restaurant", "admin"))):
    restaurant = restaurants_store.get(restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found.")
    if user["role"] == "restaurant" and user.get("restaurant_id") != restaurant_id:
        raise HTTPException(status_code=403, detail="You may only update your own restaurant.")
    patch = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if "name" in patch:
        patch["name"] = sanitize_text(patch["name"])
    if "description" in patch:
        patch["description"] = sanitize_text(patch["description"])
    return restaurants_store.update(restaurant_id, patch)


@router.delete("/{restaurant_id}")
def delete_restaurant(restaurant_id: str, user: dict = Depends(require_role("admin"))):
    if not restaurants_store.delete(restaurant_id):
        raise HTTPException(status_code=404, detail="Restaurant not found.")
    return {"message": "Restaurant deleted."}
