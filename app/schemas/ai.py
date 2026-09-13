"""Structured request/response schemas for AI agent routes.

Every agent's output is validated against one of these pydantic models
before being returned to the client, whether it came from OpenAI or the
deterministic rule-based fallback.
"""
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------- requests
class FoodSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)


class RecommendationRequest(BaseModel):
    query: Optional[str] = None
    preferences: Optional[dict] = None
    restaurant_id: Optional[str] = None
    limit: int = 6


class MenuAnalysisRequest(BaseModel):
    menu_item_id: Optional[str] = None
    name: Optional[str] = None
    ingredients: Optional[list[str]] = None


class DeliveryEstimateRequest(BaseModel):
    restaurant_id: str
    delivery_area: Optional[str] = None


class CustomerSupportRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    order_id: Optional[str] = None
    customer_id: Optional[str] = None


class RestaurantInsightsRequest(BaseModel):
    restaurant_id: str


class RiskAnalysisRequest(BaseModel):
    customer_id: Optional[str] = None
    order_id: Optional[str] = None


# ---------------------------------------------------------------- responses
class PreferenceCriteria(BaseModel):
    meal_type: Optional[str] = None
    cuisine: Optional[str] = None
    dietary_preference: Optional[str] = None
    allergies: list[str] = Field(default_factory=list)
    spice_preference: Optional[str] = None
    servings: Optional[int] = None
    budget: Optional[float] = None
    currency: str = "PKR"
    max_delivery_minutes: Optional[int] = None
    keywords: list[str] = Field(default_factory=list)
    source: str = "fallback"  # "ai" | "fallback"


class RecommendedItem(BaseModel):
    menu_item_id: str
    name: str
    restaurant_id: str
    restaurant_name: str
    price: float
    rating: float
    reason: str


class RecommendationResponse(BaseModel):
    criteria: PreferenceCriteria
    recommendations: list[RecommendedItem] = Field(default_factory=list)
    source: str = "fallback"


class MenuAnalysisResponse(BaseModel):
    menu_item_id: Optional[str] = None
    detected_allergens: list[str] = Field(default_factory=list)
    dietary_labels: list[str] = Field(default_factory=list)
    estimated_spice_level: str = "unknown"
    uncertain_ingredients: list[str] = Field(default_factory=list)
    customization_suggestions: list[str] = Field(default_factory=list)
    disclaimer: str = (
        "This allergen and dietary information is AI-assisted and informational only. "
        "It does not replace professional medical advice or direct confirmation from the restaurant."
    )
    source: str = "fallback"


class DeliveryEstimateResponse(BaseModel):
    restaurant_id: str
    estimated_preparation_minutes: int
    estimated_delivery_minutes_min: int
    estimated_delivery_minutes_max: int
    factors: list[str] = Field(default_factory=list)
    disclaimer: str = "This is an estimate and actual delivery time may vary."
    source: str = "fallback"


class SupportResponse(BaseModel):
    answer: str
    order_status: Optional[str] = None
    escalate: bool = False
    suggested_actions: list[str] = Field(default_factory=list)
    source: str = "fallback"


class InsightItem(BaseModel):
    title: str
    detail: str


class RestaurantInsightsResponse(BaseModel):
    restaurant_id: str
    total_orders: int
    total_revenue: float
    average_order_value: float
    popular_items: list[str] = Field(default_factory=list)
    low_performing_items: list[str] = Field(default_factory=list)
    peak_hours: list[str] = Field(default_factory=list)
    insights: list[InsightItem] = Field(default_factory=list)
    source: str = "fallback"


class RiskFlag(BaseModel):
    type: str
    description: str
    severity: str = "low"  # low | medium | high


class RiskAnalysisResponse(BaseModel):
    subject_id: Optional[str] = None
    risk_score: int = 0
    flags: list[RiskFlag] = Field(default_factory=list)
    recommendation: str = "No action required. Continue monitoring."
    source: str = "fallback"
