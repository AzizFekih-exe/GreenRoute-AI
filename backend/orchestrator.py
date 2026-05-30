import uuid
from database import SolventDatabase
from models import YieldPredictor, QSARClassifier
from metrics import calculate_green_solvent_score
from explanation import ExplanationEngine

class Orchestrator:
    """
    Main Orchestrator representing the integration layer.
    Coordinates the Solvent DB search, ML predictions, and provides the Human-in-the-Loop
    state machine for chemist validation.
    """
    def __init__(self, db_path="solvents.db"):
        self.db = SolventDatabase(db_path)
        self.yield_predictor = YieldPredictor()
        self.qsar_classifier = QSARClassifier()

    def generate_recommendations(self, target_smiles: str, weights: dict, overrides: dict = None) -> dict:
        """
        1. Retrieves all solvents from database.
        2. Applies chemical parameter overrides (e.g. force solvent, exclude highly toxic).
        3. Computes green metrics and predicted yield/uncertainties.
        4. Scores candidate solvents.
        5. Returns the top 3 with explanation texts and creates a validation session.
        """
        if overrides is None:
            overrides = {}
            
        candidates = self.db.get_all_solvents()
        
        # Determine reference solvent for comparative XAI (e.g. Dichloromethane or Hexane)
        ref_solvent = None
        for c in candidates:
            if c["name"].lower() == "dichloromethane":
                ref_solvent = c
                break
        if not ref_solvent:
            ref_solvent = candidates[0] if candidates else {"name": "DCM", "toxicity": 0.8, "voc": 0.9, "biodegradability": 0.1, "recyclability": 0.3}

        # Mock standard E-factor for reference
        ref_solvent_copy = ref_solvent.copy()
        ref_solvent_copy["e_factor"] = 8.5
        
        processed_candidates = []
        
        for s in candidates:
            # Skip the reference toxic solvent from recommendations
            if s["name"] == ref_solvent.get("name"):
                continue
                
            # Parameter Override: Exclude highly toxic solvents if requested
            if overrides.get("exclude_toxic") and s["toxicity"] > 0.5:
                continue
                
            # Parameter Override: Force specific solvent selection
            if overrides.get("force_solvent") and s["name"].lower() != overrides["force_solvent"].lower():
                continue
                
            # Compute simulated E-factor based on toxicity metrics
            e_factor = 6.0
            if s["toxicity"] < 0.2:
                e_factor = 2.0
            elif s["toxicity"] > 0.6:
                e_factor = 7.5
                
            # Calculate overall green solvent score
            score = calculate_green_solvent_score(
                norm_toxicity=s["toxicity"],
                norm_voc=s["voc"],
                biodegradability=s["biodegradability"],
                recyclability=s["recyclability"],
                weights=weights
            )
            
            # Predict yield and Monte Carlo uncertainty
            yield_data = self.yield_predictor.predict_yield(target_smiles, s["smiles"])
            
            s_metric = s.copy()
            s_metric["e_factor"] = e_factor
            
            # Generate justifications
            explanation = ExplanationEngine.generate_comparison_text(s_metric, ref_solvent_copy)
            yield_explanation = ExplanationEngine.get_uncertainty_explanation(yield_data)
            warnings = ExplanationEngine.get_missing_data_warnings(s)
            
            processed_candidates.append({
                "name": s["name"],
                "smiles": s["smiles"],
                "toxicity": s["toxicity"],
                "voc": s["voc"],
                "biodegradability": s["biodegradability"],
                "recyclability": s["recyclability"],
                "e_factor": e_factor,
                "green_score": round(score, 3),
                "yield_info": yield_data,
                "explanation": explanation,
                "yield_explanation": yield_explanation,
                "warnings": warnings,
                "data_source": s["data_source"]
            })
            
        # Sort candidates by their overall Green Solvent Score descending
        processed_candidates.sort(key=lambda x: x["green_score"], reverse=True)
        top_3 = processed_candidates[:3]
        
        # Initialize validation session for HITL tracking
        session_id = str(uuid.uuid4())
        self.db.save_session(session_id, target_smiles, weights, overrides, top_3)
        
        session = {
            "session_id": session_id,
            "target_smiles": target_smiles,
            "weights": weights,
            "overrides": overrides,
            "recommendations": top_3,
            "approved": False,
            "approved_solvent": None
        }
        return session

    def approve_recommendation(self, session_id: str, solvent_name: str) -> bool:
        """
        Transitions the validation state of the recommendation to 'Approved' in SQLite database.
        """
        return self.db.approve_session(session_id, solvent_name)

    def get_session_state(self, session_id: str) -> dict:
        state = self.db.get_session(session_id)
        return state if state else {}
