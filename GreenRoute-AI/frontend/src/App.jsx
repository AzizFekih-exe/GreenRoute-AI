import React, { useState } from 'react';
import './App.css';

function App() {
  const [targetSmiles, setTargetSmiles] = useState('CC(=O)O');
  const [weights, setWeights] = useState({
    toxicity: 0.3,
    voc: 0.2,
    biodegradability: 0.3,
    recyclability: 0.2,
  });
  const [overrides, setOverrides] = useState({
    exclude_toxic: false,
    exclude_halogenated: false,
    reaction_temperature: 80,
    force_solvent: '',
  });
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [approvedSolvent, setApprovedSolvent] = useState(null);
  const [selectedForApprove, setSelectedForApprove] = useState('');

  const BACKEND_URL = "http://localhost:5000";

  const handleWeightChange = (key, val) => {
    setWeights(prev => ({
      ...prev,
      [key]: parseFloat(val)
    }));
  };

  const handleRecommend = async () => {
    setLoading(true);
    setError(null);
    setApprovedSolvent(null);
    
    // Normalise weights on submission
    const sum = weights.toxicity + weights.voc + weights.biodegradability + weights.recyclability;
    const normSum = sum > 0 ? sum : 1.0;
    const normalizedWeights = {
      toxicity: weights.toxicity / normSum,
      voc: weights.voc / normSum,
      biodegradability: weights.biodegradability / normSum,
      recyclability: weights.recyclability / normSum
    };

    const payload = {
      target_smiles: targetSmiles,
      weights: normalizedWeights,
      overrides: {
        exclude_toxic: overrides.exclude_toxic,
        exclude_halogenated: overrides.exclude_halogenated,
        reaction_temperature: overrides.reaction_temperature,
        force_solvent: overrides.force_solvent.trim() || undefined
      }
    };

    try {
      const res = await fetch(`${BACKEND_URL}/api/recommend`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        throw new Error(`Server returned error status: ${res.status}`);
      }
      const data = await res.json();
      setSession(data);
      if (data.recommendations && data.recommendations.length > 0) {
        setSelectedForApprove(data.recommendations[0].name);
      }
    } catch (err) {
      setError(err.message || "Failed to connect to Flask backend API.");
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async () => {
    if (!session || !selectedForApprove) return;
    try {
      const res = await fetch(`${BACKEND_URL}/api/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: session.session_id,
          solvent_name: selectedForApprove
        })
      });
      if (res.ok) {
        setApprovedSolvent(selectedForApprove);
      } else {
        const errorText = await res.text();
        alert(`Validation failed: ${errorText}`);
      }
    } catch (err) {
      alert(`Error submitting validation: ${err.message}`);
    }
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h1 className="title-gradient">GreenRoute AI</h1>
        <p className="subtitle">
          An Explainable, Human-in-the-Loop System for Green Solvent Substitution & Synthesis Optimisation
        </p>
      </header>

      <div className="main-content">
        <aside className="sidebar">
          <div className="sidebar-section">
            <h3>🎛️ Optimization Weights</h3>
            <div className="control-group">
              <label>Toxicity Penalty: {weights.toxicity.toFixed(2)}</label>
              <input 
                type="range" min="0" max="1" step="0.05" 
                value={weights.toxicity} 
                onChange={(e) => handleWeightChange('toxicity', e.target.value)} 
              />
            </div>
            <div className="control-group">
              <label>VOC Emissions: {weights.voc.toFixed(2)}</label>
              <input 
                type="range" min="0" max="1" step="0.05" 
                value={weights.voc} 
                onChange={(e) => handleWeightChange('voc', e.target.value)} 
              />
            </div>
            <div className="control-group">
              <label>Biodegradability: {weights.biodegradability.toFixed(2)}</label>
              <input 
                type="range" min="0" max="1" step="0.05" 
                value={weights.biodegradability} 
                onChange={(e) => handleWeightChange('biodegradability', e.target.value)} 
              />
            </div>
            <div className="control-group">
              <label>Recyclability: {weights.recyclability.toFixed(2)}</label>
              <input 
                type="range" min="0" max="1" step="0.05" 
                value={weights.recyclability} 
                onChange={(e) => handleWeightChange('recyclability', e.target.value)} 
              />
            </div>
          </div>

          <div className="sidebar-section">
            <h3>⚙️ Parameters</h3>
            <div className="checkbox-group">
              <input 
                type="checkbox" id="ex-tox"
                checked={overrides.exclude_toxic}
                onChange={(e) => setOverrides(prev => ({ ...prev, exclude_toxic: e.target.checked }))}
              />
              <label htmlFor="ex-tox">Exclude Highly Toxic (&gt;0.5)</label>
            </div>
            <div className="checkbox-group">
              <input 
                type="checkbox" id="ex-halo"
                checked={overrides.exclude_halogenated}
                onChange={(e) => setOverrides(prev => ({ ...prev, exclude_halogenated: e.target.checked }))}
              />
              <label htmlFor="ex-halo">Exclude Halogenated Solvents</label>
            </div>
            <div className="control-group" style={{ marginTop: '15px' }}>
              <label>🌡️ Reaction Temperature: {overrides.reaction_temperature}°C</label>
              <input 
                type="range" min="20" max="200" step="5" 
                value={overrides.reaction_temperature} 
                onChange={(e) => setOverrides(prev => ({ ...prev, reaction_temperature: parseInt(e.target.value) }))}
              />
            </div>
            <div className="control-group" style={{ marginTop: '15px' }}>
              <label>Force Solvent Option:</label>
              <input 
                type="text" placeholder="e.g. CPME" 
                value={overrides.force_solvent}
                onChange={(e) => setOverrides(prev => ({ ...prev, force_solvent: e.target.value }))}
                className="input-text"
              />
            </div>
          </div>
        </aside>

        <main className="dashboard-area">
          <section className="search-section card">
            <h2>🧪 Molecule Optimization Search</h2>
            <div className="search-bar">
              <input 
                type="text" 
                placeholder="Enter target molecule SMILES or Common Name (e.g. CC(=O)O)" 
                value={targetSmiles}
                onChange={(e) => setTargetSmiles(e.target.value)}
                className="search-input"
              />
              <button onClick={handleRecommend} disabled={loading} className="btn-primary">
                {loading ? 'Analyzing...' : 'Analyze & Rank'}
              </button>
            </div>
          </section>

          {error && <div className="alert alert-error">⚠️ {error}</div>}

          {session && (
            <div className="results-container">
              <div className="session-token">
                Active Session Token: <code>{session.session_id}</code>
              </div>

              <div className="cards-grid">
                {session.recommendations.map((r, idx) => (
                  <div key={idx} className="glass-card recommendation-card">
                    <div className="badge rank-badge">Rank {idx + 1}</div>
                    <h3 className="solvent-name">{r.name}</h3>
                    <code className="smiles-code">{r.smiles}</code>
                    
                    <div className="metrics-box">
                      <div className="metric-row">
                        <span>Green Score:</span>
                        <strong className="score-val">{r.green_score}</strong>
                      </div>
                      <div className="metric-row">
                        <span>Predicted Yield:</span>
                        <strong>{r.yield_info.predicted_yield}%</strong>
                      </div>
                      <div className="metric-row">
                        <span>Confidence Bounds:</span>
                        <span>{r.yield_info.confidence_interval[0]}% - {r.yield_info.confidence_interval[1]}%</span>
                      </div>
                      <div className="metric-row">
                        <span>🌡️ Boiling Point:</span>
                        <strong>{r.boiling_point}°C</strong>
                      </div>
                      <div className="metric-row">
                        <span>⚡ Energy Demand:</span>
                        <strong className="energy-val">{r.energy_demand} kJ</strong>
                      </div>
                      {r.halogenated && (
                        <div className="metric-row halogenated-flag">
                          <span>☣️ Halogenated:</span>
                          <strong>Yes</strong>
                        </div>
                      )}
                    </div>

                    <p className="explanation-text">"{r.explanation}"</p>
                    <p className="yield-explanation-text">{r.yield_explanation}</p>
                    
                    <div className="card-footer">
                      <span className="source-tag">Source: {r.data_source}</span>
                    </div>

                    {r.warnings && r.warnings.map((w, wIdx) => (
                      <div key={wIdx} className="warning-item">⚠️ {w}</div>
                    ))}
                  </div>
                ))}
              </div>

              <section className="hitl-section card">
                <h2>🤝 Human-in-the-Loop Validation</h2>
                {approvedSolvent ? (
                  <div className="alert alert-success">
                    🎉 <strong>Validation Confirmed</strong>: Solvent <strong>{approvedSolvent}</strong> approved and logged for synthesis of target <code>{targetSmiles}</code>!
                  </div>
                ) : (
                  <div className="validation-controls">
                    <div className="selector-wrapper">
                      <label>Select solvent option to log approval:</label>
                      <select 
                        value={selectedForApprove} 
                        onChange={(e) => setSelectedForApprove(e.target.value)}
                        className="solvent-select"
                      >
                        {session.recommendations.map((r, idx) => (
                          <option key={idx} value={r.name}>{r.name}</option>
                        ))}
                      </select>
                    </div>
                    <button onClick={handleApprove} className="btn-approve">
                      Approve for Experiment
                    </button>
                  </div>
                )}
              </section>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
