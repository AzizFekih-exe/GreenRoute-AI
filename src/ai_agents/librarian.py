import os
import pandas as pd
from src.tox21_loader import load_compound_metadata


def librarian(question: str) -> dict:
    """Queries the local Tox21 database for compound information."""
    print("\n[LIBRARIAN] Searching local Tox21 dataset...")
    try:
        df = load_compound_metadata()
        # Searching the compoundData.csv
        # We will do a generic search using keywords from the question
        keywords = set(question.lower().replace("?", "").replace(",", "").split())
        
        # very basic keyword matching on the dataframe as text
        # usually compound names aren't extremely explicitly named in the basic tox21_compoundData except standard IDs, 
        # but let's try our best to just grab a few interesting records if they match terms
        
        matches = []
        for term in keywords:
            if len(term) > 3: # Avoid matching 'the', 'is', 'a'
                mask = df.astype(str).apply(lambda x: x.str.contains(term, case=False, na=False)).any(axis=1)
                match_subset = df[mask]
                if not match_subset.empty:
                    matches.append(match_subset.head(3))
        
        if not matches:
            return {"success": False, "content": "", "sources": [], "error": "No compounds found in Tox21 matching the query."}
            
        combined_df = pd.concat(matches).drop_duplicates().head(5)
        
        chunks = []
        for _, row in combined_df.iterrows():
            row_str = " | ".join([f"{col}: {val}" for col, val in row.items() if pd.notna(val)])
            chunks.append(f"Tox21 Record: {row_str}")

        print(f"   [SUCCESS] Found {len(chunks)} relevant records from Tox21.")
        return {"success": True, "content": "\n---\n".join(chunks), "sources": ["Tox21 Dataset (tox21_compoundData.csv)"]}

    except Exception as e:
        print(f"   [ERROR] Librarian error: {e}")
        return {"success": False, "content": "", "sources": [], "error": str(e)}
