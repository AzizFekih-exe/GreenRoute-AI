import uuid
import requests
from database import SolventDatabase
from models import YieldPredictor, QSARClassifier
from metrics import calculate_green_solvent_score
from explanation import ExplanationEngine

try:
    from rdkit import Chem
except ImportError:
    Chem = None

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

    def _is_valid_smiles(self, smiles: str) -> bool:
        if not smiles:
            return False
        if Chem is None:
            return len(smiles) > 0
        try:
            mol = Chem.MolFromSmiles(smiles)
            return mol is not None
        except Exception:
            return False

    def _is_organic_molecule(self, smiles: str) -> bool:
        """Reject atoms/ions/noble gases — require at least one carbon atom."""
        if Chem is None:
            return True  # Can't check, allow through
        try:
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return False
            carbon_count = sum(1 for atom in mol.GetAtoms() if atom.GetAtomicNum() == 6)
            return carbon_count > 0
        except Exception:
            return False

    def _get_molecule_name_from_smiles(self, smiles: str) -> str:
        """Try to get a human-readable name for a SMILES from PubChem."""
        try:
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{requests.utils.quote(smiles)}/property/IUPACName/JSON"
            response = requests.get(url, timeout=6)
            if response.status_code == 200:
                data = response.json()
                props = data.get("PropertyTable", {}).get("Properties", [])
                if props and props[0].get("IUPACName"):
                    return props[0]["IUPACName"]
        except Exception:
            pass
        return smiles  # fallback to raw SMILES

    def _resolve_name_to_smiles(self, name: str) -> str:
        name_clean = name.strip()
        if not name_clean:
            return None
        
        # Check if the name matches any of our database solvents' names exactly as a shortcut
        solvents = self.db.get_all_solvents()
        for s in solvents:
            if s["name"].lower() == name_clean.lower():
                return s["smiles"]
        
        # Query PubChem PUG REST API
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{requests.utils.quote(name_clean)}/property/CanonicalSMILES/JSON"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                properties = data.get("PropertyTable", {}).get("Properties", [])
                if properties:
                    prop = properties[0]
                    for key, val in prop.items():
                        if "SMILES" in key:
                            return val
        except Exception:
            pass
        return None

    def generate_recommendations(self, target_smiles: str, weights: dict, overrides: dict = None, user_id: int = None) -> dict:
        """
        1. Retrieves all solvents from database.
        2. Applies chemical parameter overrides (e.g. force solvent, exclude highly toxic).
        3. Computes green metrics and predicted yield/uncertainties.
        4. Scores candidate solvents.
        5. Returns the top 3 with explanation texts and creates a validation session.
        """
        if overrides is None:
            overrides = {}
            
        input_target = target_smiles.strip() if target_smiles else ""
        original_input = input_target  # Keep original user text for display/agent context
        resolved_smiles = None

        if self._is_valid_smiles(input_target):
            resolved_smiles = input_target
        else:
            resolved_smiles = self._resolve_name_to_smiles(input_target)
            if not resolved_smiles or not self._is_valid_smiles(resolved_smiles):
                raise ValueError(
                    f"Molecule '{input_target}' is neither a valid SMILES string nor a recognized compound name."
                )

        # Reject non-organic inputs (noble gases, metal atoms, ions, etc.)
        if not self._is_organic_molecule(resolved_smiles):
            raise ValueError(
                f"'{input_target}' ({resolved_smiles}) is not a valid organic molecule. "
                f"Please enter a carbon-containing compound (e.g. Glucose, Aspirin, or a SMILES like CC(=O)O)."
            )

        # Resolve a human-readable name for the target to enrich AI explanations
        target_display_name = original_input if not self._is_valid_smiles(original_input) else self._get_molecule_name_from_smiles(resolved_smiles)

        target_smiles = resolved_smiles
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
                
            # Parameter Override: Exclude halogenated solvents if requested
            if overrides.get("exclude_halogenated") and s.get("halogenated"):
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
            
            # Calculate simulated Energy Demand in kJ (heating 10 kg of solvent from 25°C to reaction_temperature)
            reaction_temp = float(overrides.get("reaction_temperature", 80.0))
            delta_t = max(0.0, reaction_temp - 25.0)
            solvent_heat_capacity = s.get("heat_capacity", 2.0)
            energy_demand = round(10.0 * solvent_heat_capacity * delta_t, 1)
            
            # Boiling point high-pressure warning
            boiling_point = s.get("boiling_point", 100.0)
            if reaction_temp > boiling_point:
                warnings.append(f"Operating temperature ({reaction_temp}°C) exceeds solvent boiling point ({boiling_point}°C). Reaction requires a sealed, high-pressure autoclave.")
            
            # Calculate Atom Economy
            atom_economy = 85.0
            if Chem:
                mol_target = Chem.MolFromSmiles(target_smiles)
                if mol_target:
                    from rdkit.Chem import Descriptors
                    from metrics import calculate_atom_economy
                    target_mw = Descriptors.MolWt(mol_target)
                    # Simulated reactants for the solvent's typical route: target + leaving group + solvent interaction factor
                    reactants_mws = [target_mw + 30.0 + (s.get('toxicity', 0.5) * 20.0)]
                    try:
                        atom_economy = round(calculate_atom_economy(target_mw, reactants_mws), 1)
                    except Exception:
                        pass

            processed_candidates.append({
                "name": s["name"],
                "smiles": s["smiles"],
                "toxicity": s["toxicity"],
                "voc": s["voc"],
                "biodegradability": s["biodegradability"],
                "recyclability": s["recyclability"],
                "boiling_point": boiling_point,
                "heat_capacity": solvent_heat_capacity,
                "halogenated": s.get("halogenated", False),
                "energy_demand": energy_demand,
                "e_factor": e_factor,
                "atom_economy": atom_economy,
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
        
        # Parallel generation of agent explanations for the top 3 recommendations
        import concurrent.futures
        try:
            from src.ai_agents.agents import run_pipeline
            
            def fetch_agent_explanation(candidate, target_sm, target_name, ref_name):
                # Build a rich, data-grounded question so the agent gives a specific scientific answer
                q = (
                    f"Explain specifically and scientifically why {candidate['name']} "
                    f"(SMILES: {candidate['smiles']}) is a preferred green solvent over "
                    f"{ref_name} for reactions involving the target compound '{target_name}' "
                    f"(SMILES: {target_sm}). "
                    f"Use the following computed green chemistry data: "
                    f"Green Score={candidate['green_score']}, "
                    f"Toxicity index={candidate['toxicity']}, "
                    f"VOC index={candidate['voc']}, "
                    f"Biodegradability={candidate['biodegradability']}, "
                    f"Recyclability={candidate['recyclability']}, "
                    f"E-factor={candidate['e_factor']}, "
                    f"Predicted Reaction Yield={candidate['yield_info']['predicted_yield']}%, "
                    f"Boiling Point={candidate['boiling_point']}C, "
                    f"Energy Demand={candidate['energy_demand']} kJ. "
                    f"Reference solvent ({ref_name}) has Toxicity=0.8, Biodegradability=0.05, E-factor=8.5."
                )
                try:
                    ai_exp = run_pipeline(q)
                    if ai_exp:
                        return ai_exp
                except Exception as e:
                    print(f"Failed to generate AI agent explanation for {candidate['name']}: {e}")
                return candidate["explanation"] # Fallback

            ref_solvent_name = ref_solvent.get("name", "DCM")
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = {
                    executor.submit(fetch_agent_explanation, r, target_smiles, target_display_name, ref_solvent_name): r
                    for r in top_3
                }
                for future in concurrent.futures.as_completed(futures):
                    r = futures[future]
                    try:
                        ai_explanation = future.result()
                        if ai_explanation:
                            r["ai_explanation"] = ai_explanation
                    except Exception:
                        pass
        except Exception as e:
            print(f"Skipping AI agent explanation generation: {e}")
        
        # Initialize validation session for HITL tracking
        session_id = str(uuid.uuid4())
        self.db.save_session(session_id, target_smiles, weights, overrides, top_3, user_id)
        
        session = {
            "session_id": session_id,
            "target_smiles": target_smiles,
            "weights": weights,
            "overrides": overrides,
            "recommendations": top_3,
            "approved": False,
            "approved_solvent": None,
            "user_id": user_id
        }
        return session

    def approve_recommendation(self, session_id: str, solvent_name: str, user_id: int = None) -> bool:
        """
        Transitions the validation state of the recommendation to 'Approved' in SQLite database.
        """
        return self.db.approve_session(session_id, solvent_name, user_id)

    def get_session_state(self, session_id: str) -> dict:
        state = self.db.get_session(session_id)
        return state if state else {}
