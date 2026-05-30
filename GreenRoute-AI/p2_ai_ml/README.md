# AI & Machine Learning Workspace (P2)

Welcome to the AI/ML Engineer workspace!

## Your Tasks:
1. **Build Yield Prediction Models**: Implement the Random Forest algorithm using RDKit computational descriptors (e.g., LogP, Molecular Weight, charge states) as inputs.
2. **Implement Uncertainty Quantification**: Formulate the Monte Carlo dropout standard deviation estimator running 50 forward passes on the yield prediction network.
3. **Build Solvent Similarity Search**: Construct the FAISS index using RDKit Morgan fingerprints (radius=2, nBits=1024) to calculate solvent proximity metrics.
4. **Train Toxicity Classifier**: Train the QSAR classifier to predict the likelihood of solvent toxicity flags based on structural smiles features.

## Recommended Folder Layout:
- `models/`: Store your serialized models (e.g., joblib/pickle files).
- `src/`: Code for descriptor calculations, model architectures, and FAISS creation.
- `notebooks/`: Jupyter notebooks for data analysis, exploration, and model validation.
