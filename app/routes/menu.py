from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import require_role
from app.schemas.menu import AvailabilityUpdate, CategoryCreate, MenuItemCreate, MenuItemUpdate
from app.utils.json_store import categories_store, menu_items_store, restaurants_store
from app.utils.validation import new_id, sanitize_text

router = APIRouter(tags=["menu"])


def _assert_owns_restaurant(user: dict, restaurant_id: str):
    if user["role"] == "admin":
        return
    if user["role"] != "restaurant" or user.get("restaurant_id") != restaurant_id:
        raise HTTPException(status_code=403, detail="You do not manage this restaurant.")


@router.get("/api/restaurants/{restaurant_id}/menu")
def get_menu(restaurant_id: str, available_only: bool = False, search: Optional[str] = None):
    restaurant = restaurants_store.get(restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found.")
    from app.services import restaurant_service

    items = restaurant_service.get_menu(restaurant_id, available_only, search)
    categories = restaurant_service.get_categories(restaurant_id)
    return {"categories": categories, "items": items}


@router.get("/api/menu-items/{item_id}")
def get_menu_item(item_id: str):
    item = menu_items_store.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found.")
    return item


@router.post("/api/restaurants/{restaurant_id}/menu", status_code=status.HTTP_201_CREATED)
def create_menu_item(restaurant_id: str, payload: MenuItemCreate, user: dict = Depends(require_role("restaurant", "admin"))):
    _assert_owns_restaurant(user, restaurant_id)
    restaurant = restaurants_store.get(restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found.")
    record = payload.model_dump()
    record["id"] = new_id("item_")
    record["restaurant_id"] = restaurant_id
    record["name"] = sanitize_text(record["name"])
    record["description"] = sanitize_text(record.get("description", ""))
    record["image"] = record.get("image") or ("https://picsum.photos/seed/" + record["id"] + "/400/300")
    record["rating"] = 0.0
    record["order_count"] = 0
    menu_items_store.create(record)
    return record


@router.post("/api/restaurants/{restaurant_id}/categories", status_code=status.HTTP_201_CREATED)
def create_category(restaurant_id: str, payload: CategoryCreate, user: dict = Depends(require_role("restaurant", "admin"))):
    _assert_owns_restaurant(user, restaurant_id)
    record = payload.model_dump()
    record["id"] = new_id("cat_")
    record["restaurant_id"] = restaurant_id
    categories_store.create(record)
    return record


@router.put("/api/menu-items/{item_id}")
def update_menu_item(item_id: str, payload: MenuItemUpdate, user: dict = Depends(require_role("restaurant", "admin"))):
    item = menu_items_store.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found.")
    _assert_owns_restaurant(user, item["restaurant_id"])
    patch = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if "name" in patch:
        patch["name"] = sanitize_text(patch["name"])
    if "description" in patch:
        patch["description"] = sanitize_text(patch["description"])
    return menu_items_store.update(item_id, patch)


@router.delete("/api/menu-items/{item_id}")
def delete_menu_item(item_id: str, user: dict = Depends(require_role("restaurant", "admin"))):
    item = menu_items_store.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found.")
    _assert_owns_restaurant(user, item["restaurant_id"])
    menu_items_store.delete(item_id)
    return {"message": "Menu item deleted."}


@router.patch("/api/menu-items/{item_id}/availability")
def update_availability(item_id: str, payload: AvailabilityUpdate, user: dict = Depends(require_role("restaurant", "admin"))):
    item = menu_items_store.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found.")
    _assert_owns_restaurant(user, item["restaurant_id"])
    return menu_items_store.update(item_id, {"is_available": payload.is_available})
