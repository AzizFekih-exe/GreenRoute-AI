from flask import Flask, request, jsonify
from orchestrator import Orchestrator

app = Flask(__name__)

@app.after_request
def add_cors_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Initialize decision engine orchestrator
orchestrator = Orchestrator()

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "service": "GreenRoute-AI Backend API"
    })

@app.route('/api/recommend', methods=['POST'])
def recommend():
    data = request.get_json() or {}
    target_smiles = data.get("target_smiles")
    if not target_smiles:
        return jsonify({"error": "Missing target_smiles parameter"}), 400
        
    weights = data.get("weights", {
        "toxicity": 0.3,
        "voc": 0.2,
        "biodegradability": 0.3,
        "recyclability": 0.2
    })
    
    overrides = data.get("overrides", {})
    
    try:
        session = orchestrator.generate_recommendations(target_smiles, weights, overrides)
        return jsonify(session)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/validate', methods=['POST'])
def validate():
    data = request.get_json() or {}
    session_id = data.get("session_id")
    solvent_name = data.get("solvent_name")
    
    if not session_id or not solvent_name:
        return jsonify({"error": "Missing session_id or solvent_name parameter"}), 400
        
    success = orchestrator.approve_recommendation(session_id, solvent_name)
    if success:
        return jsonify(orchestrator.get_session_state(session_id))
    else:
        return jsonify({"error": "Failed to approve. Validate session_id and solvent_name."}), 400

@app.route('/api/session/<session_id>', methods=['GET'])
def get_session(session_id):
    state = orchestrator.get_session_state(session_id)
    if not state:
        return jsonify({"error": "Session not found"}), 404
    return jsonify(state)

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
