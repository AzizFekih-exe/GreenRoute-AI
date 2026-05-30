from flask import Flask, request, jsonify
from orchestrator import Orchestrator
from flasgger import Swagger

app = Flask(__name__)
swagger = Swagger(app)

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
    """
    Health Check Endpoint
    ---
    responses:
      200:
        description: API is healthy
    """
    return jsonify({
        "status": "healthy",
        "service": "GreenRoute-AI Backend API"
    })

@app.route('/api/recommend', methods=['POST'])
def recommend():
    """
    Generate Solvent Recommendations
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          id: RecommendationRequest
          required:
            - target_smiles
          properties:
            target_smiles:
              type: string
              description: SMILES string of the target molecule
            weights:
              type: object
              description: Weights for different properties
            overrides:
              type: object
              description: Constraint overrides
    responses:
      200:
        description: A session with solvent recommendations
      400:
        description: Missing target_smiles
    """
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
    """
    Validate and Approve a Recommendation
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          id: ValidateRequest
          required:
            - session_id
            - solvent_name
          properties:
            session_id:
              type: string
              description: The session ID
            solvent_name:
              type: string
              description: Name of the solvent to approve
    responses:
      200:
        description: Successful validation
      400:
        description: Missing parameters or failed to approve
    """
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
    """
    Get Session State
    ---
    parameters:
      - name: session_id
        in: path
        type: string
        required: true
        description: The session ID
    responses:
      200:
        description: Session state details
      404:
        description: Session not found
    """
    state = orchestrator.get_session_state(session_id)
    if not state:
        return jsonify({"error": "Session not found"}), 404
    return jsonify(state)

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
