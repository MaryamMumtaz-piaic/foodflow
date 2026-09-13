from fastapi import APIRouter, Depends

from app.agents import (
    delivery_agent,
    insights_agent,
    menu_agent,
    preference_agent,
    recommendation_agent,
    risk_agent,
    support_agent,
)
from app.dependencies import get_current_user, get_optional_user, require_role
from app.schemas.ai import (
    CustomerSupportRequest,
    DeliveryEstimateRequest,
    FoodSearchRequest,
    MenuAnalysisRequest,
    RecommendationRequest,
    RestaurantInsightsRequest,
    RiskAnalysisRequest,
)

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/food-search")
def food_search(payload: FoodSearchRequest):
    criteria = preference_agent.extract_preferences(payload.query)
    result = recommendation_agent.recommend(criteria)
    return result


@router.post("/recommendations")
def recommendations(payload: RecommendationRequest):
    if payload.query:
        criteria = preference_agent.extract_preferences(payload.query)
    else:
        from app.schemas.ai import PreferenceCriteria

        criteria = PreferenceCriteria(**(payload.preferences or {}))
    return recommendation_agent.recommend(criteria, payload.restaurant_id, payload.limit)


@router.post("/menu-analysis")
def menu_analysis(payload: MenuAnalysisRequest):
    return menu_agent.analyze_menu_item(payload.menu_item_id, payload.name, payload.ingredients)


@router.post("/delivery-estimate")
def delivery_estimate(payload: DeliveryEstimateRequest):
    return delivery_agent.estimate_delivery(payload.restaurant_id, payload.delivery_area)


@router.post("/customer-support")
def customer_support(payload: CustomerSupportRequest, user: dict | None = Depends(get_optional_user)):
    customer_id = user["id"] if user else payload.customer_id
    return support_agent.get_support_response(payload.message, payload.order_id, customer_id)


@router.post("/restaurant-insights")
def restaurant_insights(payload: RestaurantInsightsRequest, user: dict = Depends(require_role("restaurant", "admin"))):
    if user["role"] == "restaurant" and user.get("restaurant_id") != payload.restaurant_id:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="You may only view insights for your own restaurant.")
    return insights_agent.generate_insights(payload.restaurant_id)


@router.post("/risk-analysis")
def risk_analysis(payload: RiskAnalysisRequest, user: dict = Depends(require_role("admin"))):
    return risk_agent.analyze_risk(payload.customer_id, payload.order_id)
