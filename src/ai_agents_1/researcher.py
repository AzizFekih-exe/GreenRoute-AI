import os
import re
from dotenv import load_dotenv
from tavily import TavilyClient
from .utils import extract_smiles

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
_api_key = os.environ.get("TAVILY_API_KEY")
tavily_client = TavilyClient(api_key=_api_key) if _api_key else None

PRIORITY_DOMAINS = [
    "pubchem.ncbi.nlm.nih.gov",
    "chemspider.com",
    "drugbank.com",
    "nature.com",
    "sciencedirect.com",
    "acs.org",
    "rsc.org",
    "wikipedia.org"
]

def researcher(question: str) -> dict:
    """Searches the web via Tavily, prioritizing high-authority scientific domains."""
    print("\n[RESEARCHER] Searching high-authority scientific domains...")
    
    if not tavily_client:
        print("   [ERROR] Tavily API key not found. Skipping web search.")
        return {"success": False, "content": "", "sources": [], "error": "No API key"}

    smiles = extract_smiles(question)
    query_context = f"molecule {smiles}" if smiles else ""

    try:
        # Build a short search query from key terms to stay under Tavily's 400-char limit.
        solvent_match = re.search(r"why\s+([\w\s\-]+?)\s+\(SMILES", question, re.IGNORECASE)
        target_match = re.search(r"compound '([^']+)'", question, re.IGNORECASE)
        ref_match = re.search(r"over\s+([\w\s]+)\s+for\s+reactions", question, re.IGNORECASE)
        solvent_name = solvent_match.group(1).strip() if solvent_match else ""
        target_name = target_match.group(1).strip() if target_match else ""
        ref_name = ref_match.group(1).strip() if ref_match else "DCM"

        if solvent_name and target_name:
            search_query = f"green solvent {solvent_name} vs {ref_name} for {target_name} green chemistry toxicity biodegradability"
        else:
            # Fallback: truncate the raw question + context
            search_query = f"{question} {query_context} chemistry toxicity properties"[:380]

        search_query = search_query[:390]  # Hard cap

        result = tavily_client.search(
            query=search_query,
            search_depth="advanced",
            max_results=4,
            include_answer=True,
            include_domains=PRIORITY_DOMAINS 
        )

        web_answer = result.get("answer", "")
        web_results = result.get("results", [])

        if not web_results and not web_answer:
            return {"success": False, "content": "", "sources": [], "error": "No web results found."}

        content_parts = []
        sources = []
        if web_answer:
            content_parts.append(f"Web Summary: {web_answer}")
        for r in web_results:
            content_parts.append(f"• {r.get('title','')}: {r.get('content','')[:400]}")
            sources.append(r.get("url", ""))

        print(f"   [SUCCESS] Found {len(web_results)} web results.")
        return {"success": True, "content": "\n\n".join(content_parts), "sources": sources}

    except Exception as e:
        print(f"   [ERROR] Researcher error: {e}")
        return {"success": False, "content": "", "sources": [], "error": str(e)}
