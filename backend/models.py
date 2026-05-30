import numpy as np

try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors
except ImportError:
    Chem = None
    Descriptors = None

class YieldPredictor:
    def __init__(self):
        # In a real setup, Participant 2 will load the trained Random Forest model.
        pass

    def predict_yield(self, target_smiles: str, solvent_smiles: str) -> dict:
        """
        Predicts yield for the synthesis of the target molecule using a specific solvent.
        Includes a simulated Monte Carlo Dropout uncertainty estimation using 50 forward passes.
        """
        # Base yield prediction logic based on mock structural features
        base_yield = 75.0
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
        # In a real setup, Participant 2 will load a trained classifier here.
        pass

    def predict_toxicity_flag(self, smiles: str) -> dict:
        """
        Predicts if a solvent poses a high toxicity risk.
        """
        # Basic heuristic model
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
