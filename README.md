# Heritage Shops — Inventory Forecasting System
## Phase 1 + 2 — Full Build

### Quick Start (local)
```bash
pip install -r requirements.txt
streamlit run app.py
```

### Pages
| Page | Purpose |
|------|---------|
| 📤 Data Hub | Upload Sales History, Cruise Schedule, Weather, Inventory |
| 📊 Dashboard | KPIs, revenue charts, velocity distribution |
| 🔮 Forecast & Reorder | Smart reorder list with exclusions + seasonal/cruise model |
| 🤖 QA Agent Chat | Chat with the agent to explain/flag/edit reorder logic |
| 📈 Analytics | Top performers, 12-month forecast, brand analysis |
| ⚙️ Settings | Add/remove exclusion rules and blocked item numbers |

### Smart Exclusions (always active)
- Dated items: calendars/planners with year < current year
- Service items: shipping charges, gift card activation, environmental charge
- Negative margin items
- Discontinued / clearance / out-of-print items
- Manually excluded keywords or item numbers

### Agent Commands
- `why is [item] excluded?`
- `why is [item] in the list?`
- `show urgent items`
- `top sellers`
- `what to order for cruise week`
- `exclude 'keyword'`
- `show exclusion rules`
