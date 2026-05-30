from rdkit import Chem
from rdkit.Chem import Descriptors
import numpy as np

def calculate_green_metrics(smiles):
    """Compute green metrics from SMILES using RDKit"""
    mol = Chem.MolFromSmiles(smiles)
    if not mol:
        return None
    
    # Toxicity proxy (LogP based - lower is better)
    logp = Descriptors.MolLogP(mol)
    toxicity_score = 1 / (1 + np.exp(-logp))  # sigmoid to 0-1
    
    # Biodegradability proxy (based on molecular complexity)
    num_rings = Descriptors.RingCount(mol)
    rotatable_bonds = Descriptors.NumRotatableBonds(mol)
    biodegradability = 1 / (1 + 0.5 * num_rings + 0.1 * rotatable_bonds)
    
    # VOC potential (based on molecular weight - lower MW = more volatile)
    mw = Descriptors.MolWt(mol)
    voc_score = np.exp(-mw / 100)  # 0-1 scale
    
    # Atom economy (for synthesis context - simplified)
    heavy_atoms = mol.GetNumHeavyAtoms()
    total_atoms = mol.GetNumAtoms()
    atom_economy = heavy_atoms / total_atoms if total_atoms > 0 else 0
    
    return {
        'toxicity': toxicity_score,
        'biodegradability': biodegradability,
        'voc': voc_score,
        'atom_economy': atom_economy,
        'logp': logp
    }

def rank_solvents(solvent_smiles_dict, weights=None):
    """Rank solvents by greenness with adjustable weights"""
    if weights is None:
        weights = {'toxicity': 0.3, 'voc': 0.2, 
                  'biodegradability': 0.3, 'atom_economy': 0.2}
    
    rankings = []
    for name, smiles in solvent_smiles_dict.items():
        metrics = calculate_green_metrics(smiles)
        if metrics:
            # Normalize metrics (lower toxicity/voc better, higher biodeg/atom economy better)
            score = (weights['toxicity'] * (1 - metrics['toxicity']) +
                    weights['voc'] * (1 - metrics['voc']) +
                    weights['biodegradability'] * metrics['biodegradability'] +
                    weights['atom_economy'] * metrics['atom_economy'])
            
            rankings.append({
                'name': name,
                'smiles': smiles,
                'green_score': score,
                'metrics': metrics
            })
    
    return sorted(rankings, key=lambda x: x['green_score'], reverse=True)
