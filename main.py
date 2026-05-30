"""
Chemoinformatics Demo
=====================
Thin entry-point that demonstrates all modules. No training logic here.
"""

from src.core.metrics import rank_solvents
from src.ml.predictor import predict_with_uncertainty
from src.ml.train import train_yield_predictor, train_tox21_classifier
from src.db.solvent_db import create_solvent_database, find_similar_solvents
from src.data.tox21_loader import dataset_summary


def main():
    print("=== Chemoinformatics Toolkit Demo ===\n")

    # ------------------------------------------------------------------
    # 1. Yield Prediction (small demo with known molecules)
    # NOTE: These are simple reference molecules for demonstration only.
    #       A production model would use a real reaction-yield dataset.
    # ------------------------------------------------------------------
    print("[1] Yield Predictor (demo)")
    demo_smiles = ["CCO", "CC=O", "c1ccccc1", "CC(C)=O"]
    demo_yields = [85, 72, 91, 68]

    model, scaler = train_yield_predictor(demo_smiles, demo_yields)

    test_smiles = "CCO"
    yield_pred, ci = predict_with_uncertainty(test_smiles, model, scaler)
    print(f"    Predicted yield for {test_smiles}: {yield_pred:.1f}% ± {ci:.1f}%")

    # ------------------------------------------------------------------
    # 2. Solvent Similarity Search
    # ------------------------------------------------------------------
    print("\n[2] Solvent Similarity Search")
    solvents = {
        "ethanol":          "CCO",
        "toluene":          "Cc1ccccc1",
        "water":            "O",
        "DMF":              "CN(C)C=O",
        "dichloromethane":  "C(Cl)Cl",
    }

    index, names, smiles = create_solvent_database(solvents)

    query = "CCOC"  # diethyl ether
    similar = find_similar_solvents(query, index, names, smiles, k=3)
    print(f"    Top-3 similar to {query}:")
    for s in similar:
        print(f"      {s['name']}: {s['similarity']:.3f}")

    # ------------------------------------------------------------------
    # 3. Green Chemistry Ranking
    # ------------------------------------------------------------------
    print("\n[3] Green Chemistry Ranking")
    ranked = rank_solvents(solvents)
    for r in ranked:
        print(f"    {r['name']}: {r['green_score']:.3f}")

    # ------------------------------------------------------------------
    # 4. Tox21 Toxicity Prediction (real benchmark data)
    # ------------------------------------------------------------------
    print("\n[4] Tox21 Toxicity Prediction")
    assay = "NR-AR"
    print(f"    Loading & training on assay: {assay} …")
    result = train_tox21_classifier(assay=assay, use_sparse=False)
    print(f"    Train: {result['X_train_shape'][0]} samples, "
          f"{result['X_train_shape'][1]} features")
    print(f"    Test:  {result['X_test_shape'][0]} samples")
    print(f"    Positives — train: {result['pos_train']}, "
          f"test: {result['pos_test']}")
    print(f"    ROC-AUC: {result['roc_auc']:.4f}")

    # Quick summary of all 12 assays
    print("\n    Tox21 label summary (all assays):")
    summary = dataset_summary()
    for name, stats in summary.items():
        print(f"      {name:>15s}: {stats['active']:>4d} active, "
              f"{stats['inactive']:>5d} inactive, "
              f"{stats['missing']:>5d} missing")


if __name__ == "__main__":
    main()
