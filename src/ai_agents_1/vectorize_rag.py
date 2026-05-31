"""
Vectorize the RAG document and upload to Supabase.

Usage:
    python -m ai_agents_1.vectorize_rag

This script:
  1. Reads the PDF with PyMuPDF
  2. Chunks the text into ~500-char overlapping segments
  3. Embeds each chunk with FastEmbed (BAAI/bge-small-en-v1.5, 384-dim)
  4. Upserts everything into a Supabase `documents` table with pgvector
"""

import os
import hashlib
import fitz  # PyMuPDF
from fastembed import TextEmbedding
from dotenv import load_dotenv
from supabase import create_client

# ── Config ──────────────────────────────────────────────────────────
CHUNK_SIZE = 500       # characters per chunk
CHUNK_OVERLAP = 100    # overlap between chunks
TABLE_NAME = "documents"
PDF_PATH = os.path.join(os.path.dirname(__file__), "..", "_RAG document.pdf")

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


# ── Helpers ─────────────────────────────────────────────────────────
def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract all text from a PDF using PyMuPDF."""
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[dict]:
    """Split text into overlapping chunks with metadata."""
    # Clean up whitespace
    text = " ".join(text.split())
    
    chunks = []
    start = 0
    idx = 0
    while start < len(text):
        end = start + chunk_size
        chunk_content = text[start:end]
        
        # Try to break at a sentence boundary
        if end < len(text):
            last_period = chunk_content.rfind(". ")
            if last_period > chunk_size // 2:
                end = start + last_period + 1
                chunk_content = text[start:end]
        
        chunk_id = hashlib.md5(chunk_content.encode()).hexdigest()
        chunks.append({
            "id": chunk_id,
            "content": chunk_content.strip(),
            "chunk_index": idx,
        })
        start = end - overlap
        idx += 1
    
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Embed chunk texts using FastEmbed."""
    model = TextEmbedding()  # BAAI/bge-small-en-v1.5 (384-dim)
    texts = [c["content"] for c in chunks]
    embeddings = list(model.embed(texts))
    
    for chunk, emb in zip(chunks, embeddings):
        chunk["embedding"] = emb.tolist()
    
    return chunks


def upload_to_supabase(chunks: list[dict]):
    """Upsert chunks into the Supabase documents table."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
    
    client = create_client(url, key)
    
    # Upsert in batches of 50
    batch_size = 50
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        rows = [
            {
                "id": c["id"],
                "content": c["content"],
                "chunk_index": c["chunk_index"],
                "embedding": c["embedding"],
            }
            for c in batch
        ]
        client.table(TABLE_NAME).upsert(rows).execute()
        print(f"   Uploaded batch {i // batch_size + 1} ({len(batch)} chunks)")


# ── Main ────────────────────────────────────────────────────────────
def main():
    pdf_path = os.path.abspath(PDF_PATH)
    print(f"[VECTORIZE] Reading PDF: {pdf_path}")
    
    if not os.path.exists(pdf_path):
        print(f"   [ERROR] PDF not found at: {pdf_path}")
        return
    
    # 1. Extract
    text = extract_text_from_pdf(pdf_path)
    print(f"   Extracted {len(text)} characters from PDF")
    
    if not text.strip():
        print("   [ERROR] PDF is empty or unreadable")
        return
    
    # 2. Chunk
    chunks = chunk_text(text)
    print(f"   Split into {len(chunks)} chunks (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")
    
    # 3. Embed
    print("   Embedding chunks with FastEmbed...")
    chunks = embed_chunks(chunks)
    print(f"   Embedded {len(chunks)} chunks (dim={len(chunks[0]['embedding'])})")
    
    # 4. Upload
    print("   Uploading to Supabase...")
    upload_to_supabase(chunks)
    print(f"[VECTORIZE] ✅ Done! {len(chunks)} chunks stored in Supabase '{TABLE_NAME}' table.")


if __name__ == "__main__":
    main()
