"""
VIRA — VIT Intelligent Regulation Assistant
RAG Pipeline Module

This is the BRAIN of VIRA. It orchestrates the full Retrieval-Augmented Generation flow:
  1. Load the pre-built vector store
  2. Receive a user question
  3. Find the most relevant regulation chunks
  4. Send chunks + question to Gemini
  5. Return the answer with citations

LEARNING CONCEPT — What is RAG?
Traditional chatbots (like base ChatGPT) only know what they were trained on.
RAG solves this by:
  - Storing your specific documents (VIT regulations) in a searchable database
  - At query time, FINDING the relevant pieces and GIVING them to the LLM
  - The LLM then answers based on YOUR documents, not its training data
This means:
  ✅ Accurate, regulation-specific answers
  ✅ No hallucinations about VIT-specific rules
  ✅ Easy to update when regulations change (just re-ingest the new PDF)
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import List, Tuple

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.messages import HumanMessage, AIMessage

from src.prompts import CHAT_PROMPT, CONDENSE_QUESTION_PROMPT

# Load environment variables from .env file
load_dotenv()

# ─── Constants ────────────────────────────────────────────────────────────────
VECTORSTORE_PATH = str(Path(__file__).parent.parent / "vectorstore" / "chroma_db")
EMBEDDING_MODEL = "models/gemini-embedding-001"  # Google's free embedding model
LLM_MODEL = "gemini-2.5-flash"                    # Best available model with active quota
TOP_K_RESULTS = 5  # How many regulation chunks to retrieve per query


class VIRAEngine:
    """
    The main RAG engine for VIRA.

    This class encapsulates the entire chatbot logic. You create one instance
    at startup and reuse it for all conversations (efficient — avoids reloading).
    """

    def __init__(self):
        """Initialize the RAG engine: load embeddings, vector store, and LLM."""
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "[ERROR] GOOGLE_API_KEY not found! "
                "Please create a .env file with your API key. "
                "See .env.example for the format."
            )

        print("[*] Initializing VIRA Engine...")

        # STEP 1: Initialize the Embedding Model
        # Embeddings convert text → numbers (vectors) so we can do math on meaning
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=EMBEDDING_MODEL,
            google_api_key=api_key
        )
        print("  [OK] Embedding model loaded")

        # STEP 2: Load the Vector Store (pre-built ChromaDB)
        # This is where all the regulation chunks live, as searchable vectors
        if not Path(VECTORSTORE_PATH).exists():
            raise FileNotFoundError(
                "[ERROR] Vector store not found! "
                "Please run: python scripts/ingest.py\n"
                "This will process the PDF and build the vector database."
            )

        self.vectorstore = Chroma(
            persist_directory=VECTORSTORE_PATH,
            embedding_function=self.embeddings,
            collection_name="vit_regulations"  # Must match what ingest.py used
        )
        print(f"  [OK] Vector store loaded ({self.vectorstore._collection.count()} chunks)")

        # STEP 3: Create the Retriever
        # The retriever is the "search engine" part — given a question, find top-K chunks
        self.retriever = self.vectorstore.as_retriever(
            search_type="mmr",  # MMR = Maximum Marginal Relevance (diversity-aware retrieval)
            search_kwargs={
                "k": TOP_K_RESULTS,
                "fetch_k": TOP_K_RESULTS * 3,  # Fetch 3x more, then pick diverse ones
            }
        )
        print("  [OK] Retriever configured (MMR, top-5)")

        # STEP 4: Initialize the LLM (Gemini 1.5 Flash)
        self.llm = ChatGoogleGenerativeAI(
            model=LLM_MODEL,
            google_api_key=api_key,
            temperature=0.1,      # Low temperature = more factual, less creative
            max_output_tokens=2048,
        )
        print("  [OK] Gemini 2.0 Flash LLM initialized")

        # STEP 5: Build the RAG Chain
        # This is the "assembly line" that connects retriever + LLM + prompts
        self._build_chain()
        print("  [OK] RAG chain assembled")
        print("[*] VIRA Engine ready!")

    def _build_chain(self):
        """
        Assemble the LangChain RAG pipeline.

        The pipeline has two main stages:
        Stage A — History-Aware Retriever:
            If user asks "What about arrears?", this stage uses the chat history
            to rephrase it as "What are the arrear regulations at VIT?" before
            searching the vector store. This makes follow-up questions work correctly.

        Stage B — Retrieval + Answer Chain:
            Takes the retrieved chunks, formats them into the system prompt,
            and asks Gemini to generate the answer.
        """
        # Stage A: Rephrase follow-up questions using conversation history
        history_aware_retriever = create_history_aware_retriever(
            self.llm,
            self.retriever,
            CONDENSE_QUESTION_PROMPT
        )

        # Stage B: Combine retrieved docs with the question → answer
        answer_chain = create_stuff_documents_chain(self.llm, CHAT_PROMPT)

        # Full pipeline: question → retrieve → answer
        self.rag_chain = create_retrieval_chain(history_aware_retriever, answer_chain)

    def chat(
        self,
        question: str,
        chat_history: List[Tuple[str, str]] = None
    ) -> dict:
        """
        Process a student question and return VIRA's answer.

        Args:
            question: The student's question as a string
            chat_history: List of (human_message, ai_message) tuples from previous turns

        Returns:
            dict with keys:
              - 'answer': VIRA's response text
              - 'sources': List of regulation chunks that were used
        """
        # Convert history from our simple format to LangChain's message format
        formatted_history = []
        if chat_history:
            for human_msg, ai_msg in chat_history:
                formatted_history.append(HumanMessage(content=human_msg))
                formatted_history.append(AIMessage(content=ai_msg))

        # Run the RAG chain
        result = self.rag_chain.invoke({
            "input": question,
            "chat_history": formatted_history
        })

        # Extract source documents for citation display
        sources = []
        if "context" in result:
            for doc in result["context"]:
                sources.append({
                    "content": doc.page_content,
                    "source": doc.metadata.get("source", "VIT Regulations"),
                    "chunk_id": doc.metadata.get("chunk_id", "N/A"),
                })

        return {
            "answer": result["answer"],
            "sources": sources,
        }


# ─── Singleton Pattern ────────────────────────────────────────────────────────
# We use a singleton to avoid reloading the model on every Streamlit rerun.
# Streamlit reruns the script on every interaction, but @st.cache_resource
# (used in app.py) keeps this instance alive in memory.
_engine_instance = None

def get_engine() -> VIRAEngine:
    """Get or create the singleton VIRA engine instance."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = VIRAEngine()
    return _engine_instance
