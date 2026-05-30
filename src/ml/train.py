"""
Training pipelines
==================
All model training logic lives here — main.py only orchestrates and prints.
"""

import numpy as np
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score

from src.core.descriptors import prepare_features_from_smiles
from src.ml.predictor import predict_with_uncertainty
from src.data.tox21_loader import load_tox21_data, dataset_summary


def train_yield_predictor(reactant_smiles, yields):
    """
    Train a RandomForest yield predictor from SMILES + yield pairs.

    Parameters
    ----------
    reactant_smiles : list[str]
        SMILES strings of reactants / solvents.
    yields : list[float]
        Corresponding reaction yields (%).

    Returns
    -------
    model : RandomForestRegressor
        Fitted model.
    scaler : StandardScaler
        Fitted feature scaler.
    """
    X, valid_idx = prepare_features_from_smiles(reactant_smiles)
    y = np.array(yields)[valid_idx]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_scaled, y)

    return model, scaler


def train_tox21_classifier(assay="NR-AR", use_sparse=False, n_estimators=100):
    """
    Train a RandomForest classifier on a Tox21 toxicity assay.

    Parameters
    ----------
    assay : str
        One of the 12 Tox21 assay names (e.g. "NR-AR", "SR-MMP").
    use_sparse : bool
        Whether to include sparse substructure features.
    n_estimators : int
        Number of trees in the forest.

    Returns
    -------
    dict
        Training results containing the classifier, data shapes,
        label counts, and ROC-AUC on the held-out test set.
    """
    X_train, X_test, y_train, y_test = load_tox21_data(
        assay=assay,
        use_sparse=use_sparse,
    )

    clf = RandomForestClassifier(
        n_estimators=n_estimators, n_jobs=-1, random_state=42
    )
    clf.fit(X_train, y_train)

    proba = clf.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, proba)

    return {
        "classifier": clf,
        "assay": assay,
        "X_train_shape": X_train.shape,
        "X_test_shape": X_test.shape,
        "pos_train": int((y_train == 1).sum()),
        "pos_test": int((y_test == 1).sum()),
        "roc_auc": auc,
    }
