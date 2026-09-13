"""Menu Intelligence Agent (Section 10.3).

Analyzes ingredients to flag allergens, dietary labels, and spice level.
Falls back to an ingredient-keyword table when OpenAI is unavailable.
Allergen output is always informational (never a medical guarantee).
"""
from app.agents.base import call_json_agent
from app.schemas.ai import MenuAnalysisResponse
from app.utils.json_store import menu_items_store

SYSTEM_PROMPT = (
    "You are a food menu intelligence assistant for FoodFlow. Given an item name and "
    "ingredient list, respond ONLY with a JSON object with keys: detected_allergens (array), "
    "dietary_labels (array from: vegetarian, vegan, halal, gluten_free, dairy_free, nut_free, keto, "
    "non_vegetarian), estimated_spice_level (one of none, mild, medium, hot, extra_hot), "
    "uncertain_ingredients (array of ingredient names you are not confident about), "
    "customization_suggestions (array of short strings). Never claim certainty about allergens; "
    "list only what is reasonably inferable from ingredient names."
)

ALLERGEN_KEYWORDS = {
    "peanut": "peanuts",
    "cashew": "tree nuts",
    "almond": "tree nuts",
    "walnut": "tree nuts",
    "milk": "dairy",
    "cheese": "dairy",
    "cream": "dairy",
    "butter": "dairy",
    "yogurt": "dairy",
    "egg": "eggs",
    "wheat": "gluten",
    "flour": "gluten",
    "bread": "gluten",
    "soy": "soy",
    "soya": "soy",
    "shrimp": "shellfish",
    "prawn": "shellfish",
    "crab": "shellfish",
    "fish": "fish",
    "sesame": "sesame",
}

MEAT_KEYWORDS = ["chicken", "beef", "mutton", "lamb", "fish", "prawn", "shrimp", "meat", "egg"]
VEGAN_EXCLUDE = ["milk", "cheese", "cream", "butter", "yogurt", "honey", "ghee"] + MEAT_KEYWORDS
SPICE_HINT_KEYWORDS = {
    "extra_hot": ["extra spicy", "very hot", "ghost pepper"],
    "hot": ["spicy", "chili", "chilli", "hot sauce", "masala"],
    "medium": ["curry", "karahi", "tikka"],
    "mild": ["mild", "creamy", "korma"],
}


def _fallback_analyze(name: str, ingredients: list[str]) -> MenuAnalysisResponse:
    text_ingredients = [i.lower() for i in ingredients]
    joined = " ".join(text_ingredients + [name.lower()])

    detected_allergens = sorted({
        label for kw, label in ALLERGEN_KEYWORDS.items() if kw in joined
    })

    dietary_labels = []
    if not any(m in joined for m in MEAT_KEYWORDS):
        dietary_labels.append("vegetarian")
        if not any(v in joined for v in VEGAN_EXCLUDE):
            dietary_labels.append("vegan")
    else:
        dietary_labels.append("non_vegetarian")
    if "halal" in joined:
        dietary_labels.append("halal")
    if "gluten" not in detected_allergens:
        dietary_labels.append("gluten_free")
    if "dairy" not in detected_allergens:
        dietary_labels.append("dairy_free")

    spice_level = "none"
    for level, keywords in SPICE_HINT_KEYWORDS.items():
        if any(k in joined for k in keywords):
            spice_level = level
            break

    known_food_words = set(ALLERGEN_KEYWORDS.keys()) | set(MEAT_KEYWORDS) | {"rice", "onion", "garlic", "tomato", "oil", "salt", "pepper", "sauce"}
    uncertain = [i for i in ingredients if not any(k in i.lower() for k in known_food_words)]

    suggestions = ["Ask for less spice", "Request no onions/garlic", "Ask for extra sauce on the side"]

    return MenuAnalysisResponse(
        detected_allergens=detected_allergens,
        dietary_labels=dietary_labels,
        estimated_spice_level=spice_level,
        uncertain_ingredients=uncertain,
        customization_suggestions=suggestions,
        source="fallback",
    )


def analyze_menu_item(menu_item_id: str | None, name: str | None, ingredients: list[str] | None) -> MenuAnalysisResponse:
    if menu_item_id:
        item = menu_items_store.get(menu_item_id)
        if item:
            name = item["name"]
            ingredients = item.get("ingredients", [])

    name = name or ""
    ingredients = ingredients or []

    ai_result = call_json_agent(SYSTEM_PROMPT, f"Item name: {name}\nIngredients: {', '.join(ingredients)}")
    if ai_result:
        try:
            ai_result.setdefault("source", "ai")
            ai_result["menu_item_id"] = menu_item_id
            return MenuAnalysisResponse(**ai_result)
        except Exception:
            pass

    result = _fallback_analyze(name, ingredients)
    result.menu_item_id = menu_item_id
    return result
