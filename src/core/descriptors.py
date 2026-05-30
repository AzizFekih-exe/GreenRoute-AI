from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors
import numpy as np

def get_all_descriptors(smiles):
    """Extract 200+ RDKit descriptors for a molecule"""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    
    desc_names = [desc_name for desc_name, _ in Descriptors.descList]
    desc_values = [func(mol) for _, func in Descriptors.descList]
    
    # Add extra fingerprints as features
    morgan_fp = rdMolDescriptors.GetMorganFingerprintAsBitVect(mol, radius=2, nBits=256)
    morgan_array = np.array(morgan_fp)
    
    return dict(zip(desc_names, desc_values)) | {'morgan_fp': morgan_array}

def prepare_features_from_smiles(smiles_list):
    """Convert SMILES list to feature matrix using RDKit descriptors"""
    features = []
    valid_indices = []
    
    for i, smiles in enumerate(smiles_list):
        desc = get_all_descriptors(smiles)
        if desc:
            # Remove non-numeric (morgan_fp handled separately)
            numeric_desc = {k: v for k, v in desc.items() 
                          if isinstance(v, (int, float)) and not isinstance(v, np.ndarray)}
            features.append(list(numeric_desc.values()))
            valid_indices.append(i)
    
    return np.array(features), valid_indices
