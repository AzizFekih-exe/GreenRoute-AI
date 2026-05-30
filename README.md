# GreenRoute AI

**An Explainable, Human-in-the-Loop System for Green Solvent Substitution and Synthesis Optimisation**

GreenRoute AI is an intelligent assistant built for the **InNOChem Hackathon** by **Team InNOChem** (4 participants). The system addresses two core thematic axes:
1. **Substitution of toxic and polluting solvents**: Replacing harmful chemicals (e.g., DMF, dichloromethane, hexane) with green, bio-based, or less toxic alternatives.
2. **Optimisation of synthesis routes**: Minimising waste (E-factor), maximising atom economy, and reducing energy consumption/reaction steps.

---

## 🏗️ Technical Architecture

The application is structured into three main layers:

```
[Web UI (React + Vite)] 
       │
       ▼ (REST API)
[Flask API (Port 5000)]
       │
       ▼
[Orchestrator (Python)]
       ├── Solvent DB (SQLite + FAISS for similarity)
       ├── ML Model (Random Forest Yield Prediction + QSAR Toxicity)
       ├── Green Metrics Calculator (E-factor, Atom Economy, Green Solvent Score)
       ├── Explanation Engine (Template-based XAI)
       └── Validation State Machine (Strict Human-in-the-Loop)
```

### Key Technical Specs:
- **Scientific Transparency (XAI)**: Explicit justification text for every solvent/route recommendation and uncertainty quantification (confidence intervals) for predictions.
- **Human-in-the-Loop (HITL)**: All proposed recommendations require an explicit validation ("Approve for experiment") before being considered final. This state machine is hard-coded in the backend.
- **Real Engineering**: Built using Python (Flask, Pandas, RDKit, scikit-learn, FAISS) and Dockerised for local reproducibility. No code/simple wrapper bypasses.

---

## 👥 Task Division & Workspaces

The repository is divided into specific folders dedicated to each team member's role:

| Workspace / Role | Member | Responsibility | Key Deliverables |
| :--- | :--- | :--- | :--- |
| [p1_chemistry_data/](file:///c:/Users/LENOVO/GreenRoute-AI/p1_chemistry_data) | **P1 - Chemistry Lead** | Curate greenness/toxicity data, define scoring equations, write scientific notes. | Solvent dataset, metrics formulas, 5-reaction validation set. |
| [p2_ai_ml/](file:///c:/Users/LENOVO/GreenRoute-AI/p2_ai_ml) | **P2 - AI/ML Engineer** | Build yield prediction, uncertainty models, QSAR toxicity classifiers, and FAISS indexing. | Random Forest models, Monte Carlo dropout, Morgan fingerprint FAISS search. |
| [backend/](file:///c:/Users/LENOVO/GreenRoute-AI/backend) | **P3 - Backend (You)** | Develop API, orchestrator logic, HITL state machine, and Docker config. | Flask REST API, orchestrator integration, docker-compose configuration. |
| [frontend/](file:///c:/Users/LENOVO/GreenRoute-AI/frontend) | **P4 - Frontend Lead** | Build React UI web interface, parameter overrides, visual explanations. | React/Vite dashboard, coordination of the demo. |

---

## 🚀 How to Run

### Option 1: Docker (Recommended)
You can start the entire stack (Flask backend and React frontend) using Docker Compose:

```bash
docker-compose up --build
```
- **React Frontend**: `http://localhost:8501`
- **Flask API**: `http://localhost:5000`

### Option 2: Local Installation
If you prefer to run the components manually:

1. **Start Flask API Backend**:
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r ../requirements.txt
   python app.py
   ```

2. **Start React Frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Access the dashboard at `http://localhost:8501`.

---

## 📂 Repository Structure

- `p1_chemistry_data/`: Curation workspace for P1's datasets, formulas, and scientific documentation.
- `p2_ai_ml/`: Workspace for P2's model training files, descriptors generation, and notebooks.
- `backend/`: Workspace for P3's Flask API endpoints, database setup, orchestrator, and metrics code.
- `frontend/`: Workspace for P4's React/Vite web application client.
- `docker-compose.yml`: Services container coordination.
- `requirements.txt`: Project-wide Python dependencies.
