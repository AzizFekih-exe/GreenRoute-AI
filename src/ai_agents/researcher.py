import os
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()
_api_key = os.environ.get("TAVILY_API_KEY")
tavily_client = TavilyClient(api_key=_api_key) if _api_key else None

def researcher(question: str) -> dict:
    """Searches the web via Tavily for up-to-date chemical/scientific information."""
    print("\n[RESEARCHER] Searching the web for updated information...")
    
    if not tavily_client:
        print("   [ERROR] Tavily API key not found. Skipping web search.")
        return {"success": False, "content": "", "sources": [], "error": "No API key"}

    try:
        search_query = f"{question} (chemistry OR biology OR tox21 OR pharmacology)"
        result = tavily_client.search(
            query=search_query,
            search_depth="basic",
            max_results=3,
            include_answer=True
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
