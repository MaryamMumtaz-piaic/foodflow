from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_user, require_role
from app.schemas.auth import AddressCreate, AddressUpdate, ProfileUpdate, UserPublic
from app.services import auth_service
from app.utils.json_store import addresses_store, users_store
from app.utils.validation import is_valid_phone, new_id, sanitize_text

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("/profile", response_model=UserPublic)
def get_profile(user: dict = Depends(require_role("customer"))):
    return UserPublic(**auth_service.public_user(user))


@router.put("/profile", response_model=UserPublic)
def update_profile(payload: ProfileUpdate, user: dict = Depends(require_role("customer"))):
    patch = {}
    if payload.name:
        patch["name"] = sanitize_text(payload.name)
    if payload.phone:
        if not is_valid_phone(payload.phone):
            raise HTTPException(status_code=422, detail="Invalid phone number.")
        patch["phone"] = payload.phone
    updated = users_store.update(user["id"], patch) if patch else user
    return UserPublic(**auth_service.public_user(updated))


@router.get("/addresses")
def list_addresses(user: dict = Depends(require_role("customer"))):
    return addresses_store.find_many(lambda a: a["user_id"] == user["id"])


@router.post("/addresses", status_code=status.HTTP_201_CREATED)
def add_address(payload: AddressCreate, user: dict = Depends(require_role("customer"))):
    record = payload.model_dump()
    record["id"] = new_id("addr_")
    record["user_id"] = user["id"]
    record["recipient_name"] = sanitize_text(record["recipient_name"])
    if not is_valid_phone(record["phone"]):
        raise HTTPException(status_code=422, detail="Invalid phone number.")
    if record.get("is_default"):
        for a in addresses_store.find_many(lambda a: a["user_id"] == user["id"]):
            addresses_store.update(a["id"], {"is_default": False})
    addresses_store.create(record)
    return record


@router.put("/addresses/{address_id}")
def update_address(address_id: str, payload: AddressUpdate, user: dict = Depends(require_role("customer"))):
    existing = addresses_store.get(address_id)
    if not existing or existing["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Address not found.")
    patch = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if patch.get("is_default"):
        for a in addresses_store.find_many(lambda a: a["user_id"] == user["id"]):
            addresses_store.update(a["id"], {"is_default": False})
    return addresses_store.update(address_id, patch)


@router.delete("/addresses/{address_id}")
def delete_address(address_id: str, user: dict = Depends(require_role("customer"))):
    existing = addresses_store.get(address_id)
    if not existing or existing["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Address not found.")
    addresses_store.delete(address_id)
    return {"message": "Address deleted."}
