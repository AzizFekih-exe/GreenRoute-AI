import sqlite3
import numpy as np
import os
import hashlib
import secrets
import datetime

try:
    from rdkit import Chem
    from rdkit.Chem import AllChem
except ImportError:
    Chem = None
    AllChem = None

try:
    import faiss
except ImportError:
    faiss = None

class SolventDatabase:
    def __init__(self, db_path="solvents.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._migrate_schema()
        self.create_tables()
        self.populate_default_solvents()
        self.build_faiss_index()

    def _migrate_schema(self):
        """Drop and recreate the solvents table if it was created with the old schema."""
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(solvents)")
        columns = [row[1] for row in cursor.fetchall()]
        if columns and "boiling_point" not in columns:
            cursor.execute("DROP TABLE IF EXISTS solvents")
            self.conn.commit()

        # Migrate sessions to add user_id column if it doesn't exist
        cursor.execute("PRAGMA table_info(sessions)")
        session_columns = [row[1] for row in cursor.fetchall()]
        if session_columns and "user_id" not in session_columns:
            try:
                cursor.execute("ALTER TABLE sessions ADD COLUMN user_id INTEGER REFERENCES users(id)")
                self.conn.commit()
            except sqlite3.OperationalError:
                pass

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS solvents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                smiles TEXT,
                toxicity REAL,            -- 0 to 1 (1 is highly toxic)
                voc REAL,                 -- 0 to 1 (1 is high VOC emissions)
                biodegradability REAL,    -- 0 to 1 (1 is highly biodegradable)
                recyclability REAL,       -- 0 to 1 (1 is highly recyclable)
                boiling_point REAL,       -- in °C
                heat_capacity REAL,       -- in J/g·K
                halogenated INTEGER,      -- 0 or 1
                data_source TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS synthesis_routes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_smiles TEXT,
                route_name TEXT,
                steps INTEGER,
                atom_economy REAL,
                e_factor_real REAL,
                description TEXT,
                data_source TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password_hash TEXT,
                salt TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_tokens (
                token TEXT PRIMARY KEY,
                user_id INTEGER,
                username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                target_smiles TEXT,
                weights_json TEXT,
                overrides_json TEXT,
                recommendations_json TEXT,
                approved INTEGER DEFAULT 0,
                approved_solvent TEXT,
                user_id INTEGER REFERENCES users(id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id),
                utc_timestamp TEXT,
                target_smiles TEXT,
                solvent_name TEXT,
                reaction_temperature REAL,
                weights_json TEXT,
                overrides_json TEXT,
                energy_demand REAL,
                green_score REAL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_experiments_user_time ON experiments(user_id, utc_timestamp DESC)")
        self.conn.commit()

    def populate_default_solvents(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM solvents")
        if cursor.fetchone()[0] == 0:
            solvents = [
                ("Water", "O", 0.0, 0.0, 1.0, 1.0, 100.0, 4.18, 0, "GreenRoute Solvent DB"),
                ("Ethanol", "CCO", 0.1, 0.4, 0.9, 0.8, 78.0, 2.44, 0, "GreenRoute Solvent DB"),
                ("Ethyl acetate", "CC(=O)OCC", 0.2, 0.5, 0.8, 0.7, 77.1, 1.92, 0, "GreenRoute Solvent DB"),
                ("Dichloromethane", "ClCCl", 0.8, 0.9, 0.05, 0.3, 39.6, 1.19, 1, "GreenRoute Solvent DB"),
                ("Hexane", "CCCCCC", 0.7, 0.8, 0.2, 0.5, 68.7, 2.27, 0, "GreenRoute Solvent DB"),
                ("Toluene", "Cc1ccccc1", 0.6, 0.7, 0.4, 0.6, 110.6, 1.70, 0, "GreenRoute Solvent DB"),
                ("Dimethylformamide", "CN(C)C=O", 0.9, 0.2, 0.3, 0.4, 153.0, 2.03, 0, "GreenRoute Solvent DB"),
                ("Cyclopentyl methyl ether", "CO[C@H]1CCCC1", 0.15, 0.3, 0.7, 0.9, 106.0, 1.80, 0, "GreenRoute Solvent DB"),
                ("2-Methyltetrahydrofuran", "CC1CCCO1", 0.2, 0.4, 0.6, 0.8, 80.2, 1.90, 0, "GreenRoute Solvent DB"),
                ("Ethyl lactate", "CCOC(=O)C(C)O", 0.05, 0.1, 0.95, 0.6, 154.0, 2.10, 0, "GreenRoute Solvent DB")
            ]
            cursor.executemany("""
                INSERT INTO solvents (name, smiles, toxicity, voc, biodegradability, recyclability, boiling_point, heat_capacity, halogenated, data_source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, solvents)
            self.conn.commit()

        cursor.execute("SELECT COUNT(*) FROM synthesis_routes")
        if cursor.fetchone()[0] == 0:
            routes = [
                ("ANY", "Direct Condensation (Classical)", 3, 45.2, 12.5, "Classical multi-step synthesis using stoichiometric reagents.", "GreenRoute DB"),
                ("ANY", "Catalytic Pathway (Optimised)", 2, 78.5, 4.2, "Uses a heterogeneous catalyst, eliminating one intermediate step.", "GreenRoute DB"),
                ("ANY", "Biocatalytic One-Pot (Green)", 1, 92.1, 1.1, "Enzymatic one-pot synthesis. Highly selective and minimal waste.", "GreenRoute DB")
            ]
            cursor.executemany("""
                INSERT INTO synthesis_routes (target_smiles, route_name, steps, atom_economy, e_factor_real, description, data_source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, routes)
            self.conn.commit()

    def get_synthesis_routes(self, target_smiles: str) -> list:
        cursor = self.conn.cursor()
        cursor.execute("SELECT route_name, steps, atom_economy, e_factor_real, description, data_source FROM synthesis_routes WHERE target_smiles = ? OR target_smiles = 'ANY' ORDER BY atom_economy DESC", (target_smiles,))
        routes = []
        for row in cursor.fetchall():
            routes.append({
                "route_name": row[0],
                "steps": row[1],
                "atom_economy": row[2],
                "e_factor_real": row[3],
                "description": row[4],
                "data_source": row[5]
            })
        return routes

    def get_all_solvents(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, smiles, toxicity, voc, biodegradability, recyclability, boiling_point, heat_capacity, halogenated, data_source FROM solvents")
        rows = cursor.fetchall()
        solvents = []
        for r in rows:
            solvents.append({
                "id": r[0],
                "name": r[1],
                "smiles": r[2],
                "toxicity": r[3],
                "voc": r[4],
                "biodegradability": r[5],
                "recyclability": r[6],
                "boiling_point": r[7],
                "heat_capacity": r[8],
                "halogenated": bool(r[9]),
                "data_source": r[10]
            })
        return solvents

    def build_faiss_index(self):
        if not Chem or not faiss:
            self.index = None
            self.indexed_ids = []
            return
        
        solvents = self.get_all_solvents()
        vectors = []
        self.indexed_ids = []
        
        for s in solvents:
            mol = Chem.MolFromSmiles(s["smiles"])
            if mol:
                fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=1024)
                arr = np.zeros((1,), dtype=np.int8)
                Chem.DataStructs.ConvertToNumpyArray(fp, arr)
                vectors.append(arr.astype(np.float32))
                self.indexed_ids.append(s["id"])
        
        if vectors:
            vectors_np = np.array(vectors)
            self.index = faiss.IndexFlatL2(1024)
            self.index.add(vectors_np)
        else:
            self.index = None

    def search_similar_solvents(self, query_smiles, k=3):
        if not Chem or not self.index or len(self.indexed_ids) == 0:
            # Fallback to returning top k solvents by list index
            return self.get_all_solvents()[:k]
            
        mol = Chem.MolFromSmiles(query_smiles)
        if not mol:
            return []
            
        fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=1024)
        arr = np.zeros((1,), dtype=np.int8)
        Chem.DataStructs.ConvertToNumpyArray(fp, arr)
        query_vector = np.array([arr.astype(np.float32)])
        
        distances, indices = self.index.search(query_vector, min(k, len(self.indexed_ids)))
        
        results = []
        cursor = self.conn.cursor()
        for idx in indices[0]:
            if idx == -1 or idx >= len(self.indexed_ids):
                continue
            db_id = self.indexed_ids[idx]
            cursor.execute("""
                SELECT id, name, smiles, toxicity, voc, biodegradability, recyclability, boiling_point, heat_capacity, halogenated, data_source
                FROM solvents WHERE id = ?
            """, (db_id,))
            r = cursor.fetchone()
            if r:
                results.append({
                    "id": r[0],
                    "name": r[1],
                    "smiles": r[2],
                    "toxicity": r[3],
                    "voc": r[4],
                    "biodegradability": r[5],
                    "recyclability": r[6],
                    "boiling_point": r[7],
                    "heat_capacity": r[8],
                    "halogenated": bool(r[9]),
                    "data_source": r[10]
                })
        return results

    def save_session(self, session_id, target_smiles, weights, overrides, recommendations, user_id=None):
        import json
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO sessions 
            (session_id, target_smiles, weights_json, overrides_json, recommendations_json, approved, approved_solvent, user_id)
            VALUES (?, ?, ?, ?, ?, 0, NULL, ?)
        """, (
            session_id,
            target_smiles,
            json.dumps(weights),
            json.dumps(overrides),
            json.dumps(recommendations),
            user_id
        ))
        self.conn.commit()

    def approve_session(self, session_id, solvent_name, user_id=None):
        cursor = self.conn.cursor()
        # Verify first if the session exists and if the solvent is in its recommendations list
        session = self.get_session(session_id)
        if not session:
            return False
        
        # Verify user matches
        if user_id is not None and session.get("user_id") != user_id:
            return False
        
        recommended_names = [r["name"] for r in session["recommendations"]]
        if solvent_name not in recommended_names:
            return False

        cursor.execute("""
            UPDATE sessions 
            SET approved = 1, approved_solvent = ? 
            WHERE session_id = ?
        """, (solvent_name, session_id))
        self.conn.commit()
        return True

    def get_session(self, session_id):
        import json
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT session_id, target_smiles, weights_json, overrides_json, recommendations_json, approved, approved_solvent, user_id
            FROM sessions WHERE session_id = ?
        """, (session_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "session_id": row[0],
            "target_smiles": row[1],
            "weights": json.loads(row[2]),
            "overrides": json.loads(row[3]),
            "recommendations": json.loads(row[4]),
            "approved": bool(row[5]),
            "approved_solvent": row[6],
            "user_id": row[7]
        }

    # --- Authentication Helpers ---

    def hash_password(self, password, salt=None):
        if not salt:
            salt = secrets.token_hex(16)
        pw_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex()
        return pw_hash, salt

    def create_user(self, username, password):
        cursor = self.conn.cursor()
        # Check if username already exists
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            return None
        
        pw_hash, salt = self.hash_password(password)
        try:
            cursor.execute("""
                INSERT INTO users (username, password_hash, salt)
                VALUES (?, ?, ?)
            """, (username, pw_hash, salt))
            self.conn.commit()
            user_id = cursor.lastrowid
            return {"id": user_id, "username": username}
        except sqlite3.IntegrityError:
            return None

    def check_user_credentials(self, username, password):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, username, password_hash, salt FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if not row:
            return None
        
        user_id, uname, stored_hash, salt = row
        computed_hash, _ = self.hash_password(password, salt)
        if computed_hash == stored_hash:
            return {"id": user_id, "username": uname}
        return None

    def create_user_token(self, user_id, username):
        token = secrets.token_hex(32)
        expires_at = (datetime.datetime.now() + datetime.timedelta(days=7)).isoformat()
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO user_tokens (token, user_id, username, expires_at)
            VALUES (?, ?, ?, ?)
        """, (token, user_id, username, expires_at))
        self.conn.commit()
        return token

    def verify_token(self, token):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT user_id, username, expires_at FROM user_tokens
            WHERE token = ?
        """, (token,))
        row = cursor.fetchone()
        if not row:
            return None
        
        user_id, username, expires_at = row
        if datetime.datetime.now() > datetime.datetime.fromisoformat(expires_at):
            # Clean up expired token
            self.delete_user_token(token)
            return None
            
        return {"id": user_id, "username": username}

    def delete_user_token(self, token):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM user_tokens WHERE token = ?", (token,))
        self.conn.commit()

    def log_experiment(self, user_id, utc_timestamp, target_smiles, solvent_name, reaction_temperature, weights_json, overrides_json, energy_demand, green_score):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO experiments (
                user_id, utc_timestamp, target_smiles, solvent_name, 
                reaction_temperature, weights_json, overrides_json, 
                energy_demand, green_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, utc_timestamp, target_smiles, solvent_name,
            reaction_temperature, weights_json, overrides_json,
            energy_demand, green_score
        ))
        self.conn.commit()
        return cursor.lastrowid

    def get_user_experiments(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, utc_timestamp, target_smiles, solvent_name, 
                   reaction_temperature, weights_json, overrides_json, 
                   energy_demand, green_score
            FROM experiments
            WHERE user_id = ?
            ORDER BY utc_timestamp DESC
        """, (user_id,))
        
        results = []
        import json
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "utc_timestamp": row[1],
                "target_smiles": row[2],
                "solvent_name": row[3],
                "reaction_temperature": row[4],
                "weights": json.loads(row[5]) if row[5] else {},
                "overrides": json.loads(row[6]) if row[6] else {},
                "energy_demand": row[7],
                "green_score": row[8]
            })
        return results

    def close(self):
        self.conn.close()
