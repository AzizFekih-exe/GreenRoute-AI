import re
import os
import requests
import numpy as np
import pandas as pd
from urllib.parse import quote
from rdkit import Chem, RDLogger
from rdkit.Chem import Descriptors
from src.tox21_loader import load_compound_metadata

# Silence RDKit logos/errors for cleaner logs
RDLogger.DisableLog('rdApp.*')

try:
    from src.ai_agents.utils import extract_smiles
except ImportError:
    # Fallback if import fails or file not found
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
        from rdkit.Chem.inchi import MolToInchi, InchiToInchiKey
        inchi = MolToInchi(mol)
        if not inchi:
            return None
        return InchiToInchiKey(inchi)
    except Exception:
        return None


def calculate_environmental_proxy(mol):
    """Calculates a proxy for environmental 'greenness' based on complexity and atoms."""
    # Crude proxy for E-factor/Complexity: BertzCT (Complexity) / Molecular Weight
    complexity = Descriptors.BertzCT(mol)
    mw = Descriptors.MolWt(mol)
    # Higher complexity per Dalton typically means more steps/solvents (Higher E-factor potential)
    complexity_index = complexity / mw if mw > 0 else 0
    
    # Toxicity Proxy: Rule of 5 violations + specific heavy atoms
    h_donors = Descriptors.NumHDonors(mol)
    h_acc = Descriptors.NumHAcceptors(mol)
    logp = Descriptors.MolLogP(mol)
    
    violations = 0
    if mw > 500: violations += 1
    if logp > 5: violations += 1
    if h_donors > 5: violations += 1
    if h_acc > 10: violations += 1
    
    return {
        "complexity_index": round(complexity_index, 2),
        "ro5_violations": violations,
        "is_drug_like": violations <= 1
    }


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
    Queries Tox21, PubChem BioAssay, and calculates RDKit properties for scientific insights.
    """
    print("\n[LIBRARIAN] Performing molecular analysis & multi-source lookup...")
    
    smiles_list = _extract_smiles_from_question(question)
    if not smiles_list:
        return {
            "success": False, 
            "content": "", 
            "sources": [], 
            "error": "No valid SMILES string found in query."
        }
        
    primary_smiles = smiles_list[0]
    mol = Chem.MolFromSmiles(primary_smiles)
    if not mol:
        return {
            "success": False, 
            "content": "", 
            "sources": [], 
            "error": "Invalid SMILES structure."
        }

    content_parts = []
    sources = []
    errors = []

    # 1. RDKit Molecular Properties
    mw = Descriptors.MolWt(mol)
    logp = Descriptors.MolLogP(mol)
    h_donors = Descriptors.NumHDonors(mol)
    h_acc = Descriptors.NumHAcceptors(mol)
    env_data = calculate_environmental_proxy(mol)

    rdkit_block = (
        f"Molecular Analysis for SMILES: {primary_smiles}\n"
        f"🧪 RDKIT PROPERTIES (Physicochemical):\n"
        f"• Molecular Weight: {mw:.2f} g/mol\n"
        f"• LogP (Lipophilicity): {logp:.2f}\n"
        f"• H-Bond Donors: {h_donors} | H-Bond Acceptors: {h_acc}\n"
        f"• Drug-likeness: {'High' if env_data['is_drug_like'] else 'Low'} ({env_data['ro5_violations']} Rule of 5 violations)\n"
        f"🌱 GREEN & TOXICITY PROXY:\n"
        f"• Synthetic Complexity Index: {env_data['complexity_index']} (Higher means more likely higher E-factor)\n"
        f"• Toxicity Flag: {'Low' if logp < 3 else 'Elevated LogP (Potential bioaccumulation)'}"
    )
    content_parts.append(rdkit_block)
    sources.append("RDKit Properties")

    # 2. Local Tox21 Lookup
    try:
        df = load_compound_metadata()
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
            sources.append("Tox21 Dataset")
        else:
            errors.append("No local Tox21 records matched.")
    except Exception as e:
        errors.append(f"Local Tox21 lookup error: {e}")

    # 3. PubChem BioAssay Search
    try:
        encoded_smiles = quote(primary_smiles)
        api_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{encoded_smiles}/assaysummary/JSON"
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            table = data.get("Table", {})
            columns = table.get("Columns", {}).get("Column", [])
            rows = table.get("Row", [])
            
            if rows:
                all_parsed = []
                for r in rows:
                    cells = r.get("Cell", [])
                    row_dict = dict(zip(columns, cells))
                    all_parsed.append(row_dict)
                
                active_with_target = [r for r in all_parsed if r.get("Activity Outcome") == "Active" and r.get("Target Name") not in ["None", "N/A", ""]]
                active_no_target = [r for r in all_parsed if r.get("Activity Outcome") == "Active" and r not in active_with_target]
                
                pub_chunks = [f"🔬 PUBCHEM BIOASSAY SUMMARY (Total: {len(rows)} assays found):"]
                display_results = active_with_target[:3] + active_no_target[:(5 - len(active_with_target[:3]))]
                for r in display_results[:5]:
                    target = r.get("Target Name", "Phenotypic/General")
                    pub_chunks.append(f"  - AID: {r.get('AID')} | Target: {target} | {r.get('Activity Outcome').upper()}")
                
                content_parts.append("\n".join(pub_chunks))
                sources.append("PubChem BioAssays")
            else:
                errors.append("No PubChem experimental assay records found.")
        else:
            errors.append(f"PubChem API issue (Status {response.status_code})")
            
    except Exception as e:
        errors.append(f"PubChem lookup error: {e}")

    return {
        "success": True, 
        "content": "\n\n".join(content_parts), 
        "sources": sources,
        "error": " | ".join(errors) if errors else None
    }
