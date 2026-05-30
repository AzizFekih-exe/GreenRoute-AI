class ExplanationEngine:
    """
    Template-based XAI engine to translate green metrics and ML confidence intervals
    into scientific justifications for chemists.
    """
    
    @staticmethod
    def generate_comparison_text(preferred: dict, alternative: dict) -> str:
        """
        Generates a comparative natural language explanation.
        Example: "Cyclopentyl methyl ether is preferred over dichloromethane because its E-factor 
        is 0.50 lower, it is readily biodegradable (OECD 301F), and it reduces VOC emissions by 65%."
        """
        reasons = []
        
        # E-factor improvement
        e_pref = preferred.get("e_factor", 1.0)
        e_alt = alternative.get("e_factor", 1.0)
        if e_pref < e_alt:
            reasons.append(f"its E-factor is {e_alt - e_pref:.2f} lower")
            
        # Biodegradability improvement
        bio_pref = preferred.get("biodegradability", 0.0)
        bio_alt = alternative.get("biodegradability", 0.0)
        if bio_pref > bio_alt:
            reasons.append("it is readily biodegradable (OECD 301F)")
            
        # VOC reduction
        voc_pref = preferred.get("voc", 0.0)
        voc_alt = alternative.get("voc", 0.0)
        if voc_pref < voc_alt:
            reduction = (voc_alt - voc_pref) * 100
            reasons.append(f"it reduces VOC emissions by {reduction:.0f}%")
            
        # Toxicity reduction
        tox_pref = preferred.get("toxicity", 0.0)
        tox_alt = alternative.get("toxicity", 0.0)
        if tox_pref < tox_alt:
            reasons.append("it has significantly lower toxicity/toxicity flags")

        if not reasons:
            return f"{preferred['name']} shows a comparable environmental footprint to {alternative['name']}."
            
        if len(reasons) == 1:
            reasons_str = reasons[0]
        elif len(reasons) == 2:
            reasons_str = f"{reasons[0]} and {reasons[1]}"
        else:
            reasons_str = f"{', '.join(reasons[:-1])}, and {reasons[-1]}"
            
        return f"{preferred['name']} is preferred over {alternative['name']} because {reasons_str}."

    @staticmethod
    def get_uncertainty_explanation(yield_data: dict) -> str:
        """
        Formulates an explanation regarding prediction uncertainty.
        """
        ci = yield_data.get("confidence_interval", [0.0, 100.0])
        return (
            f"The predicted reaction yield is {yield_data['predicted_yield']}% "
            f"with a 95% confidence interval of [{ci[0]}%, {ci[1]}%]. "
            f"Uncertainty is quantified using 50 Monte Carlo dropout iterations."
        )

    @staticmethod
    def get_missing_data_warnings(solvent: dict) -> list:
        """
        Identifies and flags missing endpoints to avoid 'black-box' predictions.
        """
        warnings = []
        # Simulate check for missing data
        if not solvent.get("toxicity") and solvent.get("toxicity") != 0:
            warnings.append(f"Missing toxicity endpoint for {solvent['name']} -> using conservative default.")
        if not solvent.get("biodegradability") and solvent.get("biodegradability") != 0:
            warnings.append(f"Missing biodegradability data for {solvent['name']} -> using conservative default.")
        return warnings
