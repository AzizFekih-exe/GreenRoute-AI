import numpy as np
from src.core.descriptors import get_all_descriptors

def predict_with_uncertainty(smiles, model, scaler, n_iterations=50):
    """Predict yield with confidence interval"""
    desc = get_all_descriptors(smiles)
    if not desc:
        return None, None
    
    # Extract numeric features
    numeric_desc = {k: v for k, v in desc.items() 
                   if isinstance(v, (int, float)) and not isinstance(v, np.ndarray)}
    features = np.array(list(numeric_desc.values())).reshape(1, -1)
    features_scaled = scaler.transform(features)
    
    # Monte Carlo predictions
    predictions = []
    for _ in range(n_iterations):
        # Add small noise to simulate dropout
        noise = np.random.normal(0, 0.01, features_scaled.shape)
        pred = model.predict(features_scaled + noise)[0]
        predictions.append(pred)
    
    mean_pred = np.mean(predictions)
    std_pred = np.std(predictions)
    
    return mean_pred, 1.96 * std_pred  # 95% confidence interval
