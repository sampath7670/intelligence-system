import json
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base

def utcnow():
    return datetime.now(timezone.utc)

class Suggestion(Base):
    __tablename__ = "suggestions"

    id = Column(Integer, primary_key=True, index=True)
    event_description = Column(String, nullable=False)
    interests = Column(String, nullable=False)        # Store comma-separated interests
    themes = Column(String, nullable=False)           # Store comma-separated themes
    starters_json = Column(String, nullable=False)    # JSON string representation of list of starters
    feedback_json = Column(String, nullable=False)    # JSON string representation of feedback per starter
    created_at = Column(DateTime, default=utcnow)

    @property
    def starters(self):
        try:
            return json.loads(self.starters_json)
        except Exception:
            return []

    @starters.setter
    def starters(self, value):
        self.starters_json = json.dumps(value)

    @property
    def feedback(self):
        try:
            return json.loads(self.feedback_json)
        except Exception:
            return []

    @feedback.setter
    def feedback(self, value):
        self.feedback_json = json.dumps(value)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    role = Column(String, nullable=False, default="Software Engineer")
    experience_level = Column(String, nullable=False, default="Mid-Level")
    technical_background = Column(String, nullable=False, default="Python, Machine Learning")
    networking_goal = Column(String, nullable=False, default="Career Growth & Collaboration")
    created_at = Column(DateTime, default=utcnow)

    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "experience_level": self.experience_level,
            "technical_background": self.technical_background,
            "networking_goal": self.networking_goal,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False) # pdf, docx, pptx, txt, md
    file_size = Column(Integer, nullable=False, default=0) # in bytes
    chunk_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=utcnow)

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "chunk_count": self.chunk_count,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("knowledge_documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text_content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    document = relationship("KnowledgeDocument", back_populates="chunks")

    def to_dict(self):
        return {
            "id": self.id,
            "document_id": self.document_id,
            "document_name": self.document.filename if self.document else "Unknown",
            "chunk_index": self.chunk_index,
            "text_content": self.text_content,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    conversation_type = Column(String, nullable=False) # linkedin_invitation, follow_up_email, interview_reply, event_icebreaker, technical_discussion
    title = Column(String, nullable=False)
    context_input = Column(Text, nullable=False, default="{}") # JSON of context passed in
    generated_content = Column(Text, nullable=False)
    rationale = Column(Text, nullable=True) # Explainable AI rationale
    confidence_score = Column(Float, nullable=False, default=0.85) # 0.0 to 1.0
    sources_json = Column(Text, nullable=False, default="[]") # JSON list of cited chunks/sources
    feedback = Column(Boolean, nullable=True) # True for thumbs up, False for thumbs down
    created_at = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="conversations")

    @property
    def sources(self):
        try:
            return json.loads(self.sources_json)
        except Exception:
            return []

    @sources.setter
    def sources(self, val):
        self.sources_json = json.dumps(val)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": self.user.name if self.user else "Anonymous",
            "conversation_type": self.conversation_type,
            "title": self.title,
            "context_input": json.loads(self.context_input) if self.context_input else {},
            "generated_content": self.generated_content,
            "rationale": self.rationale,
            "confidence_score": round(self.confidence_score, 2),
            "sources": self.sources,
            "feedback": self.feedback,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class VerificationRecord(Base):
    __tablename__ = "verification_records"

    id = Column(Integer, primary_key=True, index=True)
    claim = Column(Text, nullable=False)
    verdict = Column(String, nullable=False) # VERIFIED, PARTIALLY_SUPPORTED, UNVERIFIED
    confidence_score = Column(Float, nullable=False)
    sources_json = Column(Text, nullable=False, default="[]")
    explanation = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    @property
    def sources(self):
        try:
            return json.loads(self.sources_json)
        except Exception:
            return []

    @sources.setter
    def sources(self, val):
        self.sources_json = json.dumps(val)

    def to_dict(self):
        return {
            "id": self.id,
            "claim": self.claim,
            "verdict": self.verdict,
            "confidence_score": round(self.confidence_score, 2),
            "sources": self.sources,
            "explanation": self.explanation,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
