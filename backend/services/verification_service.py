import re
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.services.vector_service import vector_service
from backend.services.wiki_service import wiki_service
from backend.models.models import VerificationRecord

logger = logging.getLogger(__name__)

class VerificationService:
    def __init__(self, high_threshold: float = 0.55, medium_threshold: float = 0.35):
        self.high_threshold = high_threshold
        self.medium_threshold = medium_threshold

    def extract_claims(self, text: str) -> List[str]:
        """
        Split a block of text into atomic verifiable sentences/propositions.
        """
        if not text:
            return []
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        claims = [s.strip() for s in sentences if len(s.strip()) > 15]
        return claims if claims else [text.strip()]

    def compute_evidence_alignment(self, claim: str, passage: str) -> tuple:
        """
        Compute fine-grained semantic alignment between a claim and an evidence passage.
        Evaluates both whole-passage topical alignment and sentence-level proposition alignment,
        returning the maximum similarity score and the best corroborated excerpt.
        """
        if not passage.strip() or not claim.strip():
            return 0.0, ""

        # 1. Full passage context similarity
        full_sim = vector_service.compute_similarity(claim, passage)

        # 2. Extract atomic sentences from passage
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', passage) if len(s.strip()) > 15]
        if not sentences:
            return full_sim, passage

        best_sent = ""
        best_sent_sim = 0.0
        for s in sentences:
            s_sim = vector_service.compute_similarity(claim, s)
            if s_sim > best_sent_sim:
                best_sent_sim = s_sim
                best_sent = s

        # When an individual sentence strongly corroborates the claim, prioritize sentence score
        if best_sent_sim > full_sim:
            return best_sent_sim, best_sent
        return full_sim, passage

    def verify_claim(self, claim: str, db: Optional[Session] = None, check_wiki: bool = True) -> Dict[str, Any]:
        """
        Verify a technical or professional statement against the internal Knowledge Repository
        and Wikipedia, generating an explainable confidence score and citations.
        """
        if not claim.strip():
            return {
                "claim": claim,
                "verdict": "UNVERIFIED",
                "confidence_score": 0.0,
                "confidence_pct": 0,
                "explanation": "Claim is empty.",
                "sources": []
            }

        sources = []
        max_similarity = 0.0
        best_evidence_text = ""
        best_source_name = ""

        # 1. Search Knowledge Repository (FAISS + BM25)
        if db is not None:
            try:
                repo_results = vector_service.search(db, claim, top_k=3, hybrid=True)
                for item in repo_results:
                    sim, evidence_excerpt = self.compute_evidence_alignment(claim, item["text"])
                    if sim > max_similarity:
                        max_similarity = sim
                        best_evidence_text = evidence_excerpt
                        best_source_name = item["document_name"]
                    
                    sources.append({
                        "type": "Internal Document",
                        "name": item["document_name"],
                        "snippet": evidence_excerpt[:220] + ("..." if len(evidence_excerpt) > 220 else ""),
                        "similarity": round(sim, 3),
                        "url": None
                    })
            except Exception as e:
                logger.error(f"Error querying vector repository for claim: {e}", exc_info=True)

        # 2. Query Wikipedia if internal score is moderate/low or check_wiki is enabled
        if check_wiki and max_similarity < self.high_threshold:
            try:
                candidates = []
                if hasattr(wiki_service, "get_candidate_articles"):
                    candidates = wiki_service.get_candidate_articles(claim, top_k=6)

                if not candidates:
                    single = wiki_service.verify_fact(claim)
                    if single.get("success"):
                        candidates = [single]

                for wiki_res in candidates:
                    wiki_summary = wiki_res.get("summary", "")
                    if not wiki_summary:
                        continue
                    wiki_sim, wiki_evidence = self.compute_evidence_alignment(claim, wiki_summary)
                    if wiki_sim > max_similarity:
                        max_similarity = wiki_sim
                        best_evidence_text = wiki_evidence
                        best_source_name = f"Wikipedia: {wiki_res.get('title')}"

                    sources.append({
                        "type": "Wikipedia",
                        "name": wiki_res.get("title", "Wikipedia Article"),
                        "snippet": wiki_evidence[:220] + ("..." if len(wiki_evidence) > 220 else ""),
                        "similarity": round(wiki_sim, 3),
                        "url": wiki_res.get("url")
                    })
            except Exception as e:
                logger.warning(f"Wikipedia verification failed for query '{claim}': {e}")

        # Compute calibrated confidence score
        # When information is correct / corroborated by evidence, confidence is significantly elevated
        corroborating_sources = [s for s in sources if s.get("similarity", 0.0) >= 0.35]
        source_count_boost = min(0.04, len(corroborating_sources) * 0.02)

        if max_similarity >= self.high_threshold:
            # Information is verified / correct: scale into the high confidence range (0.88 - 0.98, i.e. 88% - 98%)
            norm = min(1.0, (max_similarity - self.high_threshold) / max(0.01, 1.0 - self.high_threshold))
            calibrated_conf = 0.88 + (0.08 * norm) + source_count_boost
            final_confidence = min(0.98, max(0.85, round(calibrated_conf, 2)))
            verdict = "VERIFIED"
            explanation = (
                f"High confidence ({int(final_confidence*100)}%). Statement strongly aligns with verified evidence from "
                f"'{best_source_name}'. Key technical concepts and context are corroborated."
            )
        elif max_similarity >= self.medium_threshold:
            # Partially supported: moderate confidence (0.60 - 0.84, i.e. 60% - 84%)
            norm = (max_similarity - self.medium_threshold) / max(0.01, self.high_threshold - self.medium_threshold)
            calibrated_conf = 0.60 + (0.22 * norm) + (source_count_boost * 0.5)
            final_confidence = min(0.84, max(0.55, round(calibrated_conf, 2)))
            verdict = "PARTIALLY_SUPPORTED"
            explanation = (
                f"Moderate confidence ({int(final_confidence*100)}%). Statement is partially supported by "
                f"'{best_source_name or 'retrieved documents'}', but specific technical assertions may require further clarification."
            )
        else:
            # Unverified / insufficient evidence: low confidence (0.05 - 0.50, i.e. 5% - 50%)
            norm = max(0.0, max_similarity / self.medium_threshold) if self.medium_threshold > 0 else 0.0
            calibrated_conf = max(0.05, min(0.50, norm * 0.45))
            final_confidence = round(calibrated_conf, 2)
            verdict = "UNVERIFIED"
            explanation = (
                f"Low confidence ({int(final_confidence*100)}%). Insufficient direct evidence found in internal knowledge base "
                "or standard encyclopedic sources to corroborate this claim."
            )

        # Sort sources by similarity descending and cap to top 4
        sources.sort(key=lambda s: s.get("similarity", 0.0), reverse=True)
        sources = sources[:4]

        result = {
            "claim": claim,
            "verdict": verdict,
            "confidence_score": final_confidence,
            "confidence_pct": int(final_confidence * 100),
            "explanation": explanation,
            "best_evidence": best_evidence_text[:300] if best_evidence_text else None,
            "sources": sources
        }

        # Log record in database if session available
        if db is not None:
            try:
                record = VerificationRecord(
                    claim=claim,
                    verdict=verdict,
                    confidence_score=final_confidence,
                    explanation=explanation
                )
                record.sources = sources
                db.add(record)
                db.commit()
                db.refresh(record)
                result["id"] = record.id
            except Exception as e:
                db.rollback()
                logger.warning(f"Could not persist verification record: {e}")

        return result

    def verify_conversation(self, generated_text: str, db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Decomposes a generated conversation into key claims and evaluates overall factual accuracy.
        """
        claims = self.extract_claims(generated_text)
        if not claims:
            return {
                "overall_verdict": "VERIFIED",
                "overall_confidence": 0.85,
                "claims_evaluated": 0,
                "claim_results": []
            }

        claim_results = []
        confidences = []
        for c in claims[:4]: # evaluate top claims to stay performant
            res = self.verify_claim(c, db=db, check_wiki=True)
            claim_results.append(res)
            confidences.append(res["confidence_score"])

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.85
        overall_verdict = (
            "VERIFIED" if avg_confidence >= 0.80
            else "PARTIALLY_SUPPORTED" if avg_confidence >= 0.55
            else "UNVERIFIED"
        )

        all_sources = []
        seen_names = set()
        for r in claim_results:
            for s in r.get("sources", []):
                if s["name"] not in seen_names:
                    all_sources.append(s)
                    seen_names.add(s["name"])

        return {
            "overall_verdict": overall_verdict,
            "overall_confidence": round(avg_confidence, 2),
            "confidence_pct": int(avg_confidence * 100),
            "claims_evaluated": len(claim_results),
            "sources": all_sources[:4],
            "claim_results": claim_results
        }

verification_service = VerificationService()
