# Crop-Watch AI

NASA Space Apps Challenge 2026 — **Field Shift** challenge.

Crop-Watch AI helps farmers compare their current multi-season crop rotation with at least two
alternatives, showing climate risks and tradeoffs (water, soil health, income, resilience) together
with the evidence, assumptions and data gaps behind each result. See [AGENTS.md](AGENTS.md) for
product context and [docs/architecture.md](docs/architecture.md) for the code layout.

## Layout

```
backend/    FastAPI app (uv-managed Python 3.12)
frontend/   React + TypeScript (Vite)
docs/       Architecture notes and research
```

## Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs. Run tests with `uv run pytest`.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

The dev server (http://localhost:5173) proxies `/api` to the backend on port 8000.

## Status

Prototype. Wheat, rice and maize have **provisional** temperature limits from the team research brief
(see `docs/research/research-brief-thresholds.md`); growth-stage lengths come from FAO-56 Table 11 (scaled to each season).
Mung bean and berseem limits come from
Feedipedia/FAO and peer-reviewed studies (`docs/research/phase2-sources.md`). Water use follows FAO-56.
Other thresholds are still empty, and the engine reports them as evidence gaps rather than guessing. SoilGrids topsoil data sets rice percolation and is returned with each comparison. Saved NASA POWER and SoilGrids responses for
Multan, Bahawalpur, Larkana and Hyderabad (`backend/app/data/sample/`) are used if NASA is unreachable.
Scoring weights in `backend/app/domain/scoring_config.py` are provisional engineering choices.
