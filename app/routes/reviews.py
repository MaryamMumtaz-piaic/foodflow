from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_current_user, require_role
from app.schemas.restaurant import ReviewCreate, ReviewUpdate
from app.services.restaurant_service import recalc_restaurant_rating
from app.utils.json_store import restaurants_store, reviews_store
from app.utils.validation import new_id, sanitize_text

router = APIRouter(tags=["reviews"])


@router.get("/api/restaurants/{restaurant_id}/reviews")
def list_reviews(restaurant_id: str):
    reviews = reviews_store.find_many(
        lambda r: r["restaurant_id"] == restaurant_id and r.get("moderation_status") == "visible"
    )
    return sorted(reviews, key=lambda r: r["created_at"], reverse=True)


@router.post("/api/restaurants/{restaurant_id}/reviews", status_code=201)
def create_review(restaurant_id: str, payload: ReviewCreate, user: dict = Depends(require_role("customer"))):
    if not restaurants_store.get(restaurant_id):
        raise HTTPException(status_code=404, detail="Restaurant not found.")
    record = {
        "id": new_id("rev_"),
        "customer_id": user["id"],
        "customer_name": user["name"],
        "restaurant_id": restaurant_id,
        "order_id": payload.order_id,
        "rating": payload.rating,
        "comment": sanitize_text(payload.comment),
        "created_at": datetime.utcnow().isoformat(),
        "moderation_status": "visible",
    }
    reviews_store.create(record)
    recalc_restaurant_rating(restaurant_id)
    return record


@router.put("/api/reviews/{review_id}")
def update_review(review_id: str, payload: ReviewUpdate, user: dict = Depends(get_current_user)):
    review = reviews_store.get(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found.")
    if user["role"] == "admin":
        pass
    elif user["role"] == "customer" and review["customer_id"] == user["id"]:
        pass
    else:
        raise HTTPException(status_code=403, detail="You can only edit your own review.")
    patch = {}
    if payload.rating is not None:
        patch["rating"] = payload.rating
    if payload.comment is not None:
        patch["comment"] = sanitize_text(payload.comment)
    if payload.moderation_status is not None and user["role"] == "admin":
        patch["moderation_status"] = payload.moderation_status
    updated = reviews_store.update(review_id, patch)
    recalc_restaurant_rating(review["restaurant_id"])
    return updated


@router.delete("/api/reviews/{review_id}")
def delete_review(review_id: str, user: dict = Depends(get_current_user)):
    review = reviews_store.get(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found.")
    if user["role"] not in ("admin",) and review["customer_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="You can only delete your own review.")
    reviews_store.delete(review_id)
    recalc_restaurant_rating(review["restaurant_id"])
    return {"message": "Review deleted."}
