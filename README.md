# Medellín Places — AI-Powered Place Recommendation

> **Live Demo:** [medellin-app-mauve.vercel.app](https://medellin-app-mauve.vercel.app)

![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?style=flat-square&logo=fastapi)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react)
![Claude](https://img.shields.io/badge/Claude-Sonnet-orange?style=flat-square)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat-square&logo=docker)
![License](https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square)

A conversational AI assistant that recommends places in Medellín based on your preferences, real-time weather, and open civic data. Built with a **multi-agent architecture** using Claude's tool use — not a simple search filter.

---

## How It Works

You describe what you're looking for in natural language. Three agents collaborate to find the best options:

```
User message
      │
      ▼
 Profiler Agent (Claude)
 Extracts: activity type, time of day,
 group type, budget preference
      │
      ▼ (profile complete)
      ├── Climate Agent → Open-Meteo API (real-time weather)
      │
      └── Orchestrator Agent (Claude + tool_use)
               │
               ├── get_clima()        → current weather + impact
               ├── buscar_lugares()   → scored place candidates
               └── servicios_cercanos() → nearby services
               │
               ▼
          Top 3 recommendations
          with reasoning, score,
          metro accessibility,
          and nearby services
                │
                ▼
         Interactive map (Leaflet)
         + chat response
```

---

## Agent Architecture

### Profiler Agent
Conducts a short conversational exchange to extract a structured user profile: activity type, moment of day, group type, and budget. Handles ambiguous or incomplete inputs across multiple turns.

### Climate Agent
Fetches real-time weather from Open-Meteo (no API key required): temperature, precipitation, humidity, and WMO weather code. Translates conditions into a recommendation impact signal (`sunny`, `light_rain`, `heavy_rain`) that filters covered vs. outdoor venues.

### Orchestrator Agent
Uses Claude's native tool use to call three tools in sequence, reason about the results, and return a structured JSON response with ranked recommendations, discard reasoning, and justifications per place.

---

## Data Sources

| Source | Data |
|---|---|
| **OpenStreetMap** | 85+ curated places across Medellín (parks, gastronomy, culture, entertainment) |
| **datos.gov.co** (pb3w-3vmc) | Business density per commune — used as activity proxy score |
| **Open-Meteo** | Real-time weather (no API key) |
| **Custom curation** | 15+ hand-scored anchor places with metadata |

### Scoring System

Each place receives a dynamic score combining:
- `score_base` — curated quality score
- `bonus_metro` — accessibility bonus by distance to metro station (Medellín Metro)
- `hora_pico_factor` — peak hour penalty (7–9am, 5–7pm)
- `actividad_empresarial` — commune business density from open civic data
- Climate filter — outdoor places penalized under rain conditions

---

## Stack

**Backend:** `Python` · `FastAPI` · `Claude Sonnet (tool_use)` · `httpx` · `Open-Meteo`

**Frontend:** `React 18` · `Vite` · `Tailwind CSS` · `Leaflet` · `react-leaflet`

**Data:** `OpenStreetMap` · `datos.gov.co` · `Open-Meteo`

**Infrastructure:** `Docker` · `docker-compose` · `Vercel`

---

## Quick Start

```bash
git clone https://github.com/agarcia1607/medellin-app
cd medellin-app
```

Configure backend `.env`:
```bash
ANTHROPIC_API_KEY=sk-ant-...
FRONTEND_URL=http://localhost:5173
```

Run with Docker:
```bash
docker-compose up
```

Or manually:
```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --port 8000

# Frontend
cd frontend
npm install && npm run dev
```

---

## API

### `POST /chat`
Profiling turn — extracts user preferences from natural language.

```json
{
  "mensaje": "I want to go out with my family this afternoon",
  "historial": [],
  "session_id": null
}
```

### `POST /recomendar`
Orchestrator turn — returns ranked recommendations.

```json
{
  "perfil": {
    "tipo": "naturaleza",
    "momento": "tarde",
    "grupo": "familia",
    "precio": "bajo"
  }
}
```

Response:
```json
{
  "razonamiento": "Given afternoon timing and family group...",
  "clima": { "descripcion": "Partly cloudy", "impacto": "nublado" },
  "recomendaciones": [
    {
      "lugar": "Parque de los Deseos",
      "score": 8.9,
      "motivo": "Interactive outdoor park near metro...",
      "metro": "Universidad — 315m",
      "coordenadas": { "lat": 6.2711, "lng": -75.5635 }
    }
  ]
}
```

---

## Project Structure

```
medellin-app/
├── backend/
│   ├── main.py           # FastAPI app + endpoints
│   ├── agents.py         # Profiler + Orchestrator (Claude)
│   ├── tools.py          # get_clima, buscar_lugares, servicios_cercanos
│   ├── analytics.py      # Session tracking
│   ├── data/
│   │   ├── places.json         # Curated places
│   │   ├── places_osm.json     # OpenStreetMap places
│   │   └── comunas_empresas.json  # Civic data (datos.gov.co)
│   └── scripts/
│       └── cargar_datos.py     # Data ingestion from datos.gov.co
├── frontend/
│   └── src/
│       ├── App.jsx
│       └── components/
│           ├── ChatUI.jsx
│           ├── MapaMapbox.jsx
│           └── AgentesVisibles.jsx  # Live agent status display
└── docker-compose.yml
```

---

## Deployment

| Service | Platform | URL |
|---|---|---|
| Frontend | Vercel | [medellin-app-mauve.vercel.app](https://medellin-app-mauve.vercel.app) |

---

## Author

**Andrés García** · Computer Scientist · Universidad Nacional de Colombia  
[GitHub](https://github.com/agarcia1607) · [LinkedIn](https://www.linkedin.com/in/andrés-felipe-garcía-orrego-17965b218)

## License

MIT
