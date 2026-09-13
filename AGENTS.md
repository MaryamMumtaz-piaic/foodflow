# AGENTS.md

This document describes the seven specialized AI agents that power FoodFlow's intelligent features, why they're separated instead of implemented as one large prompt, and the safety constraints each one operates under. See `app/agents/` for implementation and `task.md` §10 for the original specification.

## Design Principle: Specialized Agents Over One Mega-Prompt

Each agent has a single, narrow responsibility, a structured JSON output contract validated against a Pydantic schema (`app/schemas/ai.py`), and a deterministic rule-based fallback that runs whenever `OPENAI_API_KEY` is not configured or the OpenAI API call fails. This means:

- Agents are easy to test, reason about, and replace independently.
- The platform is fully demoable and functional without any API key.
- A malformed or hallucinated model response never reaches the user unvalidated — the response is checked against the schema before being returned by the API.

## The Agents

### 1. Customer Preference Agent (`preference_agent.py`)
Parses a natural-language food request (e.g. *"I want a vegetarian dinner for two under Rs. 2,000"*) into structured search criteria: meal type, cuisine, dietary preference, allergies, spice level, budget, delivery-time constraint, and serving size. Feeds the Food Recommendation Agent.

### 2. Food Recommendation Agent (`recommendation_agent.py`)
Ranks available restaurants/menu items against the structured criteria above, weighing price, rating, availability, and delivery time. Never recommends an unavailable item. Returns a short, human-readable explanation per recommendation.

### 3. Menu Intelligence Agent (`menu_agent.py`)
Analyzes a menu item's ingredients to infer allergens, dietary labels, and spice level, and explains unfamiliar ingredients. Allergen output is explicitly informational — it is not a substitute for direct confirmation from the restaurant or professional medical advice, and the agent states uncertainty rather than guessing confidently.

### 4. Delivery Prediction Agent (`delivery_agent.py`)
Estimates preparation and delivery time from restaurant workload, rider availability, and distance/zone. Every output is labeled as an estimate, with the contributing factors explained.

### 5. Customer Support Agent (`support_agent.py`)
Answers order-status, cancellation, refund, and delay questions using real order data. It must never claim a refund, cancellation, or account change has completed unless the backend has actually confirmed that state — it reports what the system knows, not what it hopes is true — and escalates issues it cannot resolve to a human.

### 6. Restaurant Insights Agent (`insights_agent.py`)
Analyzes a restaurant's order history to surface popular/low-performing dishes, peak ordering periods, preparation bottlenecks, and suggested promotions or menu changes, computed from real aggregated order data rather than invented statistics.

### 7. Fraud and Risk Agent (`risk_agent.py`)
Flags suspicious patterns — repeated refunds, duplicate/unusual orders, suspicious review activity — for administrator review. This agent only flags and explains; it never automatically suspends, bans, or otherwise punishes a user. All enforcement remains a human decision.

## Adding a New Agent

1. Define its input/output schema in `app/schemas/ai.py`.
2. Implement the OpenAI-backed path and a rule-based fallback path in `app/agents/<name>_agent.py`, both returning the same schema.
3. Validate the model's raw response against the schema before returning it — reject and fall back on validation failure rather than passing through unvalidated data.
4. Expose it through a route in `app/routes/ai.py` under `/api/ai/...`, matching the naming pattern of the existing routes.
5. Add a test in `tests/` covering both the fallback path and basic input validation.
