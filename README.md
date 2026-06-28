# 🎓 VIRA — VIT Intelligent Regulation Assistant

> An AI-powered chatbot that answers student questions about VIT Academic Regulations using RAG (Retrieval-Augmented Generation).

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://ritam03-vira-vit-chatbot-app.streamlit.app)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![Gemini](https://img.shields.io/badge/Powered%20by-Gemini%202.5-4285F4?logo=google)](https://ai.google.dev/)
[![LangChain](https://img.shields.io/badge/Framework-LangChain-00D4AA)](https://langchain.com/)

---

## What is VIRA?

VIRA answers VIT student questions about academic regulations instantly and accurately — citing the exact regulation it used. Instead of reading a 46-page PDF, just ask:

> *"I have 73% attendance in one subject. What will happen?"*

And VIRA replies with the exact regulation, consequence, and next steps.

---

## Architecture

```
Student Question
      |
      v
 Streamlit UI (app.py)
      |
      v
 RAG Pipeline (src/rag_pipeline.py)
  |-- Embedding: Google gemini-embedding-001
  |-- Vector DB: ChromaDB (187 chunks from 46-page PDF)
  |-- LLM: Google Gemini 2.5 Flash
      |
      v
 Cited Answer with Regulation Sources
```

---

## Local Setup

### Prerequisites
- Python 3.11+
- A free Google Gemini API key from [aistudio.google.com](https://aistudio.google.com/)

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/ritam03/vira-vit-chatbot.git
cd vira-vit-chatbot

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up API key
copy .env.example .env
# Edit .env and add: GOOGLE_API_KEY=your_key_here

# 5. Place VIT Regulations PDF
# Save as: data/vit_regulations.pdf

# 6. Build vector database (one-time, ~5 minutes)
python scripts/ingest.py

# 7. Launch VIRA!
streamlit run app.py
```

---

## Tech Stack

| Component | Technology | Cost |
|---|---|---|
| LLM | Google Gemini 2.5 Flash | Free |
| Embeddings | Google gemini-embedding-001 | Free |
| Vector Store | ChromaDB | Free |
| RAG Framework | LangChain | Free |
| Frontend | Streamlit | Free |
| Deployment | Streamlit Community Cloud | Free |

---

## Project Structure

```
VIRA/
├── app.py                    # Streamlit frontend
├── requirements.txt          # Dependencies
├── .env.example              # API key template
├── data/
│   └── vit_regulations.pdf   # Source document (not committed)
├── scripts/
│   ├── ingest.py             # One-time ingestion script
│   └── test_pipeline.py      # End-to-end test
├── src/
│   ├── rag_pipeline.py       # Core RAG logic
│   ├── document_processor.py # PDF parsing & chunking
│   └── prompts.py            # LLM prompt templates
└── vectorstore/
    └── chroma_db/            # Saved vector database
```

---

> **Disclaimer**: VIRA provides information for educational purposes only. Always verify with official VIT portals and academic offices.
