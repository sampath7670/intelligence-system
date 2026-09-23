import os
import sys
import json
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# Ensure the project root is importable
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.database import get_db
from backend.models.models import Suggestion, User, KnowledgeDocument, DocumentChunk, Conversation, VerificationRecord
from backend.services.nlp_service import nlp_service
from backend.services.wiki_service import wiki_service
from backend.services.document_service import document_service
from backend.services.vector_service import vector_service
from backend.services.verification_service import verification_service
from backend.services.recommendation_service import recommendation_service
from backend.services.evaluation_service import evaluation_service

router = APIRouter(prefix="/api")

# =========================================================================
# Pydantic Schemas
# =========================================================================

class SuggestionRequest(BaseModel):
    event_description: str = Field(..., min_length=5, description="Event details")
    interests: list[str] = Field(..., description="User's networking interests")

class FeedbackRequest(BaseModel):
    starter_index: int = Field(..., ge=0, description="Index of the starter")
    is_useful: Optional[bool] = Field(..., description="True if useful, False if not, None to reset")

class UserCreateRequest(BaseModel):
    name: str = Field(..., min_length=2)
    email: Optional[str] = None
    role: str = Field("Software Engineer")
    experience_level: str = Field("Mid-Level")
    technical_background: str = Field("Python, Distributed Systems")
    networking_goal: str = Field("Career Growth & Collaboration")

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2)
    top_k: int = Field(3, ge=1, le=10)
    hybrid: bool = Field(True)

class VerificationRequest(BaseModel):
    claim: str = Field(..., min_length=5)
    check_wiki: bool = Field(True)

class ConversationGenerateRequest(BaseModel):
    user_id: Optional[int] = None
    conversation_type: str = Field("linkedin_invitation", description="linkedin_invitation, follow_up_email, interview_reply, event_icebreaker, technical_discussion")
    recipient_name: str = Field("Alex")
    recipient_role: str = Field("Engineering Leader")
    topic: str = Field("Distributed AI Systems")
    specific_note: Optional[str] = ""
    use_rag: bool = Field(True)

class ConversationFeedbackRequest(BaseModel):
    feedback: Optional[bool] = Field(..., description="True for useful, False for unhelpful, None to clear")

class BenchmarkRequest(BaseModel):
    candidate_text: str = Field(..., min_length=5)
    conversation_type: str = Field("linkedin_invitation")
    custom_references: Optional[List[str]] = None

# =========================================================================
# Helper Formatters
# =========================================================================

def format_suggestion(suggestion: Suggestion) -> dict:
    return {
        "id": suggestion.id,
        "event_description": suggestion.event_description,
        "interests": [i.strip() for i in suggestion.interests.split(",") if i.strip()],
        "themes": [t.strip() for t in suggestion.themes.split(",") if t.strip()],
        "starters": suggestion.starters,
        "feedback": suggestion.feedback,
        "created_at": suggestion.created_at.isoformat() if suggestion.created_at else None
    }

# =========================================================================
# 1. User Management Endpoints (Module 1)
# =========================================================================

@router.get("/users", response_model=List[dict])
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.id.asc()).all()
    if not users:
        # Seed default default persona if none exists
        default_user = User(
            name="Alex Smith",
            email="alex@example.com",
            role="Machine Learning Engineer",
            experience_level="Mid-Level",
            technical_background="PyTorch, Transformers, RAG, FastAPI",
            networking_goal="Research Collaboration & Career Growth"
        )
        db.add(default_user)
        db.commit()
        db.refresh(default_user)
        users = [default_user]
    return [u.to_dict() for u in users]

@router.post("/users", response_model=dict)
def create_user(req: UserCreateRequest, db: Session = Depends(get_db)):
    user = User(
        name=req.name,
        email=req.email,
        role=req.role,
        experience_level=req.experience_level,
        technical_background=req.technical_background,
        networking_goal=req.networking_goal
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user.to_dict()

@router.get("/users/{user_id}", response_model=dict)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.to_dict()

# =========================================================================
# 2. Knowledge Repository & Document Management (Module 3)
# =========================================================================

@router.post("/knowledge/upload", response_model=dict)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        
        doc = document_service.ingest_document(db, file.filename, content)
        # Re-index the vector store with the new chunks
        vector_service.rebuild_index(db)

        return {
            "success": True,
            "document": doc.to_dict(),
            "message": f"Successfully ingested '{doc.filename}' ({doc.chunk_count} chunks created and indexed in FAISS + BM25)."
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to ingest document: {str(e)}")

@router.get("/knowledge/documents", response_model=List[dict])
def list_documents(db: Session = Depends(get_db)):
    document_service.seed_curated_knowledge(db)
    docs = db.query(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc()).all()
    return [d.to_dict() for d in docs]

@router.get("/knowledge/documents/{doc_id}/chunks", response_model=List[dict])
def list_document_chunks(doc_id: int, db: Session = Depends(get_db)):
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).order_by(DocumentChunk.chunk_index.asc()).all()
    return [c.to_dict() for c in chunks]

@router.delete("/knowledge/documents/{doc_id}", response_model=dict)
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    filename = doc.filename
    deleted = document_service.delete_document(db, doc_id)
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete document")

    # Rebuild vector index and BM25 index after document deletion
    vector_service.rebuild_index(db)

    return {
        "success": True,
        "message": f"Document '{filename}' and all associated indexed chunks were successfully deleted."
    }

# =========================================================================
# 3. Semantic Search & Hybrid Retrieval (Module 4)
# =========================================================================

@router.post("/knowledge/search", response_model=List[dict])
def search_knowledge(req: SearchRequest, db: Session = Depends(get_db)):
    document_service.seed_curated_knowledge(db)
    results = vector_service.search(db, query=req.query, top_k=req.top_k, hybrid=req.hybrid)
    return results

# =========================================================================
# 4. Knowledge Verification Engine (Module 5)
# =========================================================================

@router.post("/verify/knowledge", response_model=dict)
def verify_knowledge_claim(req: VerificationRequest, db: Session = Depends(get_db)):
    document_service.seed_curated_knowledge(db)
    result = verification_service.verify_claim(req.claim, db=db, check_wiki=req.check_wiki)
    return result

@router.get("/verify/history", response_model=List[dict])
def get_verification_history(limit: int = 15, db: Session = Depends(get_db)):
    records = db.query(VerificationRecord).order_by(VerificationRecord.created_at.desc()).limit(limit).all()
    return [r.to_dict() for r in records]

# Legacy fact verification route
@router.get("/verify", response_model=dict)
def verify_fact(query: str = Query(..., min_length=1, description="Fact or topic to verify")):
    res = wiki_service.verify_fact(query)
    if not res.get("success", False):
        raise HTTPException(status_code=400, detail=res.get("message", "Fact verification failed."))
    return res

# =========================================================================
# 5. Professional Conversation Generation (Modules 2 & 6)
# =========================================================================

@router.post("/conversations/generate", response_model=dict)
def generate_conversation(req: ConversationGenerateRequest, db: Session = Depends(get_db)):
    document_service.seed_curated_knowledge(db)
    
    # 1. Resolve User Persona
    user_persona = None
    if req.user_id:
        user = db.query(User).filter(User.id == req.user_id).first()
        if user:
            user_persona = user.to_dict()

    # 2. RAG Evidence Retrieval via FAISS + BM25
    retrieved_evidence = []
    if req.use_rag:
        search_query = f"{req.topic} {req.recipient_role}"
        retrieved_evidence = vector_service.search(db, search_query, top_k=2, hybrid=True)

    # 3. Context payload
    context = {
        "recipient_name": req.recipient_name,
        "recipient_role": req.recipient_role,
        "topic": req.topic,
        "specific_note": req.specific_note
    }

    # 4. Generate conversation with explainable rationale
    gen_result = nlp_service.generate_professional_conversation(
        conversation_type=req.conversation_type,
        context=context,
        user_persona=user_persona,
        retrieved_evidence=retrieved_evidence
    )

    # 5. Pass through Verification Engine to validate and produce confidence score
    verif_eval = verification_service.verify_conversation(gen_result["generated_content"], db=db)
    if verif_eval["overall_verdict"] == "VERIFIED":
        final_confidence = max(gen_result["confidence_score"], verif_eval["overall_confidence"])
        if req.use_rag and retrieved_evidence:
            final_confidence = min(0.98, final_confidence + 0.03)
    elif verif_eval["overall_verdict"] == "PARTIALLY_SUPPORTED":
        final_confidence = min(gen_result["confidence_score"], max(0.70, verif_eval["overall_confidence"]))
    else:
        final_confidence = min(gen_result["confidence_score"], verif_eval["overall_confidence"])

    # 6. Persist Conversation in Database
    convo = Conversation(
        user_id=req.user_id,
        conversation_type=req.conversation_type,
        title=gen_result["title"],
        context_input=json.dumps(context),
        generated_content=gen_result["generated_content"],
        rationale=gen_result["rationale"],
        confidence_score=round(final_confidence, 2)
    )
    # Merge citations
    convo.sources = gen_result.get("citations", []) + verif_eval.get("sources", [])
    db.add(convo)
    db.commit()
    db.refresh(convo)

    response_data = convo.to_dict()
    response_data["verification_status"] = verif_eval["overall_verdict"]
    return response_data

@router.get("/conversations", response_model=List[dict])
def list_conversations(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Conversation)
    if user_id:
        query = query.filter(Conversation.user_id == user_id)
    convos = query.order_by(Conversation.created_at.desc()).all()
    return [c.to_dict() for c in convos]

@router.post("/conversations/{convo_id}/feedback", response_model=dict)
def update_conversation_feedback(convo_id: int, req: ConversationFeedbackRequest, db: Session = Depends(get_db)):
    convo = db.query(Conversation).filter(Conversation.id == convo_id).first()
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    convo.feedback = req.feedback
    if req.feedback is True:
        # Increase confidence score when confirmed correct and valuable by the user
        convo.confidence_score = min(0.99, round(convo.confidence_score + 0.05, 2))
    elif req.feedback is False:
        convo.confidence_score = max(0.50, round(convo.confidence_score - 0.10, 2))
    db.commit()
    db.refresh(convo)
    return convo.to_dict()

# Legacy suggestions route
@router.post("/suggestions", response_model=dict)
def generate_suggestions(req: SuggestionRequest, db: Session = Depends(get_db)):
    try:
        themes = nlp_service.extract_themes(req.event_description, top_n=3)
        starters = nlp_service.generate_starters(req.event_description, themes, req.interests)
        
        suggestion = Suggestion(
            event_description=req.event_description,
            interests=",".join(req.interests),
            themes=",".join(themes),
        )
        suggestion.starters = starters
        suggestion.feedback = [None] * len(starters)
        
        db.add(suggestion)
        db.commit()
        db.refresh(suggestion)
        
        return format_suggestion(suggestion)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to generate suggestions: {str(e)}")

@router.get("/history", response_model=List[dict])
def get_history(db: Session = Depends(get_db)):
    try:
        suggestions = db.query(Suggestion).order_by(Suggestion.created_at.desc()).all()
        return [format_suggestion(s) for s in suggestions]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch history: {str(e)}")

@router.post("/history/{suggestion_id}/feedback", response_model=dict)
def log_feedback(suggestion_id: int, req: FeedbackRequest, db: Session = Depends(get_db)):
    suggestion = db.query(Suggestion).filter(Suggestion.id == suggestion_id).first()
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
        
    try:
        feedbacks = suggestion.feedback
        if len(feedbacks) <= req.starter_index:
            feedbacks = [None] * len(suggestion.starters)
            
        feedbacks[req.starter_index] = req.is_useful
        suggestion.feedback = feedbacks
        
        db.commit()
        db.refresh(suggestion)
        
        return format_suggestion(suggestion)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to log feedback: {str(e)}")

# =========================================================================
# 6. Recommendation Engine (Module 7)
# =========================================================================

@router.get("/recommendations", response_model=dict)
def get_recommendations(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    return recommendation_service.get_recommendations(db, user_id=user_id)

# =========================================================================
# 7. Analytics & Evaluation Benchmark (Module 8)
# =========================================================================

@router.get("/analytics/overview", response_model=dict)
def get_analytics_overview(db: Session = Depends(get_db)):
    # User count
    total_users = db.query(User).count()
    
    # Conversations
    convos = db.query(Conversation).all()
    total_convos = len(convos)
    thumbs_up = sum(1 for c in convos if c.feedback is True)
    thumbs_down = sum(1 for c in convos if c.feedback is False)
    
    # Suggestions legacy
    suggestions = db.query(Suggestion).all()
    legacy_events = len(suggestions)
    legacy_thumbs_up = sum(1 for s in suggestions for f in s.feedback if f is True)
    legacy_thumbs_down = sum(1 for s in suggestions for f in s.feedback if f is False)

    total_up = thumbs_up + legacy_thumbs_up
    total_down = thumbs_down + legacy_thumbs_down
    total_rated = total_up + total_down
    satisfaction_rate = round((total_up / total_rated * 100), 1) if total_rated > 0 else 100.0

    # Knowledge Documents
    doc_count = db.query(KnowledgeDocument).count()
    chunk_count = db.query(DocumentChunk).count()

    # Verification records
    verif_records = db.query(VerificationRecord).all()
    total_verifications = len(verif_records)
    verified_count = sum(1 for v in verif_records if v.verdict == "VERIFIED")
    avg_confidence = (
        round(sum(v.confidence_score for v in verif_records) / total_verifications * 100, 1)
        if total_verifications > 0 else 88.5
    )

    # Conversation types breakdown
    type_counts = {}
    for c in convos:
        type_counts[c.conversation_type] = type_counts.get(c.conversation_type, 0) + 1

    return {
        "total_users": total_users,
        "total_conversations": total_convos,
        "total_legacy_events": legacy_events,
        "satisfaction_rate": satisfaction_rate,
        "thumbs_up": total_up,
        "thumbs_down": total_down,
        "total_documents": doc_count,
        "total_chunks": chunk_count,
        "total_verifications": total_verifications,
        "verified_percentage": round(verified_count / total_verifications * 100, 1) if total_verifications > 0 else 90.0,
        "average_confidence": avg_confidence,
        "conversation_types": type_counts
    }

@router.post("/evaluation/benchmark", response_model=dict)
def run_benchmark(req: BenchmarkRequest):
    if req.custom_references:
        res = evaluation_service.evaluate_text(req.candidate_text, req.custom_references)
    else:
        res = evaluation_service.run_benchmark_suite(req.candidate_text, req.conversation_type)
    return res
