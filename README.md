# GreenRoute AI

GreenRoute AI is a Flask + React prototype for explainable green chemistry decision support. It covers two InNOChem axes:

1. Toxic solvent substitution: rank greener solvent alternatives before experimentation.
2. Synthesis route optimisation: compare route options using atom economy, E-factor, and step count.

The system is intentionally human-in-the-loop: it recommends and explains, but a chemist must explicitly approve an option before it is logged as a validated experiment.

## Features

- Name or SMILES search for target molecules, with PubChem name-to-SMILES resolution.
- RDKit validation to reject invalid or non-organic molecule inputs.
- Green solvent ranking using toxicity, VOC, biodegradability, recyclability, E-factor, predicted yield, atom economy, and energy demand.
- Synthesis route ranking with a visible weighted score:
  - 45% atom economy
  - 40% E-factor reduction
  - 15% step reduction
- Template-based XAI explanations, uncertainty intervals, warnings, and source traceability.
- Authentication, token-based sessions, approval workflow, and experiment history.

## Team Roles

| Member | Role | Main Responsibility |
| --- | --- | --- |
| Jesser Slimi| Chemistry / Data Lead | Green chemistry criteria, solvent and route metrics, scientific justification. |
| Ahmed Benmim | AI / ML Lead | Molecular validation, prediction logic, uncertainty handling, and chemoinformatics support. |
| Aziz Fekih | Backend / Integration Lead | Flask API, database, authentication, orchestration, and Docker setup. |
| Emen Slimi | Frontend / UX Lead | React interface, workflow design, result cards, route ranking display, and HITL UX. |

## Architecture

```text
React + Vite UI (localhost:8501)
    |
    | REST/JSON + Bearer token
    v
Flask API (localhost:5000)
    |
    v
Orchestrator
    |-- Molecule validation and PubChem resolution
    |-- Green solvent scoring
    |-- Yield and uncertainty estimation
    |-- Route scoring
    |-- XAI text generation
    v
SQLite database
    |-- users and tokens
    |-- solvent data
    |-- synthesis routes
    |-- sessions
    |-- experiment history
```

## Security Notes

- Login and registration use controlled React inputs.
- Passwords are sent only to the backend, never stored in React state beyond form submission.
- Backend passwords are salted and hashed with PBKDF2-HMAC-SHA256.
- Password hash comparison uses constant-time comparison.
- Tokens are random, expire after 7 days, and are required for protected API routes.
- This hackathon prototype uses permissive CORS for local demo convenience; tighten CORS and use HTTPS before production.

## Run Locally

### Backend

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python backend/app.py
```

Backend URL: `http://localhost:5000`

### Frontend

```bash
cd frontend
npm install
npm run dev -- --port 8501
```

Frontend URL: `http://localhost:8501`

### One-Click Windows Launcher

```bat
run_app.bat
```

## Docker

```bash
docker compose up --build
```

Services:

- Frontend: `http://localhost:8501`
- Backend: `http://localhost:5000`

The SQLite database is generated automatically. Docker stores it at `/app/data/solvents.db`.

## API Surface

- `POST /api/auth/register`: create a user and return a token.
- `POST /api/auth/login`: authenticate and return a token.
- `POST /api/auth/logout`: invalidate the current token.
- `GET /api/auth/me`: return the authenticated user.
- `POST /api/recommend`: generate solvent recommendations.
- `POST /api/routes`: return ranked synthesis routes.
- `POST /api/validate`: approve one recommendation.
- `POST /api/v1/experiments`: log an approved experiment.
- `GET /api/v1/experiments/history`: retrieve experiment history.
- `GET /health`: backend health check.

## Repository Layout

```text
backend/              Flask API, database, scoring, models, XAI logic
frontend/             React/Vite user interface
src/ai_agents/        Optional AI deep-dive helpers
src/tox21/            Tox21 compound metadata used for traceability
src/tox21_loader.py   Tox21 metadata loader
docker-compose.yml    Local full-stack orchestration
requirements.txt      Python runtime dependencies
run_app.bat           Windows local launcher
```

## Scientific Methods

Solvent score:

```text
score = w_tox * (1 - toxicity)
      + w_voc * (1 - VOC)
      + w_bio * biodegradability
      + w_rec * recyclability
```

Route score:

```text
score = 0.45 * atom_economy_normalized
      + 0.40 * e_factor_reduction_normalized
      + 0.15 * step_reduction_normalized
```

Uncertainty:

```text
Yield confidence intervals are estimated from 50 Monte Carlo-style forward passes.
```
