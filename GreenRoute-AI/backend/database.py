import sqlite3
import numpy as np
import os

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
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                target_smiles TEXT,
                weights_json TEXT,
                overrides_json TEXT,
                recommendations_json TEXT,
                approved INTEGER DEFAULT 0,
                approved_solvent TEXT
            )
        """)
        self.conn.commit()

    def populate_default_solvents(self):
        # (name, smiles, tox, voc, bio, rec, boiling_point, heat_capacity, halogenated, source)
        default_solvents = [
            ("Dimethylformamide", "CN(C)C=O", 0.9, 0.8, 0.1, 0.2, 153.0, 2.14, 0, "PubChem"),
            ("Dichloromethane", "ClCCl", 0.85, 0.95, 0.05, 0.4, 39.6, 1.20, 1, "ECHA"),
            ("Hexane", "CCCCCC", 0.7, 0.9, 0.2, 0.3, 68.0, 2.26, 0, "ECHA"),
            ("Toluene", "Cc1ccccc1", 0.6, 0.7, 0.5, 0.5, 110.6, 1.70, 0, "PubChem"),
            ("Cyclopentyl methyl ether", "COC1CCCC1", 0.15, 0.3, 0.8, 0.7, 106.0, 1.96, 0, "Literature"),
            ("Ethyl lactate", "CCOC(=O)C(C)O", 0.05, 0.1, 0.95, 0.6, 154.0, 2.01, 0, "Literature"),
            ("2-Methyltetrahydrofuran", "CC1CCCO1", 0.2, 0.35, 0.75, 0.7, 80.2, 1.98, 0, "Literature"),
            ("Ethanol", "CCO", 0.1, 0.4, 0.9, 0.8, 78.0, 2.44, 0, "PubChem"),
            ("Water", "O", 0.0, 0.0, 1.0, 1.0, 100.0, 4.18, 0, "USPTO")
        ]
        cursor = self.conn.cursor()
        for name, smiles, tox, voc, bio, rec, bp, hc, halo, source in default_solvents:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO solvents 
                    (name, smiles, toxicity, voc, biodegradability, recyclability, boiling_point, heat_capacity, halogenated, data_source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (name, smiles, tox, voc, bio, rec, bp, hc, halo, source))
            except sqlite3.Error:
                pass
        self.conn.commit()

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

    def save_session(self, session_id, target_smiles, weights, overrides, recommendations):
        import json
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO sessions 
            (session_id, target_smiles, weights_json, overrides_json, recommendations_json, approved, approved_solvent)
            VALUES (?, ?, ?, ?, ?, 0, NULL)
        """, (
            session_id,
            target_smiles,
            json.dumps(weights),
            json.dumps(overrides),
            json.dumps(recommendations)
        ))
        self.conn.commit()

    def approve_session(self, session_id, solvent_name):
        cursor = self.conn.cursor()
        # Verify first if the session exists and if the solvent is in its recommendations list
        session = self.get_session(session_id)
        if not session:
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
            SELECT session_id, target_smiles, weights_json, overrides_json, recommendations_json, approved, approved_solvent
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
            "approved_solvent": row[6]
        }

    def close(self):
        self.conn.close()
