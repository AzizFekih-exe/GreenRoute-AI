from rdkit import Chem

def extract_smiles(text: str) -> str:
    """Attempts to find a valid SMILES string in the question."""
    words = text.split()
    for w in words:
        w_clean = w.strip("?,.()\"'")
        # Try to parse with RDKit
        mol = Chem.MolFromSmiles(w_clean)
        # Avoid treating common short words as SMILES
        if mol is not None and w_clean.upper() not in ["I", "NO", "ON", "A", "AS", "IN", "AT", "IS", "BE", "HE", "WE", "ME", "US", "SO", "DO", "GO"]:
            return w_clean
    return ""
