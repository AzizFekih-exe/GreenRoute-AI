import re
import requests
from urllib.parse import quote
from rdkit import Chem, RDLogger
from rdkit.Chem import Descriptors
from .utils import extract_smiles
from .rag import retrieve_as_context

# Silence RDKit logos/errors for cleaner logs
RDLogger.DisableLog('rdApp.*')


def calculate_environmental_proxy(mol):
    """Calculates a proxy for environmental 'greenness' based on complexity and atoms."""
    complexity = Descriptors.BertzCT(mol)
    mw = Descriptors.MolWt(mol)
    complexity_index = complexity / mw if mw > 0 else 0
    
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
    Pull SMILES strings embedded between 'SMILES: ' and the following ').'
    Handles nested parentheses correctly by counting depth.
    """
    results = []
    pattern = r"SMILES:\s*"
    for m in re.finditer(pattern, question):
        start = m.end()
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


def _do_molecular_analysis(question: str, smiles_list: list[str]) -> tuple[list[str], list[str], list[str]]:
    """Run RDKit + PubChem analysis on SMILES. Returns (content_parts, sources, errors)."""
    content_parts = []
    sources = []
    errors = []

    primary_smiles = smiles_list[0]
    mol = Chem.MolFromSmiles(primary_smiles)
    if not mol:
        errors.append("Invalid SMILES structure.")
        return content_parts, sources, errors

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

    # 2. PubChem BioAssay Search
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

    return content_parts, sources, errors


def librarian(question: str) -> dict:
    """
    Multi-source knowledge agent:
      1. RAG retrieval from vectorized documents (always runs)
      2. RDKit molecular property analysis (if SMILES found)
      3. PubChem BioAssay lookup (if SMILES found)
    """
    print("\n[LIBRARIAN] Performing multi-source lookup...")
    
    content_parts = []
    sources = []
    errors = []

    # ── Source 1: RAG from Supabase ──────────────────────────────────
    try:
        rag_context = retrieve_as_context(question, top_k=5, threshold=0.5)
        if rag_context:
            content_parts.append(f"=== RAG KNOWLEDGE BASE ===\n{rag_context}")
            sources.append("RAG Knowledge Base")
            print("   [RAG] Retrieved relevant document chunks.")
        else:
            print("   [RAG] No relevant chunks found above threshold.")
    except Exception as e:
        errors.append(f"RAG retrieval error: {e}")
        print(f"   [RAG ERROR] {e}")

    # ── Source 2 & 3: Molecular analysis (only if SMILES present) ────
    smiles_list = _extract_smiles_from_question(question)
    if smiles_list:
        mol_parts, mol_sources, mol_errors = _do_molecular_analysis(question, smiles_list)
        content_parts.extend(mol_parts)
        sources.extend(mol_sources)
        errors.extend(mol_errors)
    
    # If we got nothing at all
    if not content_parts:
        return {
            "success": False, 
            "content": "", 
            "sources": [], 
            "error": " | ".join(errors) if errors else "No relevant data found in knowledge base or molecular analysis."
        }

    return {
        "success": True, 
        "content": "\n\n".join(content_parts), 
        "sources": sources,
        "error": " | ".join(errors) if errors else None
    }
