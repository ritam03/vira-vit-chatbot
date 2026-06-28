"""
VIRA - VIT Intelligent Regulation Assistant
RAG Pipeline Module with Model Cascade

This is the BRAIN of VIRA. It orchestrates the full RAG flow:
  1. Load the pre-built vector store
  2. Receive a user question
  3. Find the most relevant regulation chunks
  4. Send chunks + question to the best available Gemini model
  5. Return the answer with citations

MODEL CASCADE SYSTEM:
  Free tier gives ~20 requests/day per model.
  By using 7 models in a cascade, we get ~140 requests/day total.
  If a model is rate-limited (429), VIRA automatically falls back
  to the next model — transparent to the user.
"""

import os
import time
from pathlib import Path
from dotenv import load_dotenv
from typing import List, Tuple, Optional

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.messages import HumanMessage, AIMessage

from src.prompts import CHAT_PROMPT, CONDENSE_QUESTION_PROMPT

load_dotenv()

# ── Constants ──────────────────────────────────────────────────────────────────
VECTORSTORE_PATH = str(Path(__file__).parent.parent / "vectorstore" / "chroma_db")
EMBEDDING_MODEL  = "models/gemini-embedding-001"
TOP_K_RESULTS    = 5

# ── Model Cascade ──────────────────────────────────────────────────────────────
# Ordered from best quality → lightest fallback.
# Each model has its OWN independent free-tier quota (~20 RPD each).
# Total capacity: 7 models x 20 RPD = ~140 requests/day, all free.
MODEL_CASCADE = [
    "gemini-2.5-flash",       # Best quality  — 20 RPD free
    "gemini-3.5-flash",       # Latest series — 20 RPD free
    "gemini-2.5-flash-lite",  # Lighter 2.5   — 20 RPD free
    "gemini-2.0-flash",       # Proven stable — 20 RPD free
    "gemini-2.0-flash-lite",  # Lighter 2.0   — 20 RPD free
    "gemini-3.1-flash-lite",  # Lightweight   — 20 RPD free
    "gemini-flash-latest",    # Alias fallback — 20 RPD free
]

# ── Session-level quota tracker ────────────────────────────────────────────────
# Tracks which models have hit their DAILY limit in this session.
# Format: { "model_name": "daily" | "minute" }
# "daily"  = skip entirely for today
# "minute" = wait a bit then retry
_exhausted_models: dict = {}


def _is_quota_error(error: Exception) -> bool:
    """Check if an exception is a rate-limit/quota error."""
    err = str(error)
    return "429" in err or "RESOURCE_EXHAUSTED" in err or "quota" in err.lower()


def _is_daily_exhausted(error: Exception) -> bool:
    """Check if the error is a DAILY quota (not just per-minute)."""
    err = str(error)
    return (
        "GenerateRequestsPerDayPerProjectPerModel" in err
        or ("limit: 20" in err and "PerDay" in err)
        or ("limit: 0" in err)  # limit=0 means key has no quota for this model
    )


def _get_available_model(api_key: str) -> Optional[str]:
    """
    Find the first model in the cascade that isn't daily-exhausted.
    Returns None if all models are exhausted.
    """
    for model in MODEL_CASCADE:
        if _exhausted_models.get(model) == "daily":
            continue  # Skip models with daily quota exhausted
        return model
    return None


def _create_llm(model: str, api_key: str) -> ChatGoogleGenerativeAI:
    """Create a LangChain LLM instance for the given model."""
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=0.1,
        max_output_tokens=2048,
    )


def _build_chain(llm: ChatGoogleGenerativeAI, retriever) -> object:
    """Assemble the LangChain RAG pipeline for a given LLM."""
    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, CONDENSE_QUESTION_PROMPT
    )
    answer_chain = create_stuff_documents_chain(llm, CHAT_PROMPT)
    return create_retrieval_chain(history_aware_retriever, answer_chain)


class VIRAEngine:
    """
    The main RAG engine for VIRA with automatic model cascade.

    When a model hits its rate limit, the engine automatically
    falls back to the next model in MODEL_CASCADE — no user action needed.
    """

    def __init__(self):
        """Initialize the RAG engine: load embeddings and vector store."""
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "[ERROR] GOOGLE_API_KEY not found! "
                "Please create a .env file with your API key."
            )

        print("[*] Initializing VIRA Engine (with model cascade)...")

        # Load embedding model
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=EMBEDDING_MODEL,
            google_api_key=self.api_key
        )
        print("  [OK] Embedding model loaded")

        # Load vector store
        if not Path(VECTORSTORE_PATH).exists():
            raise FileNotFoundError(
                "[ERROR] Vector store not found! "
                "Please run: python scripts/ingest.py"
            )

        self.vectorstore = Chroma(
            persist_directory=VECTORSTORE_PATH,
            embedding_function=self.embeddings,
            collection_name="vit_regulations"
        )
        chunk_count = self.vectorstore._collection.count()
        print(f"  [OK] Vector store loaded ({chunk_count} chunks)")

        # Create retriever
        self.retriever = self.vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={"k": TOP_K_RESULTS, "fetch_k": TOP_K_RESULTS * 3},
        )
        print("  [OK] Retriever configured (MMR, top-5)")

        # Find the best available model to start with
        start_model = _get_available_model(self.api_key)
        if not start_model:
            raise RuntimeError("All models in the cascade are exhausted. Try again tomorrow.")

        self.current_model = start_model
        self.llm = _create_llm(self.current_model, self.api_key)
        self.rag_chain = _build_chain(self.llm, self.retriever)

        print(f"  [OK] LLM ready: {self.current_model}")
        print(f"  [OK] Cascade: {' -> '.join(MODEL_CASCADE)}")
        print("[*] VIRA Engine ready!")

    def _switch_to_next_model(self, failed_model: str, is_daily: bool) -> bool:
        """
        Mark failed_model as exhausted and rebuild the chain with the next model.
        Returns True if a fallback model was found, False if all are exhausted.

        For per-minute limits: we mark the model as exhausted and move on.
        Within seconds the quota resets, but to keep the user experience smooth
        we skip to the next model immediately rather than making the user wait.
        """
        # Always mark as "daily" so we don't loop back to same model this session
        _exhausted_models[failed_model] = "daily"
        limit_type = "daily limit" if is_daily else "minute limit (skipping)"
        print(f"  [FALLBACK] {failed_model} hit {limit_type}, trying next...")

        next_model = _get_available_model(self.api_key)
        if not next_model:
            return False

        self.current_model = next_model
        self.llm = _create_llm(self.current_model, self.api_key)
        self.rag_chain = _build_chain(self.llm, self.retriever)
        print(f"  [FALLBACK] Now using: {self.current_model}")
        return True

    def chat(
        self,
        question: str,
        chat_history: List[Tuple[str, str]] = None
    ) -> dict:
        """
        Process a student question and return VIRA's answer.
        Automatically falls back through the model cascade on rate limits.

        Returns:
            dict with keys:
              - 'answer':       VIRA's response text
              - 'sources':      List of regulation chunks used
              - 'model_used':   Which Gemini model answered the question
        """
        # Convert history to LangChain format
        formatted_history = []
        if chat_history:
            for human_msg, ai_msg in chat_history:
                formatted_history.append(HumanMessage(content=human_msg))
                formatted_history.append(AIMessage(content=ai_msg))

        payload = {"input": question, "chat_history": formatted_history}

        # Try models in cascade order until one succeeds
        attempts = 0
        last_error = None

        while attempts < len(MODEL_CASCADE):
            try:
                result = self.rag_chain.invoke(payload)

                # Success — extract sources and return
                sources = []
                if "context" in result:
                    for doc in result["context"]:
                        sources.append({
                            "content":  doc.page_content,
                            "source":   doc.metadata.get("source", "VIT Regulations"),
                            "chunk_id": doc.metadata.get("chunk_id", "N/A"),
                        })

                return {
                    "answer":     result["answer"],
                    "sources":    sources,
                    "model_used": self.current_model,
                }

            except Exception as e:
                last_error = e
                if _is_quota_error(e):
                    is_daily = _is_daily_exhausted(e)
                    switched = self._switch_to_next_model(self.current_model, is_daily)
                    if switched:
                        attempts += 1
                        continue  # Retry with new model immediately
                    else:
                        # All models exhausted
                        break
                else:
                    # Non-quota error — don't cascade, raise it
                    raise

        # All models failed
        raise ResourceWarning(
            "All free-tier Gemini models have reached their daily limit "
            f"({len(MODEL_CASCADE)} models tried). "
            "Quotas reset at midnight Pacific Time (~1:30 AM IST). "
            "Please try again tomorrow."
        )


# ── Singleton ──────────────────────────────────────────────────────────────────
_engine_instance = None

def get_engine() -> VIRAEngine:
    """Get or create the singleton VIRA engine instance."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = VIRAEngine()
    return _engine_instance
