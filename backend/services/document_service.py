import io
import os
import re
import logging
from typing import List, Dict, Any
from pypdf import PdfReader
import docx
import pptx
from sqlalchemy.orm import Session
from backend.models.models import KnowledgeDocument, DocumentChunk

logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(self, chunk_size: int = 450, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.has_seeded = False

    def parse_file(self, filename: str, content: bytes) -> str:
        """
        Parse raw bytes from PDF, DOCX, PPTX, or TXT into plain text.
        """
        ext = os.path.splitext(filename)[1].lower()
        text_content = ""

        try:
            if ext == ".pdf":
                reader = PdfReader(io.BytesIO(content))
                pages_text = []
                for idx, page in enumerate(reader.pages):
                    extracted = page.extract_text()
                    if extracted:
                        pages_text.append(f"[Page {idx + 1}]\n{extracted.strip()}")
                text_content = "\n\n".join(pages_text)

            elif ext in [".docx", ".doc"]:
                doc = docx.Document(io.BytesIO(content))
                paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
                # Also extract table text
                for table in doc.tables:
                    for row in table.rows:
                        row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                        if row_text:
                            paragraphs.append(row_text)
                text_content = "\n\n".join(paragraphs)

            elif ext in [".pptx", ".ppt"]:
                prs = pptx.Presentation(io.BytesIO(content))
                slides_text = []
                for idx, slide in enumerate(prs.slides):
                    slide_lines = []
                    for shape in slide.shapes:
                        if hasattr(shape, "text") and shape.text.strip():
                            slide_lines.append(shape.text.strip())
                    if slide_lines:
                        slides_text.append(f"[Slide {idx + 1}]\n" + "\n".join(slide_lines))
                text_content = "\n\n".join(slides_text)

            elif ext in [".txt", ".md", ".json", ".csv"]:
                try:
                    text_content = content.decode("utf-8")
                except UnicodeDecodeError:
                    text_content = content.decode("latin-1", errors="replace")

            else:
                # Default text decoding fallback
                try:
                    text_content = content.decode("utf-8")
                except Exception:
                    text_content = content.decode("latin-1", errors="replace")

        except Exception as e:
            logger.error(f"Failed to parse document '{filename}': {e}", exc_info=True)
            raise ValueError(f"Failed to parse '{filename}': {str(e)}")

        return text_content.strip()

    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping semantic chunks based on paragraph and sentence boundaries.
        """
        if not text:
            return []

        # Split into initial paragraphs
        raw_paragraphs = [p.strip() for p in re.split(r'\n{2,}', text) if p.strip()]
        chunks = []
        current_chunk = ""

        for paragraph in raw_paragraphs:
            if len(current_chunk) + len(paragraph) + 1 <= self.chunk_size:
                current_chunk = f"{current_chunk}\n\n{paragraph}".strip()
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                
                # If paragraph itself exceeds chunk_size, split by sentences
                if len(paragraph) > self.chunk_size:
                    sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                    sub_chunk = ""
                    for s in sentences:
                        if len(sub_chunk) + len(s) + 1 <= self.chunk_size:
                            sub_chunk = f"{sub_chunk} {s}".strip()
                        else:
                            if sub_chunk:
                                chunks.append(sub_chunk)
                            sub_chunk = s
                    if sub_chunk:
                        current_chunk = sub_chunk
                else:
                    current_chunk = paragraph

        if current_chunk:
            chunks.append(current_chunk)

        # Filter out trivial fragments
        valid_chunks = [c.strip() for c in chunks if len(c.strip()) > 30]
        return valid_chunks if valid_chunks else [text[:self.chunk_size]]

    def ingest_document(self, db: Session, filename: str, content: bytes) -> KnowledgeDocument:
        """
        Parse file, chunk content, and persist KnowledgeDocument + DocumentChunks in DB.
        """
        parsed_text = self.parse_file(filename, content)
        if not parsed_text:
            raise ValueError(f"Document '{filename}' appears empty or could not be extracted.")

        chunks = self.chunk_text(parsed_text)
        ext = os.path.splitext(filename)[1].lower().lstrip(".") or "txt"

        doc = KnowledgeDocument(
            filename=filename,
            file_type=ext,
            file_size=len(content),
            chunk_count=len(chunks)
        )
        db.add(doc)
        db.flush() # populate doc.id

        chunk_records = []
        for idx, chunk_str in enumerate(chunks):
            chunk_obj = DocumentChunk(
                document_id=doc.id,
                chunk_index=idx,
                text_content=chunk_str
            )
            chunk_records.append(chunk_obj)

        db.add_all(chunk_records)
        db.commit()
        db.refresh(doc)
        return doc

    def delete_document(self, db: Session, doc_id: int) -> bool:
        """
        Delete a document and all its chunks from the database.
        """
        doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
        if not doc:
            return False
        
        # Delete associated chunks
        db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).delete()
        db.delete(doc)
        db.commit()
        return True

    def seed_curated_knowledge(self, db: Session, force: bool = False):
        """
        Seed curated reference knowledge if the repository is empty.
        Provides instant out-of-the-box knowledge on networking, LLMs, and interview best practices.
        """
        if getattr(self, "has_seeded", False) and not force:
            return

        existing = db.query(KnowledgeDocument).count()
        if existing > 0 and not force:
            self.has_seeded = True
            return

        curated_docs = [
            {
                "filename": "Professional_Networking_Playbook.txt",
                "content": (
                    "Effective Professional Networking Principles:\n"
                    "1. Always lead with mutual value and curiosity rather than immediate requests. "
                    "When connecting with engineering leaders or recruiters on LinkedIn, reference specific shared technical domains or recent company milestones.\n"
                    "2. Follow-Up Timing: Send a personalized follow-up email within 24 to 48 hours of an event or interview. "
                    "Reiterate key points discussed, share relevant resources or thoughts on challenges mentioned, and propose a concise 15-minute sync.\n"
                    "3. Informational Interviews: Approach informational interviews as knowledge-seeking dialogues. Inquire about architectural choices, "
                    "career transitions, and technology roadmaps to demonstrate genuine curiosity and technical maturity."
                ).encode("utf-8")
            },
            {
                "filename": "Transformer_Models_and_RAG_Architecture.txt",
                "content": (
                    "Transformer Models & Retrieval-Augmented Generation (RAG):\n"
                    "1. Retrieval-Augmented Generation (RAG) grounds Large Language Models in verified external knowledge by retrieving "
                    "semantic context chunks via vector search before response synthesis. This directly prevents hallucinations and stale knowledge.\n"
                    "2. Knowledge Verification: To ensure factual accuracy, systems utilize semantic similarity scoring between LLM claims "
                    "and retrieved evidence passages. Cross-encoders or SBERT sentence embeddings compute entailment confidence.\n"
                    "3. Vector Search: Dense vector representations produced by Sentence-BERT (such as all-MiniLM-L6-v2) mapped into FAISS "
                    "indexes enable nearest-neighbor semantic search with sub-millisecond retrieval latency."
                ).encode("utf-8")
            },
            {
                "filename": "Technical_Interview_and_Career_Growth.txt",
                "content": (
                    "Technical Interview & Career Growth Strategies:\n"
                    "1. The STAR Methodology: Structure behavioral and technical responses around Situation, Task, Action, and Result. "
                    "Emphasize quantifiable outcomes, such as reduced latency by 40% or scaled throughput to 50,000 requests/second.\n"
                    "2. Cross-Functional Communication: Senior engineers must bridge technical complexity and business impact. "
                    "Explain tradeoffs between consistency, availability, and development speed clearly to stakeholders.\n"
                    "3. Asking Impactful Interviewer Questions: Ask insightful questions regarding engineering culture, technical debt management, "
                    "and deployment frequency (e.g. CI/CD pipelines, observability with Prometheus/Grafana) to stand out."
                ).encode("utf-8")
            }
        ]

        for item in curated_docs:
            self.ingest_document(db, item["filename"], item["content"])
        self.has_seeded = True
        logger.info("Successfully seeded curated knowledge repository.")

document_service = DocumentService()
