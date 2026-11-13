# RAG & Citation Rules

1. **LightRAG Offline Hybrid Indexing:**
   - Ingestion (`src/ingestion/build_index.py`) runs offline, parsing PDFs in `data/raw_pdfs/` into Markdown with preserved LaTeX equations and tables in `data/parsed_markdown/`.
   - Embeddings must run 100% on CPU using `BAAI/bge-small-en-v1.5` (`device="cpu"`).
   - Ingestion uses incremental SHA-256 checksum manifest to skip already-indexed documents.

2. **Free-Tier API Protection:**
   - Set `llm_model_max_async=1` and `chunk_token_size=1200` to minimize API calls and prevent rate limits.
   - Implement exponential backoff on HTTP 429 and automatic failover between Groq and Gemini.

3. **Verbatim Auditability:**
   - Retrieved citations must map to actual source documents (`14 CFR Part 23`, `19760003955.pdf`, etc.) and preserve exact sections and excerpts for display in the audit panel.

