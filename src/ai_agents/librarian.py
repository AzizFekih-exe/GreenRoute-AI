import re
import os
import requests
from urllib.parse import quote
import pandas as pd
from rdkit import Chem
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
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        from rdkit.Chem.inchi import MolToInchi
        from rdkit.Chem.inchi import InchiToInchiKey
        inchi = MolToInchi(mol)
        if not inchi:
            return None
        return InchiToInchiKey(inchi)
    except Exception:
        return None


def extract_smiles(text: str) -> str:
    """Attempts to find a valid SMILES string in the question."""
    words = text.split()
    for w in words:
        w_clean = w.strip("?,.()\"'")
        # Try to parse with RDKit
        mol = Chem.MolFromSmiles(w_clean)
        # Avoid treating words like 'ON', 'NO', 'I' as SMILES unless they really seem like one.
        if mol is not None and w_clean.upper() not in ["I", "NO", "ON", "A", "AS", "IN", "AT", "IS", "BE", "HE", "WE", "ME", "US", "SO", "DO", "GO"]:
            return w_clean
    return ""


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
        depth = 0
        i = start
        while i < len(question):
            ch = question[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                if depth == 0:
                    break
                depth -= 1
            elif ch in (" ", "\t", "\n") and depth == 0:
                break
            i += 1
        smiles = question[start:i].strip().rstrip(".,;")
        if smiles:
            results.append(smiles)
    
    # Fallback to general SMILES extraction if none found via prefix
    if not results:
        single = extract_smiles(question)
        if single:
            results.append(single)
            
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
    Queries both the local Tox21 database and the online PubChem BioAssay records.
    """
    print("\n[LIBRARIAN] Initiating dual lookup (Local Tox21 + PubChem API)...")
    
    content_parts = []
    sources = []
    errors = []

    # 1. Local Tox21 Lookup
    try:
        df = load_compound_metadata()
        smiles_list = _extract_smiles_from_question(question)
        if smiles_list:
            found_records = []
            for smi in smiles_list:
                ikey = _smiles_to_inchikey(smi)
                if not ikey:
                    continue
                connectivity = ikey.split("-")[0]
                mask = df["inchikey"].str.startswith(connectivity, na=False)
                hits = df[mask]
                if not hits.empty:
                    found_records.append(hits.head(2))

            if found_records:
                combined_df = pd.concat(found_records).drop_duplicates(subset=["ID"]).head(5)
                chunks = [_format_tox_record(row) for _, row in combined_df.iterrows()]
                content_parts.append("=== TOX21 DATABASE ===\n" + "\n\n---\n\n".join(chunks))
                sources.append("Tox21 Dataset (tox21_compoundData.csv)")
            else:
                errors.append("No local Tox21 records matched the query SMILES.")
        else:
            errors.append("No SMILES found in question to look up locally.")
    except Exception as e:
        errors.append(f"Local Tox21 lookup error: {e}")

    # 2. PubChem BioAssay Lookup
    try:
        smiles = extract_smiles(question)
        if smiles:
            encoded_smiles = quote(smiles)
            api_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{encoded_smiles}/assaysummary/JSON"
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                table = data.get("Table", {})
                columns = table.get("Columns", {}).get("Column", [])
                rows = table.get("Row", [])
                if rows:
                    chunks = [f"PubChem BioAssay Results for SMILES: {smiles}"]
                    for r in rows[:7]:  # Top 7 assays
                        cells = r.get("Cell", [])
                        row_dict = dict(zip(columns, cells))
                        aid = row_dict.get("AID", "N/A")
                        activity = row_dict.get("Activity Outcome", "N/A")
                        target = row_dict.get("Target Name", "N/A")
                        chunks.append(f"• Assay AID: {aid} - Outcome: {activity} - Target: {target}")
                    content_parts.append("=== PUBCHEM BIOASSAY ===\n" + "\n".join(chunks))
                    sources.append(f"PubChem Assays for {smiles}")
                else:
                    errors.append(f"No PubChem BioAssay records found for SMILES: {smiles}")
            else:
                errors.append(f"PubChem API returned status {response.status_code}")
        else:
            errors.append("No valid SMILES string found for PubChem lookup.")
    except Exception as e:
        errors.append(f"PubChem lookup error: {e}")

    # 3. Combine results
    if content_parts:
        return {
            "success": True,
            "content": "\n\n".join(content_parts),
            "sources": sources
        }
    else:
        return {
            "success": False,
            "content": "",
            "sources": [],
            "error": " | ".join(errors)
        }
