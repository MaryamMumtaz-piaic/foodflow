# 🍔 FoodFlow — AI-Powered Food Delivery Platform

FoodFlow is a complete food-delivery web application connecting **customers**, **restaurants**, **delivery riders**, and **administrators** in one modern, responsive platform — enhanced with specialized AI agents for natural-language food search, recommendations, menu intelligence, delivery estimation, customer support, business insights, and fraud detection.

Built as a production-inspired portfolio project with a Python/FastAPI backend and a server-rendered, vanilla-JS frontend.

## ✨ Features

- **Customer experience** — restaurant discovery, natural-language food search, cart & customization, coupons, simulated checkout, live order tracking, order history, favorites, and AI customer support.
- **Restaurant dashboard** — menu management, order pipeline (accept → prepare → ready), availability controls, reviews, and AI-generated business insights.
- **Rider dashboard** — delivery task queue, status updates through the full delivery lifecycle, issue reporting, and earnings summaries.
- **Admin dashboard** — customer/restaurant/rider management, platform-wide order monitoring, coupon management, and review/complaint moderation.
- **AI agents** (see [`AGENTS.md`](./AGENTS.md)) — seven specialized agents, each with a structured output contract and a deterministic fallback, so the app is fully functional even without an OpenAI API key.
- **Strict order-status state machine**, server-side price/coupon recalculation, and role-based access control.

## 🧱 Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, Uvicorn, Pydantic |
| Templates | Jinja2 |
| Frontend | HTML5, Tailwind CSS, Vanilla JavaScript (ES modules), Fetch API |
| AI | OpenAI Python SDK (GPT-4.1-mini or compatible) |
| Data | JSON-file mock store (repository pattern, PostgreSQL-migration-ready) |
| Testing | Pytest |

## 📁 Project Structure

```text
foodflow/
├── app/
│   ├── main.py, config.py, dependencies.py
│   ├── models/        # Data-layer entities
│   ├── schemas/        # Request/response DTOs
│   ├── routes/         # FastAPI routers
│   ├── services/        # Business logic
│   ├── agents/         # AI agents + fallbacks
│   ├── data/           # JSON mock data
│   └── utils/           # Validation, pricing, order-status rules
├── templates/           # Jinja2 pages
├── static/              # CSS, JS, images
├── tests/                # Pytest suite
├── task.md               # Full product & technical specification
├── CLAUDE.md              # Guidance for AI coding agents working in this repo
├── AGENTS.md               # AI agent responsibilities & safety constraints
└── requirements.txt
```

## 🚀 Getting Started

### Prerequisites
- Python 3.11+

### Setup

```bash
git clone https://github.com/MaryamMumtaz-piaic/foodflow.git
cd foodflow
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # optionally add your OPENAI_API_KEY
uvicorn app.main:app --reload
```

Then open **http://127.0.0.1:8000** in your browser.

> **No OpenAI API key? No problem.** Every AI agent has a deterministic rule-based fallback, so the full app — search, recommendations, dashboards, and all — works out of the box.

### Running Tests

```bash
pytest tests/ -q
```

## 🧠 AI Agent Architecture

FoodFlow splits AI functionality into seven specialized agents rather than one large prompt — see [`AGENTS.md`](./AGENTS.md) for the full breakdown of each agent's responsibilities, output contracts, and safety constraints (e.g. the support agent never fabricates a completed refund, and the risk agent only flags — it never auto-punishes).

## 🔒 Security Notes

- API keys live in environment variables and are never exposed to the frontend.
- All prices and coupon eligibility are recalculated/re-validated server-side — the frontend is never trusted.
- Passwords are hashed, never stored in plaintext; LocalStorage never holds passwords, tokens, or payment data.
- Order-status transitions are validated against a strict state machine on the backend.

## 🗺️ Roadmap

See `task.md` §24 for planned future enhancements, including PostgreSQL migration, real authentication, WebSocket live tracking, Stripe integration, and map/geolocation support.

## 📄 License

Released under the [MIT License](./LICENSE).

## 👩‍💻 Author

**Maryam Mumtaz** — Full Stack Developer & AI Agent Engineer
[Portfolio](https://maryam-piaic.vercel.app) · [LinkedIn](https://www.linkedin.com/in/maryam-mumtaz-315358361/) · [GitHub](https://github.com/MaryamMumtaz-piaic)
