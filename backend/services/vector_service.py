import os
import re
import logging
import numpy as np
from typing import List, Dict, Any, Optional
try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False
    faiss = None
from rank_bm25 import BM25Okapi
from sqlalchemy.orm import Session
from backend.models.models import DocumentChunk, KnowledgeDocument

logger = logging.getLogger(__name__)

class VectorService:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.embedding_model = None
        self.dimension = 384 # all-MiniLM-L6-v2 dimension
        self.faiss_index = None
        self.bm25_index = None
        self.chunk_metadata: List[Dict[str, Any]] = []
        self.tokenized_corpus: List[List[str]] = []
        self.embeddings_matrix: Optional[np.ndarray] = None
        self.is_initialized = False
        self.use_fallback = False

    def load_model(self):
        """Lazy load SentenceTransformer model."""
        if self.embedding_model is not None or self.use_fallback:
            return

        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading SentenceTransformer: {self.model_name}...")
            self.embedding_model = SentenceTransformer(self.model_name)
            self.dimension = self.embedding_model.get_sentence_embedding_dimension()
            logger.info(f"SentenceTransformer loaded successfully (dimension={self.dimension}).")
        except Exception as e:
            logger.warning(f"Could not load SentenceTransformer ({e}). Using TF-IDF/heuristic vector fallback.")
            self.use_fallback = True

    def _normalize(self, vectors: np.ndarray) -> np.ndarray:
        """L2 normalize vectors for cosine similarity via Inner Product."""
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1e-10
        return vectors / norms

    def encode(self, texts: List[str]) -> np.ndarray:
        """Compute normalized dense embeddings for a list of strings."""
        self.load_model()
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)

        if not self.use_fallback and self.embedding_model is not None:
            try:
                embeddings = self.embedding_model.encode(
                    texts,
                    batch_size=32,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                    normalize_embeddings=True
                )
                return embeddings.astype(np.float32)
            except Exception as e:
                logger.warning(f"SentenceTransformer encode failed: {e}. Falling back.")

        # Heuristic fallback embedding: bag-of-characters/words hash vector
        vecs = []
        for text in texts:
            vec = np.zeros(self.dimension, dtype=np.float32)
            words = re.findall(r'\w+', text.lower())
            for w in words:
                idx = hash(w) % self.dimension
                vec[idx] += 1.0
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec /= norm
            vecs.append(vec)
        return np.array(vecs, dtype=np.float32)

    def tokenize_text(self, text: str) -> List[str]:
        return re.findall(r'\w+', text.lower())

    def rebuild_index(self, db: Session):
        """
        Build FAISS vector index and BM25 index from all DocumentChunks in the database.
        """
        chunks = db.query(DocumentChunk).all()
        self.chunk_metadata = []
        self.tokenized_corpus = []

        if not chunks:
            if HAS_FAISS and faiss is not None:
                self.faiss_index = faiss.IndexFlatIP(self.dimension)
            self.embeddings_matrix = np.zeros((0, self.dimension), dtype=np.float32)
            self.bm25_index = None
            self.is_initialized = True
            logger.info("Vector & BM25 indexes initialized with 0 chunks.")
            return

        texts = []
        for c in chunks:
            doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == c.document_id).first()
            doc_name = doc.filename if doc else "Unknown"
            texts.append(c.text_content)
            self.chunk_metadata.append({
                "chunk_id": c.id,
                "document_id": c.document_id,
                "document_name": doc_name,
                "chunk_index": c.chunk_index,
                "text": c.text_content
            })
            self.tokenized_corpus.append(self.tokenize_text(c.text_content))

        # Build dense embeddings
        embeddings = self.encode(texts)
        self.embeddings_matrix = embeddings

        if HAS_FAISS and faiss is not None:
            self.faiss_index = faiss.IndexFlatIP(self.dimension)
            self.faiss_index.add(embeddings)
        else:
            self.faiss_index = None

        # Build BM25 index
        if self.tokenized_corpus:
            self.bm25_index = BM25Okapi(self.tokenized_corpus)

        self.is_initialized = True
        logger.info(f"Rebuilt index with {len(chunks)} chunks and BM25 corpus.")

    def search(self, db: Session, query: str, top_k: int = 4, hybrid: bool = True) -> List[Dict[str, Any]]:
        """
        Execute hybrid search (FAISS/NumPy dense semantic search + BM25 keyword search)
        using Reciprocal Rank Fusion (RRF).
        """
        if not self.is_initialized or (self.faiss_index is None and self.embeddings_matrix is None):
            self.rebuild_index(db)

        if not self.chunk_metadata or not query.strip():
            return []

        k = min(top_k * 2, len(self.chunk_metadata))

        # 1. Dense Semantic Search
        query_emb = self.encode([query])

        if HAS_FAISS and self.faiss_index is not None:
            dense_distances, dense_indices = self.faiss_index.search(query_emb, k)
            d_dists = dense_distances[0]
            d_idxs = dense_indices[0]
        else:
            # NumPy inner product vector search
            scores = np.dot(self.embeddings_matrix, query_emb.T).flatten()
            top_indices = np.argsort(scores)[::-1][:k]
            d_dists = scores[top_indices]
            d_idxs = top_indices

        dense_ranks: Dict[int, int] = {}
        idx_to_dist: Dict[int, float] = {}
        for rank, (dist, idx) in enumerate(zip(d_dists, d_idxs)):
            if idx != -1 and idx < len(self.chunk_metadata):
                dense_ranks[idx] = rank + 1
                idx_to_dist[idx] = float(dist)

        # 2. Sparse Keyword Search (BM25)
        bm25_ranks: Dict[int, int] = {}
        if hybrid and self.bm25_index is not None:
            tokenized_query = self.tokenize_text(query)
            if tokenized_query:
                bm25_scores = self.bm25_index.get_scores(tokenized_query)
                # Sort indices by score descending
                sorted_bm25_indices = np.argsort(bm25_scores)[::-1][:k]
                for rank, idx in enumerate(sorted_bm25_indices):
                    if bm25_scores[idx] > 0:
                        bm25_ranks[idx] = rank + 1

        # 3. Reciprocal Rank Fusion (RRF)
        # RRF formula: Score(d) = 1 / (60 + r_dense) + 1 / (60 + r_bm25)
        rrf_k = 60.0
        all_candidate_indices = set(dense_ranks.keys()).union(set(bm25_ranks.keys()))
        scored_candidates = []

        for idx in all_candidate_indices:
            r_dense = dense_ranks.get(idx, 1000)
            r_bm25 = bm25_ranks.get(idx, 1000)
            rrf_score = (1.0 / (rrf_k + r_dense)) + (1.0 / (rrf_k + r_bm25))

            # Retrieve base similarity for score calibration
            dense_dist = idx_to_dist.get(idx, 0.0)

            meta = self.chunk_metadata[idx]
            scored_candidates.append({
                "chunk_id": meta["chunk_id"],
                "document_id": meta["document_id"],
                "document_name": meta["document_name"],
                "chunk_index": meta["chunk_index"],
                "text": meta["text"],
                "score": float(dense_dist), # Raw cosine similarity
                "rrf_score": float(rrf_score)
            })

        # Sort by RRF score descending
        scored_candidates.sort(key=lambda x: x["rrf_score"], reverse=True)
        return scored_candidates[:top_k]

    def compute_similarity(self, text1: str, text2: str) -> float:
        """Compute cosine similarity between two sentences/paragraphs."""
        if not text1.strip() or not text2.strip():
            return 0.0

        embs = self.encode([text1, text2])
        sim = float(np.dot(embs[0], embs[1]))
        return max(0.0, min(1.0, sim))

vector_service = VectorService()
