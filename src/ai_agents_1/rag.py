"""
RAG retrieval module — queries Supabase for semantically similar document chunks.
Uses FastEmbed for query embedding, Supabase's match_documents RPC for search.
"""

import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Lazy-loaded singletons
_embed_model = None
_supabase_client = None


def _get_embed_model():
    global _embed_model
    if _embed_model is None:
        from fastembed import TextEmbedding
        _embed_model = TextEmbedding()  # BAAI/bge-small-en-v1.5, 384-dim
    return _embed_model


def _get_supabase():
    global _supabase_client
    if _supabase_client is None:
        from supabase import create_client
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
        _supabase_client = create_client(url, key)
    return _supabase_client


def retrieve(query: str, top_k: int = 5, threshold: float = 0.5) -> list[dict]:
    """
    Embed the query and retrieve the top-k most similar chunks from Supabase.

    Returns a list of dicts: [{"content": str, "similarity": float, "chunk_index": int}, ...]
    """
    # 1. Embed the query
    model = _get_embed_model()
    query_embedding = list(model.embed([query]))[0].tolist()

    # 2. Call Supabase RPC
    client = _get_supabase()
    response = client.rpc("match_documents", {
        "query_embedding": query_embedding,
        "match_count": top_k,
        "match_threshold": threshold,
    }).execute()

    results = response.data or []
    return [
        {
            "content": r["content"],
            "similarity": round(r["similarity"], 4),
            "chunk_index": r["chunk_index"],
        }
        for r in results
    ]


def retrieve_as_context(query: str, top_k: int = 5, threshold: float = 0.5) -> str:
    """
    Retrieve relevant chunks and format them as a single context string
    ready to be injected into an LLM prompt.
    """
    try:
        results = retrieve(query, top_k=top_k, threshold=threshold)
    except (ImportError, ValueError) as exc:
        print(f"   [RAG SKIPPED] {exc}")
        return ""

    if not results:
        return ""

    parts = []
    for i, r in enumerate(results, 1):
        parts.append(f"[Document Chunk {i} | Relevance: {r['similarity']:.0%}]\n{r['content']}")

    return "\n\n---\n\n".join(parts)
