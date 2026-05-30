from rdkit import Chem
from rdkit.Chem import AllChem
import numpy as np
import faiss

def create_solvent_database(solvent_smiles_dict):
    """Build FAISS index for fast solvent similarity search"""
    fingerprints = []
    names = []
    smiles_list = []
    
    for name, smiles in solvent_smiles_dict.items():
        mol = Chem.MolFromSmiles(smiles)
        if mol:
            fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius=2, nBits=2048)
            fp_array = np.array(fp, dtype=np.float32)
            fingerprints.append(fp_array)
            names.append(name)
            smiles_list.append(smiles)
    
    # Create FAISS index
    index = faiss.IndexFlatL2(2048)  # L2 distance
    index.add(np.array(fingerprints))
    
    return index, names, smiles_list

def find_similar_solvents(query_smiles, index, solvent_names, solvent_smiles, k=3):
    """Find k most similar solvents to query"""
    mol = Chem.MolFromSmiles(query_smiles)
    if not mol:
        return []
        
    fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius=2, nBits=2048)
    fp_array = np.array(fp, dtype=np.float32).reshape(1, -1)
    
    distances, indices = index.search(fp_array, k)
    
    results = []
    for i, idx in enumerate(indices[0]):
        if idx < len(solvent_names):
            results.append({
                'name': solvent_names[idx],
                'smiles': solvent_smiles[idx],
                'similarity': 1 / (1 + distances[0][i])  # convert distance to similarity
            })
    return results
