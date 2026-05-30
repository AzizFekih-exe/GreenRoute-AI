# Training data (SMILES of reactants + products or solvents)
reactant_smiles = ["CCO", "CC=O", "c1ccccc1", "CC(C)=O"]
yields = [85, 72, 91, 68]  # reaction yields

X, valid_idx = prepare_features_from_smiles(reactant_smiles)
y = np.array(yields)[valid_idx]


# Train model
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_scaled, y)

# Save model
joblib.dump(model, 'yield_predictor.pkl')
joblib.dump(scaler, 'scaler.pkl')
# Example
yield_pred, ci = predict_with_uncertainty("CCO", model, scaler)
print(f"Predicted yield: {yield_pred:.1f}% ± {ci:.1f}%")

# Example solvent database
solvents = {
    "ethanol": "CCO",
    "toluene": "Cc1ccccc1", 
    "water": "O",
    "DMF": "CN(C)C=O",
    "dichloromethane": "C(Cl)Cl"
}

index, solvent_names, solvent_smiles = create_solvent_database(solvents)
# Test
similar = find_similar_solvents("CCOC", k=3)  # diethyl ether

# Test
ranked = rank_solvents(solvents)
for r in ranked:
    print(f"{r['name']}: {r['green_score']:.3f}")