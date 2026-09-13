"""FoodFlow FastAPI application factory."""
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.routes import (
    admin,
    ai,
    auth,
    cart,
    coupons,
    customers,
    menu,
    orders,
    restaurants,
    reviews,
    riders,
)

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="FoodFlow API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# ---------------------------------------------------------------- API routers
app.include_router(auth.router)
app.include_router(customers.router)
app.include_router(restaurants.router)
app.include_router(menu.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(reviews.router)
app.include_router(coupons.router)
app.include_router(riders.router)
app.include_router(admin.router)
app.include_router(ai.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "ai_enabled": settings.ai_enabled, "env": settings.APP_ENV}


# ---------------------------------------------------------------- HTML pages
def _render(request: Request, template_name: str, **context):
    return templates.TemplateResponse(request, template_name, context)


@app.get("/")
def page_home(request: Request):
    return _render(request, "index.html")


@app.get("/restaurants")
def page_restaurants(request: Request):
    return _render(request, "restaurants.html")


@app.get("/restaurant-detail")
def page_restaurant_detail(request: Request):
    return _render(request, "restaurant-detail.html")


@app.get("/food-detail")
def page_food_detail(request: Request):
    return _render(request, "food-detail.html")


@app.get("/cart")
def page_cart(request: Request):
    return _render(request, "cart.html")


@app.get("/checkout")
def page_checkout(request: Request):
    return _render(request, "checkout.html")


@app.get("/order-tracking")
def page_order_tracking(request: Request):
    return _render(request, "order-tracking.html")


@app.get("/order-confirmation")
def page_order_confirmation(request: Request):
    return _render(request, "order-confirmation.html")


@app.get("/order-history")
def page_order_history(request: Request):
    return _render(request, "order-history.html")


@app.get("/support")
def page_support(request: Request):
    return _render(request, "support.html")


@app.get("/profile")
def page_profile(request: Request):
    return _render(request, "profile.html")


@app.get("/dashboard/restaurant")
def page_restaurant_dashboard(request: Request):
    return _render(request, "restaurant-dashboard.html")


@app.get("/dashboard/rider")
def page_rider_dashboard(request: Request):
    return _render(request, "rider-dashboard.html")


@app.get("/dashboard/admin")
def page_admin_dashboard(request: Request):
    return _render(request, "admin-dashboard.html")
