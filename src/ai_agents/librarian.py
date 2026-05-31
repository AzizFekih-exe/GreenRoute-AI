import requests
from urllib.parse import quote
from rdkit import Chem

def extract_smiles(text: str) -> str:
    """Attempts to find a valid SMILES string in the question."""
    words = text.split()
    for w in words:
        w_clean = w.strip("?,.()\"'")
        # Try to parse with RDKit
        mol = Chem.MolFromSmiles(w_clean)
        # Avoid treating words like 'ON', 'NO', 'I' as SMILES unless they really seem like one. Let's just trust RDKit for now, but exclude very short words if they're common.
        if mol is not None and w_clean.upper() not in ["I", "NO", "ON", "A", "AS", "IN", "AT", "IS", "BE", "HE", "WE", "ME", "US", "SO", "DO", "GO"]:
            return w_clean
    return ""

def librarian(question: str) -> dict:
    """Queries PubChem BioAssay records for a SMILES structure."""
    print("\n[LIBRARIAN] Searching PubChem BioAssay records...")
    
    smiles = extract_smiles(question)
    
    if not smiles:
        return {"success": False, "content": "", "sources": [], "error": "No valid SMILES string found in query."}
        
    try:
        encoded_smiles = quote(smiles)
        api_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{encoded_smiles}/assaysummary/JSON"
        
        # Step 1: Tell PubChem to search its BioAssay records for this specific structure
        response = requests.get(api_url, timeout=10)
        
        if response.status_code != 200:
            return {"success": False, "content": "", "sources": [], "error": f"PubChem API returned status {response.status_code}. It may not exist in their DB or the SMILES is malformed."}
            
        data = response.json()
        
        table = data.get("Table", {})
        columns = table.get("Columns", {}).get("Column", [])
        rows = table.get("Row", [])
        
        if not rows:
            return {"success": True, "content": f"No BioAssay records found for SMILES: {smiles}", "sources": [api_url]}
            
        chunks = [f"PubChem BioAssay Results for SMILES: {smiles}"]
        for r in rows[:7]:  # Top 7 assays
            cells = r.get("Cell", [])
            row_dict = dict(zip(columns, cells))
            
            aid = row_dict.get("AID", "N/A")
            activity = row_dict.get("Activity Outcome", "N/A")
            target = row_dict.get("Target Name", "N/A")
            
            chunks.append(f"• Assay AID: {aid} - Outcome: {activity} - Target: {target}")
            
        print(f"   [SUCCESS] Found {len(rows)} BioAssay records. Showing top {min(7, len(rows))}.")
        return {"success": True, "content": "\n".join(chunks), "sources": [f"PubChem Assays for {smiles}"]}
        
    except Exception as e:
        print(f"   [ERROR] Librarian error: {e}")
        return {"success": False, "content": "", "sources": [], "error": str(e)}
