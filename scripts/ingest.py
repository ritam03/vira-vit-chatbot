"""
VIRA - VIT Intelligent Regulation Assistant
Document Ingestion Script (Optimized - ~5 min total)

Run this ONCE to process the VIT regulations PDF and build the vector database.

Usage:
    python scripts/ingest.py

Rate limit strategy:
  - Free tier: 100 embed requests/minute
  - We send 50 chunks/batch, wait 65s between batches
  - 187 chunks = 4 batches = ~4 minutes total
  - Skips already-embedded chunks if resuming
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent.parent))
load_dotenv()

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from src.document_processor import process_pdf

# --- Configuration ---
PDF_PATH = Path(__file__).parent.parent / "data" / "vit_regulations.pdf"
VECTORSTORE_PATH = str(Path(__file__).parent.parent / "vectorstore" / "chroma_db")
EMBEDDING_MODEL = "models/gemini-embedding-001"
BATCH_SIZE = 50        # 50 chunks per batch (well under 100/min limit)
BATCH_DELAY = 65       # 65 seconds between batches (resets the rate limit window)


def embed_batch_with_retry(vectorstore, batch, label, max_retries=5):
    """Embed a batch, auto-retrying on 429 rate-limit errors."""
    for attempt in range(1, max_retries + 1):
        try:
            vectorstore.add_documents(batch)
            return
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err or "quota" in err.lower():
                wait = 70  # Default wait
                if "retry in" in err.lower():
                    try:
                        part = err.lower().split("retry in")[1].strip()
                        wait = int(float(part.split("s")[0].strip())) + 15
                    except Exception:
                        pass
                print(f"\n   [Rate limit hit] Attempt {attempt}/{max_retries} for {label}")
                print(f"   Auto-waiting {wait}s...", end="", flush=True)
                time.sleep(wait)
                print(" retrying now")
            else:
                raise


def main():
    print("=" * 60)
    print("  VIRA - Document Ingestion (Optimized ~5 min)")
    print("=" * 60)

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("[ERROR] GOOGLE_API_KEY not found!")
        sys.exit(1)
    print("[OK] API key found")

    if not PDF_PATH.exists():
        print(f"[ERROR] PDF not found at: {PDF_PATH}")
        sys.exit(1)
    print(f"[OK] PDF: {PDF_PATH.name}")

    # Process PDF
    print("\n[...] Processing PDF...")
    documents = process_pdf(str(PDF_PATH))
    total = len(documents)
    print(f"[OK] {total} chunks ready")

    # Init embeddings
    print(f"\n[...] Initializing {EMBEDDING_MODEL}...")
    embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL, google_api_key=api_key)
    print("[OK] Embeddings ready")

    # Open/create vector store
    vectorstore = Chroma(
        persist_directory=VECTORSTORE_PATH,
        embedding_function=embeddings,
        collection_name="vit_regulations"
    )

    # Check what's already embedded (resume support)
    already_done = vectorstore._collection.count()
    if already_done > 0:
        print(f"\n[INFO] Found {already_done} chunks already embedded. Resuming from chunk {already_done + 1}...")
        documents = documents[already_done:]

    if not documents:
        print("[OK] All chunks already embedded! Nothing to do.")
        print(f"   Total in DB: {vectorstore._collection.count()}")
        print("\n[DONE] Run the chatbot:  streamlit run app.py\n")
        return

    remaining = len(documents)
    total_batches = (remaining + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"\n[...] Embedding {remaining} chunks in {total_batches} batch(es) of {BATCH_SIZE}")
    print(f"   Est. time: ~{max(1, (total_batches - 1) * BATCH_DELAY // 60)}m {(max(0, (total_batches - 1)) * BATCH_DELAY) % 60}s\n")

    start = time.time()
    for i in range(0, remaining, BATCH_SIZE):
        batch = documents[i: i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        label = f"Batch {batch_num}/{total_batches}"
        end_chunk = already_done + i + len(batch)

        print(f"   [{label}] embedding chunks {already_done + i + 1}-{end_chunk}...", end="", flush=True)
        embed_batch_with_retry(vectorstore, batch, label)
        print(f" done  (total in DB: {vectorstore._collection.count()})")

        if i + BATCH_SIZE < remaining:
            print(f"   Pausing {BATCH_DELAY}s for rate limit reset...")
            time.sleep(BATCH_DELAY)

    elapsed = int(time.time() - start)
    final_count = vectorstore._collection.count()

    print(f"\n[OK] Done! {final_count} chunks in vector store")
    print(f"   Time taken: {elapsed // 60}m {elapsed % 60}s")
    print("\n" + "=" * 60)
    print("  [DONE] Launch VIRA:  streamlit run app.py")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
