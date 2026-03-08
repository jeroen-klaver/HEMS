# HEMS Build Plan

Following the build order from CLAUDE.md — each layer is testable before the next.

---

## Phase 1: Backend — Integration Layer

- [x] Create full directory structure (empty placeholder files)
- [x] `backend/integrations/base.py` — abstract base + manifest types
- [x] `backend/integrations/registry.py` — plugin self-registration decorator
- [x] `backend/integrations/homewizard_p1.py` — HomeWizard P1 grid meter
- [x] `backend/integrations/homewizard_socket.py` — HomeWizard smart plug
- [x] `backend/integrations/shelly.py` — Shelly Gen1 + Gen2 smart plugs
- [x] `backend/integrations/enphase.py` — Enphase IQ Gateway solar
- [x] `backend/integrations/alfen_eve.py` — Alfen Eve EV charger (Modbus TCP)
- [x] `backend/integrations/weheat.py` — WeHeat heat pump (OAuth2 cloud)
- [x] Write standalone test scripts for each integration (tests/test_*.py)

## Phase 2: Backend — Models & Database

- [x] `backend/models/readings.py` — SQLModel DB models
- [x] `backend/models/schemas.py` — Pydantic API response schemas
- [x] `backend/database.py` — SQLite setup via SQLModel

## Phase 3: Backend — Core Runtime

- [x] `backend/state.py` — global in-memory state (current readings)
- [x] `backend/scheduler.py` — APScheduler polling + control loop (5s)
- [x] `backend/config.py` — Pydantic settings loader (reads config.yaml)

## Phase 4: Backend — Services

- [x] `backend/services/pricing.py` — ENTSO-E fetcher + daily cache
- [x] `backend/services/forecast.py` — Open-Meteo + pvlib PV forecast
- [x] `backend/services/charging_logic.py` — Solar surplus state machine
- [x] `backend/services/influx_export.py` — Optional InfluxDB writer
- [x] `backend/services/daily_summary.py` — Daily aggregation job

## Phase 5: Backend — API

- [x] `backend/api/routes_status.py` — GET /api/v1/status
- [x] `backend/api/routes_history.py` — GET /api/v1/history
- [x] `backend/api/routes_config.py` — CRUD /api/v1/config/integrations
- [x] `backend/api/routes_pricing.py` — GET /api/v1/pricing/today + tomorrow
- [x] `backend/api/routes_forecast.py` — GET /api/v1/forecast
- [x] `backend/api/websocket.py` — WS /ws/live (5s push)
- [x] `backend/main.py` — FastAPI app entrypoint, wire everything

## Phase 6: Docker / Infra

- [x] `backend/Dockerfile`
- [x] `frontend/Dockerfile` + `frontend/nginx.conf`
- [x] `docker-compose.yml`
- [x] `docker-compose.influxdb.yml` — optional InfluxDB overlay
- [x] `.env.example` + `config.yaml.example`
- [x] `backend/requirements.txt`

## Phase 7: Frontend — Hooks & Data

- [x] `frontend/` Vite + React + TypeScript + Tailwind scaffold (`package.json`)
- [x] `frontend/src/hooks/useLiveData.ts` — WebSocket hook
- [x] `frontend/src/hooks/useHistory.ts` — history fetch hook

## Phase 8: Frontend — Components

- [x] `frontend/src/components/EnergyFlow.tsx` — SVG animated flow diagram
- [x] `frontend/src/components/DeviceCard.tsx` — generic device card
- [x] `frontend/src/components/ChargingMode.tsx` — OFF/MIN/SOLAR/FAST selector
- [x] `frontend/src/components/PriceChart.tsx` — 24h price bar chart
- [x] `frontend/src/components/ForecastChart.tsx` — PV forecast chart
- [x] `frontend/src/components/IntegrationForm.tsx` — dynamic form renderer

## Phase 9: Frontend — Pages

- [x] `frontend/src/pages/Dashboard.tsx` — main energy flow view
- [x] `frontend/src/pages/Settings.tsx` — dynamic config UI
- [x] `frontend/src/pages/History.tsx` — historical charts
- [x] `frontend/src/pages/Pricing.tsx` — hourly prices + forecast
- [x] `frontend/src/App.tsx` — routing + layout

## Phase 10: Docs

- [x] `docs/integrations/ADDING_NEW_INTEGRATION.md`
- [x] `docs/configuration.md`
- [x] `README.md`
- [x] `LICENSE` (MIT)

---

## Phase 11: Multi-array Solar Configuration + GUI

### Achtergrond
Gebruiker heeft 2 solar arrays (Zuid-Oost 11 panelen, Zuid-West 8 panelen) met verschillende
hellingshoek en azimuth. Arrays worden opgeslagen in SQLite (net als integrations), zodat
de GUI ze kan beheren zonder config.yaml aan te raken.

### Backend

- [ ] `backend/models/readings.py` — `SolarArray` SQLModel tabel toevoegen
      (id, name, panel_count, wp_per_panel, tilt_degrees, azimuth_degrees, enabled)
- [ ] `backend/api/routes_solar.py` — CRUD: GET/POST `/api/v1/solar-arrays`,
      PUT/DELETE `/api/v1/solar-arrays/{id}`
- [ ] `backend/models/schemas.py` — `SolarArraySchema` + `SolarArrayCreateSchema` toevoegen
- [ ] `backend/services/forecast.py` — updaten: per uur de output van alle enabled arrays
      optellen; fallback op config.yaml `ForecastConfig` als er geen DB-arrays zijn
- [ ] `backend/api/routes_forecast.py` — `total_kwp` retourneren op basis van DB-arrays
- [ ] `backend/main.py` — `routes_solar` router registreren

### Frontend

- [ ] `frontend/src/types.ts` — `SolarArray` type toevoegen
- [ ] `frontend/src/pages/Settings.tsx` — "Solar Arrays" sectie toevoegen:
      lijst van arrays + add/edit/remove knoppen (inline form, geen modal nodig)

### Wat per array wordt opgeslagen
| Veld | Voorbeeld |
|---|---|
| Naam | "Zuid-Oost" |
| Aantal panelen | 11 |
| Wp per paneel | 400 |
| Hellingshoek | 35° |
| Azimuth | 135° (ZO), 225° (ZW), 180° = Zuid |
| Ingeschakeld | true/false |

*system_kwp per array = panel_count × wp_per_panel / 1000*

---

## Review

All 10 phases complete. Full HEMS codebase built from scratch.

### What was built

### Backend (Python 3.12 / FastAPI)

- Plugin registry with `@register` decorator — new integrations need zero core changes
- 6 integrations: Enphase IQ Gateway, HomeWizard P1, HomeWizard Socket, Shelly Gen1+2, Alfen Eve (Modbus TCP), WeHeat (OAuth2 cloud)
- APScheduler polling loop every 5s — all integrations polled concurrently; one failure never blocks others
- Solar surplus EV charging state machine with hysteresis (off/min/solar/fast modes)
- Smart plug surplus control (80%/30% thresholds)
- ENTSO-E day-ahead pricing with all-in markup calculation + per-day cache
- Open-Meteo + pvlib PV production forecast + per-day cache
- SQLite via SQLModel (readings, integrations, charging sessions, daily summaries)
- Optional InfluxDB v2 export (lazy-init, no-op if not configured)
- Full REST API: status, history, integrations CRUD, pricing, forecast, charging mode
- WebSocket `/ws/live` pushing full status JSON every 5s with multi-client support

### Frontend (React 18 / Vite / TypeScript / Tailwind / Recharts)

- WebSocket hook with exponential back-off reconnect
- Animated SVG energy flow diagram (6 nodes, arrow thickness scales with watts)
- DeviceCard with live status dot, power reading, today kWh, smart plug toggle
- ChargingMode selector (calls API on change)
- PriceChart with green/yellow/red colouring vs daily average
- ForecastChart (area chart, yellow gradient)
- IntegrationForm fully driven by backend manifest — no hardcoded fields
- Settings page: list + add (type picker → modal form) + edit + delete
- History page: range selector, one chart per device/field
- Pricing page: today + tomorrow + forecast combined

### Infra

- Multi-stage Dockerfiles for backend (python:3.12-slim) and frontend (node:20 → nginx:alpine)
- nginx reverse proxy for API + WebSocket with SPA fallback
- `HEMS_DATA_DIR` env var routes config.yaml and hems.db to Docker volume
- Optional InfluxDB overlay via `docker-compose.influxdb.yml`

### Known next steps / TODOs

- ~~Vehicle SoC API~~ → geïmplementeerd via volkswagen_weconnect.py
- `charge_by_time` enforcement in charging_logic.py is declared in config but not yet implemented
- Daily summary net cost calculation needs pricing data joined in
- Settings page does not yet expose global config (lat/lon, pricing, charging thresholds) — only integrations
- No authentication on the API (fine for LAN-only; add if exposing externally)
