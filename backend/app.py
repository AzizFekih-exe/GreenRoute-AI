from flask import Flask, request, jsonify
from functools import wraps
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

# Authentication Middleware
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid token"}), 401
            
        token = auth_header.split(" ")[1]
        user = orchestrator.db.verify_token(token)
        if not user:
            return jsonify({"error": "Invalid or expired token"}), 401
            
        request.user = user
        return f(*args, **kwargs)
    return decorated

@app.route('/api/auth/register', methods=['POST'])
def register():
    """
    Register a new user
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          properties:
            username:
              type: string
            password:
              type: string
    responses:
      200:
        description: Successful registration
      400:
        description: Registration failed
    """
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400
        
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters long"}), 400

    user = orchestrator.db.create_user(username, password)
    if not user:
        return jsonify({"error": "Username already exists"}), 400
        
    token = orchestrator.db.create_user_token(user["id"], user["username"])
    return jsonify({
        "message": "User registered successfully",
        "token": token,
        "username": username
    }), 200

@app.route('/api/auth/login', methods=['POST'])
def login():
    """
    Login user and return token
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          properties:
            username:
              type: string
            password:
              type: string
    responses:
      200:
        description: Successful login
      401:
        description: Invalid credentials
    """
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400
        
    user = orchestrator.db.check_user_credentials(username, password)
    if not user:
        return jsonify({"error": "Invalid username or password"}), 401
        
    token = orchestrator.db.create_user_token(user["id"], user["username"])
    return jsonify({
        "token": token,
        "username": username
    }), 200

@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout():
    """
    Logout current user
    ---
    responses:
      200:
        description: Logged out successfully
    """
    auth_header = request.headers.get("Authorization")
    token = auth_header.split(" ")[1]
    orchestrator.db.delete_user_token(token)
    return jsonify({"message": "Logged out successfully"}), 200

@app.route('/api/auth/me', methods=['GET'])
@require_auth
def me():
    """
    Get current user details
    ---
    responses:
      200:
        description: User details
    """
    return jsonify({
        "user_id": request.user["id"],
        "username": request.user["username"]
    }), 200

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
@require_auth
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
        session = orchestrator.generate_recommendations(target_smiles, weights, overrides, user_id=request.user["id"])
        return jsonify(session)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/validate', methods=['POST'])
@require_auth
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
        
    success = orchestrator.approve_recommendation(session_id, solvent_name, user_id=request.user["id"])
    if success:
        return jsonify(orchestrator.get_session_state(session_id))
    else:
        return jsonify({"error": "Failed to approve. Validate session_id and solvent_name."}), 400

@app.route('/api/v1/experiments', methods=['POST'])
@require_auth
def log_experiment():
    """
    Log an experimental validation event
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          properties:
            target_smiles:
              type: string
            solvent_name:
              type: string
            reaction_temperature:
              type: number
            weights:
              type: object
            overrides:
              type: object
            energy_demand:
              type: number
            green_score:
              type: number
            utc_timestamp:
              type: string
    responses:
      200:
        description: Logged successfully
      400:
        description: Missing parameters
    """
    data = request.get_json() or {}
    import json
    try:
        exp_id = orchestrator.db.log_experiment(
            user_id=request.user["id"],
            utc_timestamp=data.get("utc_timestamp"),
            target_smiles=data.get("target_smiles"),
            solvent_name=data.get("solvent_name"),
            reaction_temperature=data.get("reaction_temperature"),
            weights_json=json.dumps(data.get("weights", {})),
            overrides_json=json.dumps(data.get("overrides", {})),
            energy_demand=data.get("energy_demand"),
            green_score=data.get("green_score")
        )
        return jsonify({"message": "Experiment logged", "experiment_id": exp_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/experiments/history', methods=['GET'])
@require_auth
def get_experiments_history():
    """
    Get experimental validation history
    ---
    responses:
      200:
        description: List of experiments
    """
    try:
        history = orchestrator.db.get_user_experiments(request.user["id"])
        return jsonify({"history": history}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/session/<session_id>', methods=['GET'])
@require_auth
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
    if state.get("user_id") is not None and state.get("user_id") != request.user["id"]:
        return jsonify({"error": "Unauthorized to access this session"}), 403
    return jsonify(state)

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
