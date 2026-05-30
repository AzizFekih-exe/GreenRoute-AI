import os
import json
from dotenv import load_dotenv
from groq import Groq

# Attempt to import some local helpers to provide constraints/context
try:
    from src.core.descriptors import get_all_descriptors
    from src.ml.similarity import structural_similarity
except ImportError:
    pass

load_dotenv()
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def gatekeeper(question: str) -> dict:
    """Decides if the question is relevant to chemoinformatics, chemistry, or biology."""
    print("\n[GATEKEEPER] Evaluating question relevance...")
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": """You are the relevance gatekeeper for a Chemoinformatics AI assistant.
The assistant helps users analyze molecules, query Tox21 datasets, calculate molecular properties, and find chemical data online.
Your ONLY job is to determine if the user's question is TOPICALLY related to:
- Chemistry, chemoinformatics, biology, pharmacology
- Toxicity, solubility, molecular properties (e.g., LogP, descriptors)
- Machine learning applied to drug discovery
- Tox21 dataset or similar scientific datasets
- General scientific explanations

CRITICAL RULES:
1. ONLY evaluate TOPIC RELEVANCE. 
2. DO NOT try to answer the question yourself.
3. Allow ANY question related to chemistry, molecules, datasets, RDKit, or AI in science.
4. If a user provides a SMILES string (like CCO, c1ccccc1), ALWAYS allow it.
5. Refuse completely unrelated topics (like baking a cake, general politics, movie reviews, sports). 
   Note: It does not have to be too strict. If there's a slight science/tech angle, allow it.

Respond ONLY with valid JSON (no markdown, no extra text):
{"allowed": true, "reason": "..."}
or
{"allowed": false, "reason": "..."}
"""
                },
                {"role": "user", "content": question}
            ]
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())
        status = "ALLOWED" if result.get("allowed") else "BLOCKED"
        print(f"   [{status}] — {result.get('reason', '')}")
        return result
    except Exception as e:
        print(f"    Gatekeeper error: {e}")
        return {"allowed": True, "reason": "Gatekeeper failed – defaulting to allow.", "error": str(e)}
