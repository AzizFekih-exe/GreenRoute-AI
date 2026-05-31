import re
import pandas as pd
from src.tox21_loader import load_compound_metadata

# Assay columns and their human-readable names
_ASSAY_LABELS = {
    "NR.AhR":       "Aryl hydrocarbon Receptor (NR-AhR)",
    "NR.AR":        "Androgen Receptor (NR-AR)",
    "NR.AR.LBD":    "Androgen Receptor LBD (NR-AR-LBD)",
    "NR.Aromatase": "Aromatase (NR-Aromatase)",
    "NR.ER":        "Estrogen Receptor (NR-ER)",
    "NR.ER.LBD":    "Estrogen Receptor LBD (NR-ER-LBD)",
    "NR.PPAR.gamma":"PPAR-gamma (NR-PPAR-gamma)",
    "SR.ARE":       "Oxidative Stress (SR-ARE)",
    "SR.ATAD5":     "DNA Damage (SR-ATAD5)",
    "SR.HSE":       "Heat Shock (SR-HSE)",
    "SR.MMP":       "Mitochondrial Membrane Potential (SR-MMP)",
    "SR.p53":       "p53 Tumor Suppressor (SR-p53)",
}


def _smiles_to_inchikey(smiles: str) -> str | None:
    """Convert a SMILES string to an InChIKey using RDKit."""
    try:
        from rdkit import Chem
        from rdkit.Chem.inchi import MolToInchi
        from rdkit.Chem.inchi import InchiToInchiKey
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        inchi = MolToInchi(mol)
        if not inchi:
            return None
        return InchiToInchiKey(inchi)
    except Exception:
        return None


def _extract_smiles_from_question(question: str) -> list[str]:
    """
    Pull SMILES strings embedded between 'SMILES: ' and the following ').'.
    Handles nested parentheses correctly by counting depth.
    """
    results = []
    pattern = r"SMILES:\s*"
    for m in re.finditer(pattern, question):
        start = m.end()
        # Walk forward counting parenthesis depth to find where this SMILES ends.
        # SMILES ends when we hit ') ' or ').' or end-of-string at depth 0.
        depth = 0
        i = start
        while i < len(question):
            ch = question[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                if depth == 0:
                    # Closing paren belongs to the surrounding text, not SMILES
                    break
                depth -= 1
            elif ch in (" ", "\t", "\n") and depth == 0:
                break
            i += 1
        smiles = question[start:i].strip().rstrip(".,;")
        if smiles:
            results.append(smiles)
    return results


def _format_tox_record(row: pd.Series) -> str:
    """Build a human-readable string for one Tox21 record."""
    parts = [f"Compound ID: {row.get('ID', 'N/A')} | InChIKey: {row.get('inchikey', 'N/A')}"]
    tox_parts = []
    for col, label in _ASSAY_LABELS.items():
        val = row.get(col)
        if pd.notna(val):
            result = "ACTIVE (toxic)" if int(val) == 1 else "INACTIVE (non-toxic)"
            tox_parts.append(f"  • {label}: {result}")
    if tox_parts:
        parts.append("Toxicity Assay Results:\n" + "\n".join(tox_parts))
    else:
        parts.append("  (No assay data available for this compound)")
    return "\n".join(parts)


def librarian(question: str) -> dict:
    """
    Queries the local Tox21 database for compound toxicity profiles.
    Extracts SMILES from the question, converts to InChIKey, then looks up Tox21 records.
    """
    print("\n[LIBRARIAN] Searching local Tox21 dataset...")
    try:
        df = load_compound_metadata()

        # Extract all SMILES from question and convert to InChIKeys
        smiles_list = _extract_smiles_from_question(question)
        if not smiles_list:
            return {
                "success": False, "content": "", "sources": [],
                "error": "No SMILES found in question to look up in Tox21."
            }

        found_records = []
        for smi in smiles_list:
            ikey = _smiles_to_inchikey(smi)
            if not ikey:
                continue
            # Match on the first 14 chars of InChIKey (connectivity layer) to be robust
            connectivity = ikey.split("-")[0]
            mask = df["inchikey"].str.startswith(connectivity, na=False)
            hits = df[mask]
            if not hits.empty:
                found_records.append(hits.head(2))

        if not found_records:
            return {
                "success": False, "content": "", "sources": [],
                "error": "No compounds found in Tox21 matching the query molecules."
            }

        combined_df = pd.concat(found_records).drop_duplicates(subset=["ID"]).head(5)
        chunks = [_format_tox_record(row) for _, row in combined_df.iterrows()]

        print(f"   [SUCCESS] Found {len(chunks)} Tox21 records for query molecules.")
        return {
            "success": True,
            "content": "\n\n---\n\n".join(chunks),
            "sources": ["Tox21 Dataset (tox21_compoundData.csv)"]
        }

    except Exception as e:
        print(f"   [ERROR] Librarian error: {e}")
        return {"success": False, "content": "", "sources": [], "error": str(e)}
