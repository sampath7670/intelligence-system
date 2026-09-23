import sys
import os
import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import Base, get_db
from backend.main import app
from backend.models.models import Suggestion, User, KnowledgeDocument, DocumentChunk, Conversation, VerificationRecord
from backend.services.nlp_service import nlp_service
from backend.services.wiki_service import wiki_service
from backend.services.document_service import document_service
from backend.services.vector_service import vector_service
from backend.services.verification_service import verification_service
from backend.services.recommendation_service import recommendation_service
from backend.services.evaluation_service import evaluation_service

# Configure isolated testing database
TEST_DATABASE_URL = "sqlite:///test_networking_assistant.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_db():
    """Create all tables before each test and drop them after."""
    Base.metadata.create_all(bind=engine)
    nlp_service.use_fallback = True
    vector_service.use_fallback = True
    document_service.has_seeded = False
    db = TestingSessionLocal()
    try:
        document_service.seed_curated_knowledge(db, force=True)
        vector_service.rebuild_index(db)
    finally:
        db.close()
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists("test_networking_assistant.db"):
        try:
            os.remove("test_networking_assistant.db")
        except Exception:
            pass

client = TestClient(app)

# =========================================================================
# 1. DOCUMENT SERVICE TESTS (Module 3)
# =========================================================================

def test_document_service_chunking():
    sample_text = (
        "Retrieval-Augmented Generation (RAG) is an architectural pattern that enhances language models. "
        "It retrieves verifiable external facts from a vector database before text generation.\n\n"
        "By doing so, the system avoids generating hallucinations and guarantees source traceability. "
        "Knowledge verification compares the output against retrieved evidence to compute confidence."
    )
    chunks = document_service.chunk_text(sample_text)
    assert len(chunks) >= 1
    assert any("Retrieval-Augmented" in c for c in chunks)

def test_document_service_text_ingestion():
    db = TestingSessionLocal()
    try:
        content = b"Effective networking requires active listening and mutual value exchange."
        doc = document_service.ingest_document(db, "test_notes.txt", content)
        assert doc.id is not None
        assert doc.filename == "test_notes.txt"
        assert doc.chunk_count >= 1
    finally:
        db.close()

# =========================================================================
# 2. VECTOR SERVICE & HYBRID RETRIEVAL (Module 4)
# =========================================================================

def test_vector_service_indexing_and_search():
    db = TestingSessionLocal()
    try:
        # Ingest document
        content = b"FAISS is a library for dense vector similarity search developed by Meta Research."
        document_service.ingest_document(db, "faiss_overview.txt", content)
        vector_service.rebuild_index(db)

        results = vector_service.search(db, query="dense vector similarity", top_k=2, hybrid=True)
        assert len(results) >= 1
        assert "FAISS" in results[0]["text"]
        assert "score" in results[0]
        assert "rrf_score" in results[0]
    finally:
        db.close()

def test_vector_service_similarity_computation():
    sim = vector_service.compute_similarity("machine learning and neural networks", "deep learning and AI models")
    assert 0.0 <= sim <= 1.0

# =========================================================================
# 3. KNOWLEDGE VERIFICATION ENGINE (Module 5)
# =========================================================================

def test_verification_service_claim_check():
    db = TestingSessionLocal()
    try:
        # Seed and test claim
        document_service.seed_curated_knowledge(db)
        vector_service.rebuild_index(db)

        res = verification_service.verify_claim(
            "Retrieval-Augmented Generation retrieves semantic context chunks to prevent hallucinations.",
            db=db,
            check_wiki=False
        )
        assert "verdict" in res
        assert "confidence_score" in res
        assert res["confidence_score"] > 0.0
        assert "explanation" in res
    finally:
        db.close()

def test_verification_factual_accuracy_alignment():
    db = TestingSessionLocal()
    try:
        # 1. Test claim matching internal knowledge repository with sentence alignment
        res_rag = verification_service.verify_claim(
            "Retrieval-Augmented Generation grounds large language models in verified external documents to reduce hallucinations.",
            db=db,
            check_wiki=False
        )
        assert res_rag["verdict"] in ["VERIFIED", "PARTIALLY_SUPPORTED"]
        assert res_rag["confidence_pct"] >= 30

        # 2. Test sentence alignment method directly
        sim, excerpt = verification_service.compute_evidence_alignment(
            "Transformers use self-attention mechanisms.",
            "Deep learning systems rely on various architectures. Transformers use self-attention mechanisms to process tokens in parallel. This enables massive scaling."
        )
        assert sim > 0.30
        assert "Transformers use self-attention" in excerpt

        # 3. Verify that correct information corroborated by knowledge receives high confidence
        assert res_rag["verdict"] == "VERIFIED"
        assert res_rag["confidence_score"] >= 0.85
        assert res_rag["confidence_pct"] >= 85
    finally:
        db.close()

# =========================================================================
# 4. RECOMMENDATION SERVICE (Module 7)
# =========================================================================

def test_recommendation_service():
    db = TestingSessionLocal()
    try:
        recs = recommendation_service.get_recommendations(db)
        assert "recommended_topics" in recs
        assert len(recs["recommended_topics"]) >= 2
        assert "strategy_guidance" in recs
        assert "mindset" in recs["strategy_guidance"]
        assert "recommended_questions" in recs
    finally:
        db.close()

# =========================================================================
# 5. EVALUATION BENCHMARK SERVICE (Module 8)
# =========================================================================

def test_evaluation_service_metrics():
    candidate = "Hi Alex, I would love to connect and discuss distributed AI systems."
    references = [
        "Hi Alex, I would love to connect and follow your journey in AI systems.",
        "Hello Alex, I'd like to connect on LinkedIn to discuss distributed systems."
    ]
    scores = evaluation_service.evaluate_text(candidate, references)
    assert "bleu" in scores
    assert "chrf" in scores
    assert "rouge1" in scores
    assert scores["chrf"] > 0.0

def test_evaluation_benchmark_suite():
    candidate = "Hi Alex, great meeting you at the summit. I really enjoyed our discussion on RAG pipelines."
    suite_res = evaluation_service.run_benchmark_suite(candidate, "linkedin_invitation")
    assert suite_res["chrf"] > 0.0
    assert "interpretation" in suite_res

# =========================================================================
# 6. NLP SERVICE & PROFESSIONAL CONVERSATION GENERATION (Modules 2 & 6)
# =========================================================================

def test_nlp_service_extract_themes_fallback():
    event_desc = "AI and sustainable cities development summit on climate change"
    themes = nlp_service.extract_themes(event_desc, top_n=3)
    assert len(themes) == 3

def test_nlp_service_professional_generation_all_modalities():
    modalities = ["linkedin_invitation", "follow_up_email", "interview_reply", "technical_discussion", "event_icebreaker"]
    context = {
        "recipient_name": "Dr. Aris Thorne",
        "recipient_role": "VP of AI Research",
        "topic": "Retrieval-Augmented Generation",
        "specific_note": "Mention our discussion on vector search latency."
    }
    persona = {
        "role": "Machine Learning Engineer",
        "experience_level": "Senior",
        "technical_background": "PyTorch, Transformers, FAISS",
        "networking_goal": "Technical Collaboration"
    }

    for mod in modalities:
        result = nlp_service.generate_professional_conversation(mod, context, persona)
        assert result["conversation_type"] == mod
        assert len(result["generated_content"]) > 30
        assert "rationale" in result
        assert result["confidence_score"] >= 0.70

# =========================================================================
# 7. FASTAPI API ROUTES TESTS
# =========================================================================

def test_user_routes():
    # 1. Create User
    payload = {
        "name": "Sarah Connor",
        "email": "sarah@example.com",
        "role": "Cloud Architect",
        "experience_level": "Senior",
        "technical_background": "AWS, Kubernetes, Go",
        "networking_goal": "Industry Collaboration"
    }
    create_res = client.post("/api/users", json=payload)
    assert create_res.status_code == 200
    user_data = create_res.json()
    assert user_data["name"] == "Sarah Connor"
    user_id = user_data["id"]

    # 2. Get User
    get_res = client.get(f"/api/users/{user_id}")
    assert get_res.status_code == 200
    assert get_res.json()["role"] == "Cloud Architect"

def test_knowledge_routes():
    # 1. List Curated Documents
    res = client.get("/api/knowledge/documents")
    assert res.status_code == 200
    docs = res.json()
    assert len(docs) >= 1
    doc_id = docs[0]["id"]

    # 2. Hybrid Search Route
    search_payload = {"query": "RAG architecture", "top_k": 2, "hybrid": True}
    search_res = client.post("/api/knowledge/search", json=search_payload)
    assert search_res.status_code == 200
    assert isinstance(search_res.json(), list)

    # 3. Delete Document Route
    del_res = client.delete(f"/api/knowledge/documents/{doc_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # 4. Verify Document was removed
    res_after = client.get("/api/knowledge/documents")
    remaining_ids = [d["id"] for d in res_after.json()]
    assert doc_id not in remaining_ids

def test_verification_routes(monkeypatch):
    # Mock wikipedia lookup for isolated test
    monkeypatch.setattr(wiki_service, "verify_fact", lambda q: {
        "success": True, "title": "RAG", "summary": "RAG enhances LLMs with external data.", "url": "https://wiki.org/rag"
    })
    v_res = client.post("/api/verify/knowledge", json={"claim": "RAG uses external data.", "check_wiki": True})
    assert v_res.status_code == 200
    v_data = v_res.json()
    assert v_data["verdict"] in ["VERIFIED", "PARTIALLY_SUPPORTED", "UNVERIFIED"]

def test_conversation_generation_route():
    payload = {
        "conversation_type": "linkedin_invitation",
        "recipient_name": "Elena Rostova",
        "recipient_role": "Director of Engineering",
        "topic": "Scalable Microservices",
        "specific_note": "Met at Cloud Summit",
        "use_rag": True
    }
    res = client.post("/api/conversations/generate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "id" in data
    assert "generated_content" in data
    assert "confidence_score" in data
    assert "rationale" in data

    # Test feedback on conversation
    convo_id = data["id"]
    fb_res = client.post(f"/api/conversations/{convo_id}/feedback", json={"feedback": True})
    assert fb_res.status_code == 200
    assert fb_res.json()["feedback"] is True

def test_analytics_and_evaluation_routes():
    # Analytics overview
    a_res = client.get("/api/analytics/overview")
    assert a_res.status_code == 200
    assert "total_conversations" in a_res.json()
    assert "satisfaction_rate" in a_res.json()

    # Evaluation benchmark
    e_payload = {
        "candidate_text": "Hi Alex, great meeting you at the summit. I really enjoyed our discussion on RAG pipelines.",
        "conversation_type": "linkedin_invitation"
    }
    e_res = client.post("/api/evaluation/benchmark", json=e_payload)
    assert e_res.status_code == 200
    assert "chrf" in e_res.json()
    assert "bleu" in e_res.json()

# =========================================================================
# 8. LEGACY COMPATIBILITY TESTS
# =========================================================================

def test_root_endpoint():
    res = client.get("/")
    assert res.status_code == 200
    assert "API is running" in res.json()["message"]

def test_legacy_suggestions_and_feedback():
    payload = {
        "event_description": "AI for Sustainable Cities Summit",
        "interests": ["climate change", "urban planning"]
    }
    res = client.post("/api/suggestions", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data["starters"]) == 3

    # Feedback
    fb_res = client.post(f"/api/history/{data['id']}/feedback", json={"starter_index": 0, "is_useful": True})
    assert fb_res.status_code == 200
    assert fb_res.json()["feedback"][0] is True
