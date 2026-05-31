"""
Tox21 Dataset Loader
====================
Downloads and loads the Tox21 toxicology benchmark dataset from the
JKU Bioinformatics mirror (https://bioinf.jku.at/research/DeepTox/tox21.html).

The dataset contains:
- 12,060 training compounds and 647 test compounds
- 801 dense chemical descriptors (molecular weight, solubility, surface area…)
- 272,776 sparse chemical substructure features (ECFP10, DFS6, DFS8) in Matrix Market format
- 12 binary toxicity assay labels with many missing values (NAs)

Assays:
    NR-AR, NR-AR-LBD, NR-AhR, NR-Aromatase, NR-ER, NR-ER-LBD,
    NR-PPAR-gamma, SR-ARE, SR-ATAD5, SR-HSE, SR-MMP, SR-p53
"""

import os
import gzip
import logging
from pathlib import Path
from urllib.request import urlretrieve

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL = "https://bioinf.jku.at/research/DeepTox/"

_FILES = {
    # Dense features
    "dense_train": "tox21_dense_train.csv.gz",
    "dense_test":  "tox21_dense_test.csv.gz",
    # Sparse features
    "sparse_train":      "tox21_sparse_train.mtx.gz",
    "sparse_test":       "tox21_sparse_test.mtx.gz",
    "sparse_colnames":   "tox21_sparse_colnames.txt.gz",
    "sparse_rownames_train": "tox21_sparse_rownames_train.txt.gz",
    "sparse_rownames_test":  "tox21_sparse_rownames_test.txt.gz",
    # Labels
    "labels_train": "tox21_labels_train.csv.gz",
    "labels_test":  "tox21_labels_test.csv.gz",
    # Compound metadata
    "compound_data": "tox21_compoundData.csv",
}

# Public-facing assay names (dashes, readable)
TOX21_ASSAYS = [
    "NR-AR", "NR-AR-LBD", "NR-AhR", "NR-Aromatase",
    "NR-ER", "NR-ER-LBD", "NR-PPAR-gamma",
    "SR-ARE", "SR-ATAD5", "SR-HSE", "SR-MMP", "SR-p53",
]

# Actual column names in the JKU CSV files (dots instead of dashes)
_ASSAY_COL_MAP = {
    "NR-AR":        "NR.AR",
    "NR-AR-LBD":    "NR.AR.LBD",
    "NR-AhR":       "NR.AhR",
    "NR-Aromatase": "NR.Aromatase",
    "NR-ER":        "NR.ER",
    "NR-ER-LBD":    "NR.ER.LBD",
    "NR-PPAR-gamma":"NR.PPAR.gamma",
    "SR-ARE":       "SR.ARE",
    "SR-ATAD5":     "SR.ATAD5",
    "SR-HSE":       "SR.HSE",
    "SR-MMP":       "SR.MMP",
    "SR-p53":       "SR.p53",
}

DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "tox21"

# ---------------------------------------------------------------------------
# Download helpers
# ---------------------------------------------------------------------------

def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _download_file(filename: str, data_dir: Path) -> Path:
    """Download a single file if it doesn't already exist on disk."""
    dest = data_dir / filename
    if dest.exists():
        logger.debug("Already cached: %s", dest)
        return dest

    url = BASE_URL + filename
    logger.info("Downloading %s → %s", url, dest)
    try:
        urlretrieve(url, str(dest))
    except Exception as e:
        raise RuntimeError(
            f"Failed to download {url}. Check your internet connection.\n"
            f"Original error: {e}"
        ) from e
    return dest


def download_tox21(data_dir: Path | str | None = None,
                   include_sparse: bool = True,
                   include_compound_data: bool = False) -> Path:
    """
    Download all required Tox21 files to data_dir.

    Parameters
    ----------
    data_dir : path-like, optional
        Where to store the files. Defaults to ``src/tox21/``.
    include_sparse : bool
        Whether to also download the (larger) sparse feature files.
    include_compound_data : bool
        Whether to download ``tox21_compoundData.csv``.

    Returns
    -------
    Path
        The directory containing downloaded files.
    """
    data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
    _ensure_dir(data_dir)

    keys_to_download = ["dense_train", "dense_test", "labels_train", "labels_test"]
    if include_sparse:
        keys_to_download += [
            "sparse_train", "sparse_test",
            "sparse_colnames", "sparse_rownames_train", "sparse_rownames_test",
        ]
    if include_compound_data:
        keys_to_download.append("compound_data")

    for key in keys_to_download:
        _download_file(_FILES[key], data_dir)

    logger.info("All Tox21 files ready in %s", data_dir)
    return data_dir


# ---------------------------------------------------------------------------
# Loading helpers
# ---------------------------------------------------------------------------

def _load_dense(path: Path) -> np.ndarray:
    """Load a gzipped dense-feature CSV and return a numpy array."""
    df = pd.read_csv(path, index_col=0, compression="gzip")
    return df.values.astype(np.float32)


def _load_sparse(path: Path):
    """Load a Matrix Market .mtx.gz file and return a scipy sparse matrix."""
    from scipy import io as spio
    return spio.mmread(str(path)).tocsc()


def _load_labels(path: Path) -> pd.DataFrame:
    """Load the label CSV. NaN indicates a missing assay result."""
    return pd.read_csv(path, index_col=0, compression="gzip")


def _filter_sparse_columns(X_sparse_train, X_sparse_test,
                            min_nonzero_frac: float = 0.05):
    """
    Keep only sparse columns where >*min_nonzero_frac* of training rows
    are non-zero (mirrors the JKU reference code).
    """
    col_mask = ((X_sparse_train > 0).mean(axis=0) > min_nonzero_frac).A.ravel()
    return X_sparse_train[:, col_mask], X_sparse_test[:, col_mask]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_tox21_data(
    assay: str = "NR-AR",
    use_sparse: bool = False,
    sparse_min_freq: float = 0.05,
    data_dir: Path | str | None = None,
    drop_na: bool = True,
):
    """
    Load Tox21 data ready for model training.

    Parameters
    ----------
    assay : str
        Which of the 12 toxicity assays to use as the target label.
        One of :data:`TOX21_ASSAYS`.
    use_sparse : bool
        If ``True``, combine the 801 dense features with the filtered
        sparse substructure features (~272 k raw, filtered by sparse_min_freq).
    sparse_min_freq : float
        Minimum fraction of non-zero training rows to keep a sparse column
        (default 5 %, same as the JKU reference code).
    data_dir : path-like, optional
        Override the default download/cache directory.
    drop_na : bool
        If ``True`` (default), rows where the chosen assay label is NaN
        are dropped.  If ``False``, NaN labels are kept (useful for
        semi-supervised approaches).

    Returns
    -------
    X_train : np.ndarray
        Training feature matrix.
    X_test : np.ndarray
        Test feature matrix.
    y_train : np.ndarray
        Binary training labels (0/1).
    y_test : np.ndarray
        Binary test labels (0/1).

    Raises
    ------
    ValueError
        If assay is not one of the 12 valid assay names.
    RuntimeError
        If downloads fail.

    Examples
    --------
    >>> X_train, X_test, y_train, y_test = load_tox21_data("NR-AR")
    >>> print(X_train.shape, y_train.shape)
    """
    # Validate assay name
    if assay not in TOX21_ASSAYS:
        raise ValueError(
            f"Unknown assay '{assay}'. Must be one of: {TOX21_ASSAYS}"
        )

    # 1. Ensure data is downloaded
    data_dir = download_tox21(
        data_dir=data_dir,
        include_sparse=use_sparse,
    )

    # 2. Load dense features
    logger.info("Loading dense features…")
    X_train_dense = _load_dense(data_dir / _FILES["dense_train"])
    X_test_dense  = _load_dense(data_dir / _FILES["dense_test"])

    # 3. Optionally combine with sparse features
    if use_sparse:
        logger.info("Loading sparse features…")
        X_train_sparse = _load_sparse(data_dir / _FILES["sparse_train"])
        X_test_sparse  = _load_sparse(data_dir / _FILES["sparse_test"])

        X_train_sparse, X_test_sparse = _filter_sparse_columns(
            X_train_sparse, X_test_sparse, min_nonzero_frac=sparse_min_freq,
        )
        logger.info("Sparse features filtered → %d columns kept", X_train_sparse.shape[1])

        X_train = np.hstack([X_train_dense, X_train_sparse.toarray()])
        X_test  = np.hstack([X_test_dense,  X_test_sparse.toarray()])
    else:
        X_train = X_train_dense
        X_test  = X_test_dense

    # 4. Load labels
    logger.info("Loading labels for assay '%s'…", assay)
    y_train_df = _load_labels(data_dir / _FILES["labels_train"])
    y_test_df  = _load_labels(data_dir / _FILES["labels_test"])

    col_name = _ASSAY_COL_MAP[assay]  # translate dash → dot
    y_train_series = y_train_df[col_name]
    y_test_series  = y_test_df[col_name]

    # 5. Handle missing labels
    if drop_na:
        train_mask = np.isfinite(y_train_series.values)
        test_mask  = np.isfinite(y_test_series.values)

        n_train_dropped = (~train_mask).sum()
        n_test_dropped  = (~test_mask).sum()
        if n_train_dropped or n_test_dropped:
            logger.info(
                "Dropped %d train / %d test rows with NaN labels for '%s'",
                n_train_dropped, n_test_dropped, assay,
            )

        X_train = X_train[train_mask]
        X_test  = X_test[test_mask]
        y_train = y_train_series.values[train_mask].astype(np.int8)
        y_test  = y_test_series.values[test_mask].astype(np.int8)
    else:
        y_train = y_train_series.values
        y_test  = y_test_series.values

    logger.info(
        "Loaded Tox21 [%s]: X_train=%s  X_test=%s  "
        "pos_train=%d  pos_test=%d",
        assay, X_train.shape, X_test.shape,
        (y_train == 1).sum() if drop_na else np.nansum(y_train == 1),
        (y_test == 1).sum()  if drop_na else np.nansum(y_test == 1),
    )

    return X_train, X_test, y_train, y_test


def load_compound_metadata(data_dir: Path | str | None = None) -> pd.DataFrame:
    """
    Load ``tox21_compoundData.csv`` which contains compound IDs,
    SMILES, and other metadata.

    Returns
    -------
    pd.DataFrame
    """
    data_dir = download_tox21(
        data_dir=data_dir,
        include_sparse=False,
        include_compound_data=True,
    )
    return pd.read_csv(data_dir / _FILES["compound_data"])


def dataset_summary(data_dir: Path | str | None = None) -> dict:
    """
    Return a dict summarising label availability across all 12 assays.

    Returns
    -------
    dict
        Keys are assay names; values are dicts with counts of
        ``active``, ``inactive``, and ``missing`` labels.
    """
    data_dir = download_tox21(data_dir=data_dir, include_sparse=False)
    y_train = _load_labels(data_dir / _FILES["labels_train"])
    y_test  = _load_labels(data_dir / _FILES["labels_test"])
    y_all = pd.concat([y_train, y_test])

    summary = {}
    for assay in TOX21_ASSAYS:
        col_name = _ASSAY_COL_MAP[assay]
        col = y_all[col_name]
        summary[assay] = {
            "active":   int((col == 1).sum()),
            "inactive": int((col == 0).sum()),
            "missing":  int(col.isna().sum()),
            "total":    len(col),
        }
    return summary
