# Intelligent Networking Assistant

An AI-powered system for **Personalized Professional Communication, Retrieval-Augmented Generation (RAG), and Knowledge Verification** using Transformer models.

---

## 🌟 Key Modules & Capabilities

### 1. User Management (Module 1)
* **Persona-Driven Context**: Configurable user profiles capturing professional roles (e.g. Machine Learning Engineer, Product Manager, Student), technical backgrounds, experience levels, and networking objectives.

### 2. Multi-Modal Professional Conversation Generator (Module 2 & 6)
* **Tailored Formats**:
  * 💼 **LinkedIn Connection Invitations** (<300 characters or personalized note)
  * 📧 **Post-Event / Meeting Follow-up Emails** (structured subject lines, action items)
  * 🎯 **Technical Interview Follow-up & STAR Responses**
  * 💡 **Technical Discussion Contributions** (grounded in verified technical facts)
  * 🎤 **Conference & Event Icebreakers** (agenda & theme-targeted)
* **Explainable AI**: Every output provides an explicit **Explainability Rationale** and **Confidence Score**.

### 3. Multi-Format Knowledge Repository (Module 3)
* Ingests and extracts text from **PDF**, **Word (.docx)**, **PowerPoint (.pptx)**, and **Plain Text/Markdown**.
* Automated sliding-window chunking with overlap.
* Pre-seeded with curated reference documents covering networking principles, RAG architectures, and career strategies.

### 4. Semantic Search & Hybrid RAG Engine (Module 4)
* **Sentence-BERT Dense Embeddings**: Generates semantic vectors via `sentence-transformers/all-MiniLM-L6-v2`.
* **FAISS Vector Index**: Sub-millisecond dense inner-product / cosine similarity search.
* **BM25 Keyword Search**: Exact lexical matching via `rank_bm25`.
* **Reciprocal Rank Fusion (RRF)**: Merges dense vector and sparse keyword rankings for optimal document retrieval.

### 5. Knowledge Verification Engine (Module 5)
* Factual consistency and entailment validation.
* Cross-references claims against internal knowledge repository chunks and Wikipedia encyclopedic articles.
* Generates an explainable **Factuality Confidence Score (0-100%)**, **Verdict** (`VERIFIED`, `PARTIALLY_SUPPORTED`, `UNVERIFIED`), and **Source Citations**.

### 6. Smart Recommendation Engine (Module 7)
* Suggests high-impact discussion topics based on user role and industry trends.
* Recommends strategic follow-up timing and questions.
* Learns proven high-impact conversation starters from past positive user ratings.

### 7. Analytics Dashboard & Objective Evaluation (Module 8)
* Visual metrics tracking total conversations, feedback satisfaction rate, and indexed knowledge chunks.
* **Live NLP Evaluation Suite**: Computes **SacreBLEU**, **chrF**, and **ROUGE-1 / ROUGE-2 / ROUGE-L** scores against gold-standard professional communication benchmarks.

---

## 🚀 Quick Start Guide

### Prerequisites
* Python 3.10+ (Tested on Python 3.11 and 3.13)
* Windows, macOS, or Linux

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd networking-assistant

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1    # On Windows
# source .venv/bin/activate     # On Linux/macOS

# Install dependencies
pip install -r backend/requirements.txt
```

### Running the Services

**Terminal 1: Start FastAPI Backend**
```powershell
.\.venv\Scripts\uvicorn backend.main:app --reload --port 8000
```
* Interactive Swagger API Docs: `http://127.0.0.1:8000/docs`

**Terminal 2: Start Streamlit Frontend**
```powershell
.\.venv\Scripts\streamlit run frontend/app.py
```
* Web Interface: `http://localhost:8501`

### Running Automated Tests
```powershell
.\.venv\Scripts\pytest -v
```
