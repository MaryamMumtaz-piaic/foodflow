from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_current_user, require_role
from app.schemas.menu import CouponCreate, CouponUpdate, CouponValidateRequest, CouponValidateResponse
from app.services import coupon_service
from app.utils.json_store import coupons_store
from app.utils.validation import new_id

router = APIRouter(prefix="/api/coupons", tags=["coupons"])


@router.get("")
def list_coupons(user: dict = Depends(get_current_user)):
    coupons = coupons_store.list_all()
    if user["role"] not in ("admin", "restaurant"):
        coupons = [c for c in coupons if c.get("is_active")]
    return coupons


@router.post("/validate", response_model=CouponValidateResponse)
def validate_coupon(payload: CouponValidateRequest, user: dict = Depends(require_role("customer"))):
    try:
        coupon, discount = coupon_service.validate_coupon(payload.code, payload.subtotal, payload.restaurant_id)
    except coupon_service.CouponError as e:
        return CouponValidateResponse(valid=False, reason=str(e))
    return CouponValidateResponse(valid=True, discount_amount=discount, coupon_code=coupon["code"])


@router.post("", status_code=201)
def create_coupon(payload: CouponCreate, user: dict = Depends(require_role("admin", "restaurant"))):
    if coupon_service.get_coupon_by_code(payload.code):
        raise HTTPException(status_code=400, detail="A coupon with this code already exists.")
    record = payload.model_dump()
    record["id"] = new_id("cpn_")
    record["code"] = record["code"].upper()
    record["used_count"] = 0
    coupons_store.create(record)
    return record


@router.put("/{coupon_id}")
def update_coupon(coupon_id: str, payload: CouponUpdate, user: dict = Depends(require_role("admin", "restaurant"))):
    if not coupons_store.get(coupon_id):
        raise HTTPException(status_code=404, detail="Coupon not found.")
    patch = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    return coupons_store.update(coupon_id, patch)


@router.delete("/{coupon_id}")
def delete_coupon(coupon_id: str, user: dict = Depends(require_role("admin", "restaurant"))):
    if not coupons_store.delete(coupon_id):
        raise HTTPException(status_code=404, detail="Coupon not found.")
    return {"message": "Coupon deleted."}
