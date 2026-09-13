"""Customer Preference Agent (Section 10.1).

Parses natural-language food requests into structured search criteria.
Falls back to regex/keyword parsing when OpenAI is unavailable.
"""
import re

from app.agents.base import call_json_agent
from app.schemas.ai import PreferenceCriteria

SYSTEM_PROMPT = (
    "You are a food-delivery preference extraction assistant for FoodFlow, a Pakistani "
    "food delivery platform using PKR currency. Extract structured search criteria from "
    "the user's natural-language request. Respond ONLY with a JSON object with these keys: "
    "meal_type, cuisine, dietary_preference, allergies (array), spice_preference, servings (int), "
    "budget (number, PKR), currency (always 'PKR'), max_delivery_minutes (int or null), "
    "keywords (array of important food keywords). Use null for unknown fields."
)

DIETARY_KEYWORDS = {
    "vegetarian": "vegetarian",
    "vegan": "vegan",
    "halal": "halal",
    "gluten free": "gluten_free",
    "gluten-free": "gluten_free",
    "dairy free": "dairy_free",
    "keto": "keto",
}

MEAL_KEYWORDS = ["breakfast", "lunch", "dinner", "snack", "dessert"]
SPICE_KEYWORDS = {
    "extra spicy": "extra_hot",
    "very spicy": "extra_hot",
    "spicy": "hot",
    "mild": "mild",
    "not spicy": "none",
    "no spice": "none",
}
CUISINE_KEYWORDS = [
    "pakistani", "chinese", "italian", "fast food", "bbq", "desi", "continental",
    "thai", "indian", "arabian", "mexican", "japanese", "sushi", "burger", "pizza",
]
ALLERGY_KEYWORDS = ["peanut", "nuts", "dairy", "gluten", "egg", "shellfish", "soy"]


def _fallback_extract(query: str) -> PreferenceCriteria:
    q = query.lower()

    meal_type = next((m for m in MEAL_KEYWORDS if m in q), None)

    dietary = None
    for kw, label in DIETARY_KEYWORDS.items():
        if kw in q:
            dietary = label
            break

    cuisine = next((c for c in CUISINE_KEYWORDS if c in q), None)

    spice = None
    for kw, label in SPICE_KEYWORDS.items():
        if kw in q:
            spice = label
            break

    allergies = [a for a in ALLERGY_KEYWORDS if a in q]

    budget_match = re.search(r"(?:rs\.?\s?|pkr\s?)(\d[\d,]*)", q)
    if not budget_match:
        budget_match = re.search(r"under\s+(\d[\d,]*)", q)
    budget = None
    if budget_match:
        budget = float(budget_match.group(1).replace(",", ""))

    NUMBER_WORDS = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    }
    servings_match = re.search(r"for\s+(\d+)", q)
    if servings_match:
        servings = int(servings_match.group(1))
    else:
        word_match = re.search(r"for\s+(one|two|three|four|five|six|seven|eight|nine|ten)\b", q)
        servings = NUMBER_WORDS[word_match.group(1)] if word_match else None

    minutes_match = re.search(r"(\d+)\s*(?:min|minute)", q)
    max_minutes = int(minutes_match.group(1)) if minutes_match else None

    keywords = [w for w in re.findall(r"[a-zA-Z]+", q) if len(w) > 3][:8]

    return PreferenceCriteria(
        meal_type=meal_type,
        cuisine=cuisine,
        dietary_preference=dietary,
        allergies=allergies,
        spice_preference=spice,
        servings=servings,
        budget=budget,
        currency="PKR",
        max_delivery_minutes=max_minutes,
        keywords=keywords,
        source="fallback",
    )


def extract_preferences(query: str) -> PreferenceCriteria:
    ai_result = call_json_agent(SYSTEM_PROMPT, query)
    if ai_result:
        try:
            ai_result.setdefault("source", "ai")
            return PreferenceCriteria(**ai_result)
        except Exception:
            pass
    return _fallback_extract(query)
