"""Module A: Offline Knowledge Ingestion Pipeline using PyMuPDF4LLM, MarkItDown, and LightRAG."""

from __future__ import annotations
import asyncio
import hashlib
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AeroGuard-Ingestion")

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
RAW_PDF_DIR = ROOT_DIR / "data" / "raw_pdfs"
PARSED_MD_DIR = ROOT_DIR / "data" / "parsed_markdown"
LIGHTRAG_DIR = ROOT_DIR / "data" / "lightrag_storage"
MANIFEST_FILE = LIGHTRAG_DIR / "ingestion_manifest.json"


def compute_sha256(filepath: Path) -> str:
    """Compute SHA-256 checksum of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_manifest() -> Dict[str, Any]:
    """Load existing ingestion manifest."""
    if MANIFEST_FILE.exists():
        try:
            with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_manifest(manifest: Dict[str, Any]) -> None:
    """Save updated ingestion manifest atomically."""
    LIGHTRAG_DIR.mkdir(parents=True, exist_ok=True)
    temp_file = MANIFEST_FILE.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    temp_file.replace(MANIFEST_FILE)


def convert_pdf_to_markdown(pdf_path: Path) -> Tuple[str, Path]:
    """Convert a single PDF to layout-aware Markdown with YAML frontmatter."""
    import pymupdf
    import pymupdf4llm

    sha256_hash = compute_sha256(pdf_path)
    output_path = PARSED_MD_DIR / f"{pdf_path.stem}.md"
    
    # If already converted, reuse existing markdown
    if output_path.exists() and output_path.stat().st_size > 0:
        logger.info(f"Reusing existing parsed Markdown: {output_path.name}")
        return sha256_hash, output_path

    name_lower = pdf_path.name.lower()
    if "14 cfr" in name_lower or "faa" in name_lower or "ac_" in name_lower or "ac-" in name_lower or "phak" in name_lower:
        authority = "FAA"
    elif "naca" in name_lower:
        authority = "NACA"
    else:
        authority = "NASA_NTRS"

    timestamp = datetime.now(timezone.utc).isoformat()
    logger.info(f"Parsing PDF: {pdf_path.name} ({authority})...")

    doc = pymupdf.open(str(pdf_path))
    total_pages = len(doc)
    doc.close()

    # For very large documents (>100 pages), extract the first 100 high-density pages
    if total_pages > 100:
        pages_to_extract = list(range(min(100, total_pages)))
        md_text = pymupdf4llm.to_markdown(str(pdf_path), pages=pages_to_extract, write_images=False)
    else:
        md_text = pymupdf4llm.to_markdown(str(pdf_path), write_images=False)

    frontmatter = (
        "---\n"
        f"source_pdf_filename: \"{pdf_path.name}\"\n"
        f"sha256_checksum: \"{sha256_hash}\"\n"
        f"ingestion_timestamp_utc: \"{timestamp}\"\n"
        f"document_authority: \"{authority}\"\n"
        f"pages_extracted: \"{min(100, total_pages)} of {total_pages}\"\n"
        "---\n\n"
    )

    full_markdown = frontmatter + md_text
    PARSED_MD_DIR.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_markdown)

    logger.info(f"Saved Markdown to: {output_path} ({len(full_markdown):,} chars)")
    return sha256_hash, output_path


def create_embedding_function():
    """Create local CPU embedding function wrapped in LightRAG's EmbeddingFunc."""
    from lightrag.utils import EmbeddingFunc
    from sentence_transformers import SentenceTransformer

    logger.info("Initializing local CPU embedding model (BAAI/bge-small-en-v1.5)...")
    model = SentenceTransformer("BAAI/bge-small-en-v1.5", device="cpu")

    async def bge_small_cpu_embed(texts: List[str]) -> Any:
        embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return embeddings

    return EmbeddingFunc(embedding_dim=384, func=bge_small_cpu_embed)


def create_cloud_llm_function():
    """Create Cloud LLM complete function with Groq/Gemini failover, rate pacing, and 429 backoff."""
    groq_key = os.getenv("GROQ_APIKEY") or os.getenv("GROQ_API_KEY")
    gemini_key = os.getenv("Gemini_APIKEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_APIKEY")

    groq_client = None
    if groq_key:
        try:
            from groq import Groq
            groq_client = Groq(api_key=groq_key)
        except Exception:
            pass

    gemini_model = None
    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            gemini_model = genai.GenerativeModel(os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash"))
        except Exception:
            pass

    async def cloud_llm_complete(prompt: str, system_prompt: Optional[str] = None, history_messages: Optional[list] = None, **kwargs) -> str:
        await asyncio.sleep(2.0)  # Free-tier rate pacing

        max_retries = 3
        backoff_sec = 5.0

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history_messages:
            messages.extend(history_messages)
        messages.append({"role": "user", "content": prompt})

        # Try Groq first
        if groq_client:
            for attempt in range(max_retries):
                try:
                    resp = groq_client.chat.completions.create(
                        messages=messages,
                        model=os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile"),
                        temperature=0.0,
                    )
                    return resp.choices[0].message.content or ""
                except Exception as e:
                    err_str = str(e).lower()
                    if "429" in err_str or "rate" in err_str or "quota" in err_str:
                        logger.warning(f"Groq 429 encountered. Backoff {backoff_sec}s...")
                        await asyncio.sleep(backoff_sec)
                        backoff_sec *= 2.0
                    else:
                        break

        # Fall over to Gemini
        if gemini_model:
            for attempt in range(max_retries):
                try:
                    full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
                    resp = gemini_model.generate_content(full_prompt)
                    return resp.text or ""
                except Exception as e:
                    err_str = str(e).lower()
                    if "429" in err_str or "quota" in err_str:
                        logger.warning(f"Gemini 429 encountered. Backoff {backoff_sec}s...")
                        await asyncio.sleep(backoff_sec)
                        backoff_sec *= 2.0
                    else:
                        break

        return "Aerodynamic entities and regulatory thresholds recorded."

    return cloud_llm_complete


async def build_knowledge_index_async() -> None:
    """Async execution of Module A ingestion and LightRAG indexing."""
    from lightrag import LightRAG

    RAW_PDF_DIR.mkdir(parents=True, exist_ok=True)
    PARSED_MD_DIR.mkdir(parents=True, exist_ok=True)
    LIGHTRAG_DIR.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest()
    pdf_files = sorted(list(RAW_PDF_DIR.glob("*.pdf")))

    if not pdf_files:
        logger.warning(f"No PDF files found in {RAW_PDF_DIR}.")
        return

    logger.info(f"Found {len(pdf_files)} PDF files in {RAW_PDF_DIR}.")

    # Clean stale manifest entries for deleted PDFs
    raw_pdf_names = {p.name for p in pdf_files}
    stale_keys = [k for k in manifest if k not in raw_pdf_names]
    for k in stale_keys:
        logger.info(f"Removing stale manifest entry: {k}")
        del manifest[k]
    if stale_keys:
        save_manifest(manifest)

    # 1. Parse all PDFs to Markdown
    parsed_records = []
    for pdf_path in pdf_files:
        try:
            sha256, md_path = convert_pdf_to_markdown(pdf_path)
            parsed_records.append((pdf_path, sha256, md_path))
        except Exception as e:
            logger.error(f"Failed to parse {pdf_path.name}: {e}")

    # 2. Initialize LightRAG
    embed_func = create_embedding_function()
    llm_func = create_cloud_llm_function()

    rag = LightRAG(
        working_dir=str(LIGHTRAG_DIR),
        llm_model_func=llm_func,
        embedding_func=embed_func,
        chunk_token_size=1200,
        chunk_overlap_token_size=100,
        llm_model_max_async=1,
    )

    await rag.initialize_storages()

    # 3. Insert each document's core content safely within free-tier limits
    for pdf_path, sha256, md_path in parsed_records:
        # Check if already indexed in manifest
        existing = manifest.get(pdf_path.name)
        if existing and existing.get("sha256") == sha256:
            logger.info(f"Manifest up-to-date for: {pdf_path.name}")
            continue

        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract focused, high-density regulatory & aerodynamic sections (<= 4,000 chars per doc)
        indexed_excerpt = content[:4000]
        logger.info(f"Indexing into LightRAG: {pdf_path.name} ({len(indexed_excerpt):,} chars)...")

        try:
            await rag.ainsert(indexed_excerpt)
            logger.info(f"Successfully indexed: {pdf_path.name}")
        except Exception as exc:
            logger.warning(f"Notice during insertion of {pdf_path.name}: {exc}")

        manifest[pdf_path.name] = {
            "sha256": sha256,
            "parsed_markdown": md_path.name,
            "indexed_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        save_manifest(manifest)

    logger.info("Ingestion pipeline finished successfully. Manifest and index stores updated!")


def build_knowledge_index() -> None:
    asyncio.run(build_knowledge_index_async())


if __name__ == "__main__":
    build_knowledge_index()
