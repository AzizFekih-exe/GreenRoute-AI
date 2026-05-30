def calculate_e_factor(total_waste_kg: float, product_kg: float) -> float:
    """
    Calculates the E-factor (Environmental Factor).
    Formula: E-factor = total waste (kg) / product (kg)
    """
    if product_kg <= 0:
        raise ValueError("Product mass must be greater than zero.")
    return total_waste_kg / product_kg


def calculate_atom_economy(product_mw: float, reactants_mws: list) -> float:
    """
    Calculates the Atom Economy percentage.
    Formula: Atom economy = (MW of desired product / sum of MW of all reactants) * 100%
    """
    total_reactants_mw = sum(reactants_mws)
    if total_reactants_mw <= 0:
        raise ValueError("Total molecular weight of reactants must be greater than zero.")
    return (product_mw / total_reactants_mw) * 100.0


def calculate_green_solvent_score(
    norm_toxicity: float,
    norm_voc: float,
    biodegradability: float,
    recyclability: float,
    weights: dict = None
) -> float:
    """
    Calculates the weighted Green Solvent Score.
    Default Formula:
      Green solvent score = 0.3 * (1 - normalised toxicity)
                          + 0.2 * (1 - normalised VOC)
                          + 0.3 * biodegradability
                          + 0.2 * recyclability
    
    Inputs are assumed to be normalized between 0.0 and 1.0.
    """
    if weights is None:
        weights = {
            "toxicity": 0.3,
            "voc": 0.2,
            "biodegradability": 0.3,
            "recyclability": 0.2
        }
    
    # Normalize weights to ensure they sum to 1.0 if they don't already
    total_weight = sum(weights.values())
    if total_weight <= 0:
        raise ValueError("Sum of weights must be greater than zero.")
    
    w_tox = weights.get("toxicity", 0.3) / total_weight
    w_voc = weights.get("voc", 0.2) / total_weight
    w_bio = weights.get("biodegradability", 0.3) / total_weight
    w_rec = weights.get("recyclability", 0.2) / total_weight

    score = (
        w_tox * (1.0 - norm_toxicity) +
        w_voc * (1.0 - norm_voc) +
        w_bio * biodegradability +
        w_rec * recyclability
    )
    return score
