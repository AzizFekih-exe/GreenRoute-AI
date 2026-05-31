import numpy as np
import os

try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors
except ImportError:
    Chem = None
    Descriptors = None

try:
    import joblib
except ImportError:
    joblib = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.environ.get("MODEL_DIR", os.path.join(BASE_DIR, "models"))
YIELD_MODEL_PATH = os.path.join(MODEL_DIR, "yield_predictor.joblib")
QSAR_MODEL_PATH = os.path.join(MODEL_DIR, "toxicity_classifier.joblib")

class YieldPredictor:
    def __init__(self):
        self.model = None
        if joblib:
            try:
                if os.path.exists(YIELD_MODEL_PATH):
                    self.model = joblib.load(YIELD_MODEL_PATH)
            except Exception:
                pass

    def predict_yield(self, target_smiles: str, solvent_smiles: str) -> dict:
        """
        Predicts yield for the synthesis of the target molecule using a specific solvent.
        Includes a simulated Monte Carlo Dropout uncertainty estimation using 50 forward passes.
        """
        # Base yield prediction logic based on mock structural features or real ML model
        base_yield = 75.0
        
        # Option B: Run real Random Forest model if loaded
        if self.model:
            try:
                if Chem and Descriptors:
                    mol_target = Chem.MolFromSmiles(target_smiles)
                    mol_solvent = Chem.MolFromSmiles(solvent_smiles)
                    if mol_target and mol_solvent:
                        # Extract basic sample features (P2 can adjust these headers later)
                        features = np.array([[
                            Descriptors.MolWt(mol_target),
                            Descriptors.MolLogP(mol_target),
                            Descriptors.MolWt(mol_solvent),
                            Descriptors.MolLogP(mol_solvent)
                        ]])
                        base_yield = float(self.model.predict(features)[0])
            except Exception:
                pass
        else:
            if Chem:
                mol_target = Chem.MolFromSmiles(target_smiles)
                mol_solvent = Chem.MolFromSmiles(solvent_smiles)
                if mol_target and mol_solvent:
                    # Add deterministic variation based on molecular weights
                    mw_target = Descriptors.MolWt(mol_target)
                    mw_solvent = Descriptors.MolWt(mol_solvent)
                    base_yield = 60.0 + (mw_target + mw_solvent) % 30.0
        
        # Simulate 50 Monte Carlo Dropout forward passes by adding normal noise
        # This is a placeholder for the actual MC Dropout implementation
        np.random.seed(42)  # Seed for reproducibility
        forward_passes = np.random.normal(loc=base_yield, scale=3.5, size=50)
        forward_passes = np.clip(forward_passes, 0.0, 100.0)
        
        mean_yield = float(np.mean(forward_passes))
        std_yield = float(np.std(forward_passes))
        
        # 95% confidence interval (approx. 1.96 standard deviations)
        ci_lower = max(0.0, mean_yield - 1.96 * std_yield)
        ci_upper = min(100.0, mean_yield + 1.96 * std_yield)
        
        return {
            "predicted_yield": round(mean_yield, 2),
            "uncertainty_std": round(std_yield, 2),
            "confidence_interval": [round(ci_lower, 2), round(ci_upper, 2)]
        }


class QSARClassifier:
    def __init__(self):
        self.model = None
        if joblib:
            try:
                if os.path.exists(QSAR_MODEL_PATH):
                    self.model = joblib.load(QSAR_MODEL_PATH)
            except Exception:
                pass

    def predict_toxicity_flag(self, smiles: str) -> dict:
        """
        Predicts if a solvent poses a high toxicity risk.
        """
        # Option B: Run real trained classifier if loaded
        if self.model:
            try:
                if Chem and Descriptors:
                    mol = Chem.MolFromSmiles(smiles)
                    if mol:
                        # Extract basic descriptors (P2 can adjust these headers later)
                        features = np.array([[
                            Descriptors.MolWt(mol),
                            Descriptors.MolLogP(mol),
                            Descriptors.TPSA(mol)
                        ]])
                        prob = float(self.model.predict_proba(features)[0][1])
                        return {
                            "toxicity_probability": round(prob, 2),
                            "is_toxic_flag": prob > 0.5
                        }
            except Exception:
                pass
                
        # Basic heuristic model fallback
        prob = 0.15
        if "N" in smiles or "Cl" in smiles:
            prob = 0.82
        elif "C" in smiles and len(smiles) > 5:
            # e.g., Hexane, Toluene
            prob = 0.65
            
        return {
            "toxicity_probability": round(prob, 2),
            "is_toxic_flag": prob > 0.5
        }
