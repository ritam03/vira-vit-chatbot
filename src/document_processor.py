"""
VIRA — VIT Intelligent Regulation Assistant
Document Processor Module

This module handles reading the VIT Regulations PDF and converting it into
searchable "chunks" that we store in our vector database.

LEARNING CONCEPT — Chunking:
Imagine the regulations document is a 200-page book. When a student asks
about attendance, we don't want to read the whole book — we want to jump
directly to the attendance section. Chunking breaks the book into ~500-word
pieces. Each piece gets a "fingerprint" (embedding). When a question arrives,
we find the pieces with the most similar fingerprints.
"""

import fitz  # PyMuPDF — the PDF reading library
import re
from pathlib import Path
from typing import List

from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter


def load_pdf(pdf_path: str) -> str:
    """
    Read all text from a PDF file.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Full text content of the PDF as a string
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found at: {pdf_path}")

    print(f"[...] Loading PDF: {pdf_path.name}")
    doc = fitz.open(str(pdf_path))

    full_text = []
    page_count = doc.page_count  # Save before closing
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        if text.strip():  # Skip empty pages
            # Add page marker so we can cite page numbers later
            full_text.append(f"\n--- Page {page_num} ---\n{text}")

    doc.close()
    raw_text = "\n".join(full_text)
    print(f"[OK] Loaded {page_count} pages, {len(raw_text):,} characters")
    return raw_text


def clean_text(text: str) -> str:
    """
    Clean the raw PDF text — remove artifacts, extra whitespace, etc.

    PDFs often have messy text when extracted: extra spaces, weird line breaks,
    headers/footers repeated on every page. This function cleans that up.
    """
    # Remove excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)  # Max 2 consecutive newlines
    text = re.sub(r' {2,}', ' ', text)       # Remove double spaces

    # Remove common PDF header/footer patterns (page numbers, watermarks)
    text = re.sub(r'Page \d+ of \d+', '', text)

    # Clean up hyphenated word breaks (PDF sometimes breaks words across lines)
    text = re.sub(r'-\n(\w)', r'\1', text)

    return text.strip()


def chunk_documents(text: str, source_name: str = "VIT Academic Regulations") -> List[Document]:
    """
    Split the document text into overlapping chunks for vector storage.

    LEARNING CONCEPT — Chunk Size & Overlap:
    - chunk_size=800: Each chunk is ~800 characters (~120-150 words)
    - chunk_overlap=150: Adjacent chunks share 150 characters
    
    Why overlap? If an answer spans two chunks (e.g., a rule spans a page break),
    the overlap ensures we don't miss it. The overlap creates "bridge" content.

    Args:
        text: The full cleaned document text
        source_name: Label for citation purposes

    Returns:
        List of LangChain Document objects ready for embedding
    """
    # RecursiveCharacterTextSplitter tries to split on natural boundaries:
    # First tries \n\n (paragraph breaks), then \n (line breaks), then spaces
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        separators=["\n\n", "\n", ". ", " ", ""],  # Order of preference for splitting
        length_function=len,
    )

    chunks = splitter.split_text(text)
    print(f"[OK] Split into {len(chunks)} chunks")

    # Wrap each chunk in a LangChain Document object with metadata
    # Metadata is crucial — it tells us WHERE the answer came from
    documents = []
    for i, chunk in enumerate(chunks):
        doc = Document(
            page_content=chunk,
            metadata={
                "source": source_name,
                "chunk_id": i,
                "total_chunks": len(chunks),
            }
        )
        documents.append(doc)

    return documents


def process_pdf(pdf_path: str) -> List[Document]:
    """
    Full pipeline: PDF → cleaned text → chunks → LangChain Documents

    This is the main function you call. It combines all the steps above.
    """
    raw_text = load_pdf(pdf_path)
    clean = clean_text(raw_text)
    documents = chunk_documents(clean)
    return documents
