# hybrid_similarity.py - Best of both worlds
from rdkit import Chem
from rdkit.Chem import AllChem, DataStructs, Descriptors
import numpy as np

def property_similarity(smiles1, smiles2):
    """Compare molecular properties (LogP, MW, HBD, HBA)"""
    mol1 = Chem.MolFromSmiles(smiles1)
    mol2 = Chem.MolFromSmiles(smiles2)
    
    if mol1 is None or mol2 is None:
        return 0.0
    
    # Get properties
    props1 = [
        Descriptors.MolLogP(mol1),
        Descriptors.MolWt(mol1),
        Descriptors.NumHDonors(mol1),
        Descriptors.NumHAcceptors(mol1)
    ]
    props2 = [
        Descriptors.MolLogP(mol2),
        Descriptors.MolWt(mol2),
        Descriptors.NumHDonors(mol2),
        Descriptors.NumHAcceptors(mol2)
    ]
    
    # Normalize and calculate similarity
    props1 = np.array(props1)
    props2 = np.array(props2)
    
    # Maximum differences for normalization
    max_diffs = [5.0, 500.0, 5.0, 5.0]  # LogP, MW, HBD, HBA ranges
    
    normalized_diff = np.abs(props1 - props2) / max_diffs
    similarity = 1 - np.mean(normalized_diff)
    
    return max(0, min(1, similarity))  # Clamp to [0,1]

def structural_similarity(smiles1, smiles2):
    """Traditional RDKit fingerprint similarity"""
    mol1 = Chem.MolFromSmiles(smiles1)
    mol2 = Chem.MolFromSmiles(smiles2)
    
    if mol1 is None or mol2 is None:
        return 0.0
    
    fp1 = AllChem.GetMorganFingerprintAsBitVect(mol1, radius=2, nBits=2048)
    fp2 = AllChem.GetMorganFingerprintAsBitVect(mol2, radius=2, nBits=2048)
    
    return DataStructs.TanimotoSimilarity(fp1, fp2)

def combined_similarity(smiles1, smiles2, struct_weight=0.5, prop_weight=0.5):
    """Combine structural and property similarity"""
    struct_sim = structural_similarity(smiles1, smiles2)
    prop_sim = property_similarity(smiles1, smiles2)
    
    return struct_weight * struct_sim + prop_weight * prop_sim

# Test with problem case
print("="*60)
print("SIMILARITY COMPARISON")
print("="*60)

pairs = [
    ("Ethanol", "CCO", "Methanol", "CO"),
    ("Ethanol", "CCO", "Water", "O"),
    ("Benzene", "c1ccccc1", "Toluene", "Cc1ccccc1"),
]

for name1, smiles1, name2, smiles2 in pairs:
    struct = structural_similarity(smiles1, smiles2)
    prop = property_similarity(smiles1, smiles2)
    combined = combined_similarity(smiles1, smiles2)
    
    print(f"\n{name1} vs {name2}")
    print(f"  Structural similarity: {struct:.3f}")
    print(f"  Property similarity:   {prop:.3f}")
    print(f"  Combined:              {combined:.3f}")