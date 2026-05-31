import React, { useState } from 'react';
import './App.css';

function AuthPage({ onLogin, BACKEND_URL }) {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    const u = username.trim();
    const p = password.trim();
    if (!u || !p) {
      setError('Please fill in all fields.');
      return;
    }

    if (!isLogin && p.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }

    setLoading(true);
    const endpoint = isLogin ? '/api/auth/login' : '/api/auth/register';
    try {
      const res = await fetch(`${BACKEND_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: u, password: p })
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Authentication failed.');
      }
      onLogin(data);
    } catch (err) {
      setError(err.message || 'Connection to authentication server failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <span className="auth-logo">🧪</span>
        <h2>{isLogin ? 'Sign In to GreenRoute AI' : 'Create Account'}</h2>
        <p className="auth-subtitle">
          {isLogin 
            ? 'Access explainable green solvent optimization tools' 
            : 'Get started with green chemistry substitution recommendations'}
        </p>

        {error && <div className="alert alert-error" style={{ marginBottom: '20px' }}>⚠️ {error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input 
              type="text" 
              id="username" 
              className="form-input" 
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={loading}
              placeholder="e.g. chemist_smith"
              required 
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input 
              type="password" 
              id="password" 
              className="form-input" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              placeholder="••••••••"
              required 
            />
          </div>

          <button type="submit" className="btn-auth-submit" disabled={loading}>
            {loading ? 'Authenticating...' : isLogin ? 'Sign In' : 'Create Account'}
          </button>
        </form>

        <div className="auth-toggle-text">
          {isLogin ? "Don't have an account?" : "Already have an account?"}
          <button 
            type="button" 
            className="auth-toggle-link"
            onClick={() => {
              setIsLogin(!isLogin);
              setError('');
              setUsername('');
              setPassword('');
            }}
            disabled={loading}
          >
            {isLogin ? 'Sign Up' : 'Sign In'}
          </button>
        </div>
      </div>
    </div>
  );
}

const renderBoldText = (text) => {
  if (!text) return "";
  const parts = text.split(/(\*\*.*?\*\*)/g);
  return parts.map((part, idx) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={idx} style={{ color: "var(--accent-color)" }}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
};

const renderExplanationText = (text) => {
  if (!text) return null;
  
  let cleaned = text.trim();
  if (cleaned.startsWith('"') && cleaned.endsWith('"')) {
    cleaned = cleaned.slice(1, -1).trim();
  }
  
  const paragraphs = cleaned.split("\n\n");
  return paragraphs.map((para, pIdx) => {
    if (para.includes("Sources:") || para.includes("---")) {
      const lines = para.split("\n").filter(l => l.trim().length > 0);
      return (
        <div key={pIdx} className="explanation-sources" style={{ borderTop: "1px dashed rgba(255,255,255,0.08)", marginTop: "12px", paddingTop: "8px" }}>
          {lines.map((line, lIdx) => {
            const cleanLine = line.replace(/^[*\-\s•]+/, "").trim();
            if (cleanLine.includes("Sources:") || cleanLine.startsWith("---")) {
              if (cleanLine.startsWith("---")) return null;
              return <h5 key={lIdx} style={{ margin: "5px 0", color: "var(--accent-light)", fontSize: "0.85rem", fontWeight: "600" }}>{cleanLine}</h5>;
            }
            return <div key={lIdx} className="source-item" style={{ fontSize: "0.8rem", color: "var(--text-muted)", margin: "3px 0 3px 10px", wordBreak: "break-all" }}>• {cleanLine}</div>;
          })}
        </div>
      );
    }
    
    if (para.includes("\n-") || para.includes("\n*") || para.includes("\n•") || para.startsWith("- ") || para.startsWith("* ") || para.startsWith("• ")) {
      const lines = para.split("\n").filter(l => l.trim().length > 0);
      return (
        <ul key={pIdx} style={{ paddingLeft: "15px", margin: "8px 0", listStyleType: "disc" }}>
          {lines.map((line, lIdx) => {
            const cleanLine = line.replace(/^[*\-\s•]+/, "").trim();
            return <li key={lIdx} style={{ fontSize: "0.9rem", color: "var(--text-main)", marginBottom: "4px", lineHeight: "1.4" }}>{renderBoldText(cleanLine)}</li>;
          })}
        </ul>
      );
    }
    
    return (
      <p key={pIdx} className="explanation-paragraph" style={{ margin: "8px 0", lineHeight: "1.4", fontSize: "0.9rem", color: "#cbd5e0" }}>
        {renderBoldText(para)}
      </p>
    );
  });
};

function App() {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('greenroute_user');
    return saved ? JSON.parse(saved) : null;
  });
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
  const [activeTab, setActiveTab] = useState('optimization');
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [routes, setRoutes] = useState([]);
  const [routesLoading, setRoutesLoading] = useState(false);

  const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";

  const handleLogoutLocal = () => {
    setUser(null);
    localStorage.removeItem('greenroute_user');
    setSession(null);
    setApprovedSolvent(null);
  };

  const handleLogout = async () => {
    if (user && user.token) {
      try {
        await fetch(`${BACKEND_URL}/api/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${user.token}`
          }
        });
      } catch (err) {
        console.error("Failed to call logout API:", err);
      }
    }
    handleLogoutLocal();
  };

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
      const headers = { 'Content-Type': 'application/json' };
      if (user && user.token) {
        headers['Authorization'] = `Bearer ${user.token}`;
      }
      const res = await fetch(`${BACKEND_URL}/api/recommend`, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(payload)
      });
      if (res.status === 401) {
        handleLogoutLocal();
        throw new Error("Session expired. Please sign in again.");
      }
      if (!res.ok) {
        let errMsg = `Server returned error status: ${res.status}`;
        try {
          const errData = await res.json();
          if (errData && errData.error) {
            errMsg = errData.error;
          }
        } catch (e) {}
        throw new Error(errMsg);
      }
      const data = await res.json();
      setSession(data);
      if (data.target_smiles) {
        setTargetSmiles(data.target_smiles);
      }
      if (data.recommendations && data.recommendations.length > 0) {
        setSelectedForApprove(data.recommendations[0].name);
      }
    } catch (err) {
      setError(err.message || "Failed to connect to Flask backend API.");
    } finally {
      setLoading(false);
    }
  };

  const fetchHistory = async () => {
    setHistoryLoading(true);
    try {
      const headers = {};
      if (user && user.token) {
        headers['Authorization'] = `Bearer ${user.token}`;
      }
      const res = await fetch(`${BACKEND_URL}/api/v1/experiments/history`, { headers });
      if (res.ok) {
        const data = await res.json();
        setHistory(data.history || []);
      }
    } catch (err) {
      console.error('Failed to fetch history:', err);
    } finally {
      setHistoryLoading(false);
    }
  };

  const fetchRoutes = async (smilesQuery) => {
    setRoutesLoading(true);
    try {
      const headers = { 'Content-Type': 'application/json' };
      if (user && user.token) {
        headers['Authorization'] = `Bearer ${user.token}`;
      }
      const res = await fetch(`${BACKEND_URL}/api/routes`, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({ target_smiles: smilesQuery })
      });
      if (res.ok) {
        const data = await res.json();
        setRoutes(data.routes || []);
      }
    } catch (err) {
      console.error('Failed to fetch routes:', err);
    } finally {
      setRoutesLoading(false);
    }
  };

  const handleApprove = async () => {
    if (!session || !selectedForApprove) return;
    try {
      const headers = { 'Content-Type': 'application/json' };
      if (user && user.token) {
        headers['Authorization'] = `Bearer ${user.token}`;
      }
      const res = await fetch(`${BACKEND_URL}/api/validate`, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({
          session_id: session.session_id,
          solvent_name: selectedForApprove
        })
      });
      if (res.status === 401) {
        handleLogoutLocal();
        alert("Session expired. Please sign in again.");
        return;
      }
      if (res.ok) {
        setApprovedSolvent(selectedForApprove);

        // --- Event Interception: Log the experiment ---
        const approvedRec = session.recommendations.find(r => r.name === selectedForApprove);
        const experimentPayload = {
          utc_timestamp: new Date().toISOString(),
          target_smiles: targetSmiles,
          solvent_name: selectedForApprove,
          reaction_temperature: overrides.reaction_temperature,
          weights: weights,
          overrides: overrides,
          energy_demand: approvedRec ? approvedRec.energy_demand : null,
          green_score: approvedRec ? approvedRec.green_score : null
        };
        try {
          await fetch(`${BACKEND_URL}/api/v1/experiments`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(experimentPayload)
          });
        } catch (logErr) {
          console.error('Failed to log experiment:', logErr);
        }
      } else {
        const errorText = await res.text();
        alert(`Validation failed: ${errorText}`);
      }
    } catch (err) {
      alert(`Error submitting validation: ${err.message}`);
    }
  };

  if (!user) {
    return (
      <div className="app-container">
        <header className="app-header">
          <div className="app-header-container">
            <div>
              <h1 className="title-gradient">GreenRoute AI</h1>
              <p className="subtitle">
                An Explainable, Human-in-the-Loop System for Green Solvent Substitution & Synthesis Optimisation
              </p>
            </div>
          </div>
        </header>
        <AuthPage 
          BACKEND_URL={BACKEND_URL} 
          onLogin={(userData) => {
            setUser(userData);
            localStorage.setItem('greenroute_user', JSON.stringify(userData));
          }} 
        />
      </div>
    );
  }

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="app-header-container">
          <div>
            <h1 className="title-gradient">GreenRoute AI</h1>
            <p className="subtitle">
              An Explainable, Human-in-the-Loop System for Green Solvent Substitution & Synthesis Optimisation
            </p>
          </div>
          <div className="header-right">
            <div className="user-profile-badge">
              <div className="user-avatar">{user.username.charAt(0).toUpperCase()}</div>
              <span>👤 {user.username}</span>
            </div>
            <button onClick={handleLogout} className="btn-logout">
              Logout
            </button>
          </div>
        </div>
      </header>

      <div className="main-content">
        <aside className="sidebar">
          <div className="sidebar-nav">
            <button
              className={`sidebar-nav-btn ${activeTab === 'optimization' ? 'active' : ''}`}
              onClick={() => setActiveTab('optimization')}
            >
              🧪 Optimization
            </button>
            <button
              className={`sidebar-nav-btn ${activeTab === 'routes' ? 'active' : ''}`}
              onClick={() => { setActiveTab('routes'); fetchRoutes(targetSmiles); }}
            >
              🛣️ Synthesis Routes
            </button>
            <button
              className={`sidebar-nav-btn ${activeTab === 'history' ? 'active' : ''}`}
              onClick={() => { setActiveTab('history'); fetchHistory(); }}
            >
              📜 History
            </button>
          </div>

          {activeTab === 'optimization' && (<>
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
          </>)}
        </aside>

        <main className="dashboard-area">
          {activeTab === 'optimization' && (<>
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
                        <strong>{r.yield_info.predicted_yield}% ± {r.yield_info.uncertainty_std}%</strong>
                      </div>
                      <div className="metric-row">
                        <span>⚛️ Atom Economy:</span>
                        <strong>{r.atom_economy}%</strong>
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

                    <div className="explanation-text-container" style={{ margin: "15px 0", borderLeft: "2px solid var(--accent-color)", paddingLeft: "12px" }}>
                      {renderExplanationText(r.explanation)}
                    </div>
                    {r.ai_explanation && (
                      <details className="ai-explanation-accordion" style={{ margin: "10px 0", padding: "10px", background: "rgba(255,255,255,0.05)", borderRadius: "8px" }}>
                        <summary style={{ cursor: "pointer", fontWeight: "bold", color: "var(--accent-color)" }}>🤖 AI Deep-Dive Analysis</summary>
                        <div style={{ marginTop: "10px", fontSize: "0.9rem", lineHeight: "1.5" }}>
                          {renderExplanationText(r.ai_explanation)}
                        </div>
                      </details>
                    )}
                    <p className="yield-explanation-text" style={{ fontSize: "0.85rem", opacity: 0.8 }}>{r.yield_explanation}</p>
                    
                    <div className="card-footer">
                      <span className="source-tag">
                        Source: {r.data_source}
                        {' | '}
                        <a href={`https://pubchem.ncbi.nlm.nih.gov/#query=${encodeURIComponent(r.smiles)}`} target="_blank" rel="noreferrer" style={{color: "var(--accent-color)"}}>View on PubChem</a>
                      </span>
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
          </>)}

          {activeTab === 'routes' && (
            <section className="routes-section">
              <h2 className="history-title">🛣️ Synthesis Route Optimisation</h2>
              <p className="history-subtitle">Ranked alternative synthesis pathways for target <code>{targetSmiles}</code>, optimized for Atom Economy and E-factor.</p>
              {routesLoading ? (
                <div className="history-loading">Analyzing chemical pathways...</div>
              ) : routes.length === 0 ? (
                <div className="history-empty">
                  <span className="history-empty-icon">🔬</span>
                  <p>No routes found for this molecule.</p>
                </div>
              ) : (
                <div className="cards-grid">
                  {routes.map((rt, idx) => (
                    <div key={idx} className="glass-card recommendation-card">
                      <div className="badge rank-badge">Rank {idx + 1}</div>
                      <h3 className="solvent-name">{rt.route_name}</h3>
                      <p style={{marginTop: "5px", fontSize: "0.9rem", color: "var(--text-muted)"}}>{rt.description}</p>
                      
                      <div className="metrics-box" style={{marginTop: "15px"}}>
                        <div className="metric-row">
                          <span>Ranking Score:</span>
                          <strong className="score-val">{rt.ranking_score ?? 'N/A'}/100</strong>
                        </div>
                        <div className="metric-row">
                          <span>⚛️ Atom Economy:</span>
                          <strong style={{color: "var(--accent-color)"}}>{rt.atom_economy}%</strong>
                        </div>
                        <div className="metric-row">
                          <span>🗑️ Real E-factor:</span>
                          <strong>{rt.e_factor_real}</strong>
                        </div>
                        <div className="metric-row">
                          <span>🔄 Reaction Steps:</span>
                          <strong>{rt.steps}</strong>
                        </div>
                      </div>
                      
                      <div style={{marginTop: "15px", padding: "12px", background: "rgba(0, 255, 135, 0.05)", borderRadius: "8px", borderLeft: "3px solid var(--accent-color)"}}>
                        <div style={{fontSize: "0.82rem", lineHeight: "1.45", padding: "10px", background: "rgba(0,0,0,0.18)", borderRadius: "6px"}}>
                          <strong style={{color: "var(--accent-color)"}}>Why this rank?</strong>
                          <div><strong>Calculation:</strong> {rt.ranking_formula || 'Not available'}</div>
                          {rt.score_components && (
                            <div style={{marginTop: "6px"}}>
                              Components: AE={rt.score_components.atom_economy_normalized}, E-factor={rt.score_components.e_factor_normalized}, Steps={rt.score_components.steps_normalized}
                            </div>
                          )}
                          <div style={{marginTop: "6px"}}>
                            <strong>Argument:</strong> {rt.ranking_argument || 'This route is ranked from atom economy, E-factor, and step-count trade-offs.'}
                          </div>
                        </div>
                      </div>
                      <div className="card-footer">
                        <span className="source-tag">Source: {rt.data_source}</span>
                      </div>
                    </div>
                  ))}
                  <div className="route-ranking-note">
                    <p>
                      <strong>Scoring formula:</strong> Ranking score = 45% atom economy + 40% E-factor reduction + 15% step reduction. Lower E-factor and fewer steps are normalized so the best route gets 1.000 and the worst gets 0.000.
                    </p>
                    <p>
                      <strong>Interpretation:</strong> Routes are not ranked by description text. They are ranked by the weighted score shown on each card, where high atom economy keeps more reactant mass in the product, low E-factor means less waste per product mass, and fewer steps reduce handling, purification, and energy burden.
                    </p>
                  </div>
                </div>
              )}
            </section>
          )}

          {activeTab === 'history' && (
            <section className="history-section">
              <h2 className="history-title">📜 Experiment Validation History</h2>
              <p className="history-subtitle">All validated solvent selections, logged with full experimental context.</p>
              {historyLoading ? (
                <div className="history-loading">Loading history...</div>
              ) : history.length === 0 ? (
                <div className="history-empty">
                  <span className="history-empty-icon">🧫</span>
                  <p>No experiments validated yet.</p>
                  <p className="text-muted">Run an optimization search and approve a solvent to start building your experiment log.</p>
                </div>
              ) : (
                <div className="history-timeline">
                  {history.map((exp, idx) => (
                    <div key={exp.id} className="history-card glass-card">
                      <div className="history-card-header">
                        <span className="history-index">#{history.length - idx}</span>
                        <span className="history-timestamp">
                          {new Date(exp.utc_timestamp).toLocaleString()}
                        </span>
                      </div>
                      <div className="history-card-body">
                        <div className="history-detail">
                          <span className="history-label">🧪 Target Molecule</span>
                          <code className="smiles-code">{exp.target_smiles}</code>
                        </div>
                        <div className="history-detail">
                          <span className="history-label">✅ Approved Solvent</span>
                          <strong className="history-solvent-name">{exp.solvent_name}</strong>
                        </div>
                        <div className="history-metrics">
                          <div className="history-metric">
                            <span>🌡️ Temp</span>
                            <strong>{exp.reaction_temperature}°C</strong>
                          </div>
                          {exp.energy_demand != null && (
                            <div className="history-metric">
                              <span>⚡ Energy</span>
                              <strong className="energy-val">{exp.energy_demand} kJ</strong>
                            </div>
                          )}
                          {exp.green_score != null && (
                            <div className="history-metric">
                              <span>🌿 Green Score</span>
                              <strong className="score-val">{exp.green_score}</strong>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
