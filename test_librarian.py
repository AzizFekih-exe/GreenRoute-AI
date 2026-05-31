from src.ai_agents.librarian import librarian

def test_librarian_with_smiles():
    print("="*60)
    print("TESTING LIBRARIAN AGENT (PUBCHEM API)")
    print("="*60)
    
    # Example: Aspirin SMILES
    query = "Find bioassay records for aspirin: CC(=O)OC1=CC=CC=C1C(=O)O"
    
    print(f"\nUser Query: {query}")
    result = librarian(query)
    
    if result["success"]:
        print(f"\n[SUCCESS] Content retrieved:")
        print("-" * 40)
        print(result["content"])
        print("-" * 40)
        print(f"Sources: {result['sources']}")
    else:
        print(f"\n[FAILED] Error: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    test_librarian_with_smiles()
