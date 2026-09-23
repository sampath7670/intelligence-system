import logging
from typing import List, Dict, Any
import sacrebleu
from rouge_score import rouge_scorer

logger = logging.getLogger(__name__)

class EvaluationService:
    def __init__(self):
        self.rouge = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)

    def evaluate_text(self, candidate: str, references: List[str]) -> Dict[str, Any]:
        """
        Compute objective NLP evaluation metrics (BLEU, chrF, ROUGE-1/2/L)
        comparing candidate generation against gold-standard references.
        """
        if not candidate.strip() or not references:
            return {
                "bleu": 0.0,
                "chrf": 0.0,
                "rouge1": 0.0,
                "rouge2": 0.0,
                "rougeL": 0.0,
                "interpretation": "Insufficient text for evaluation."
            }

        cleaned_refs = [r.strip() for r in references if r.strip()]
        if not cleaned_refs:
            cleaned_refs = [candidate]

        # 1. SacreBLEU (Word-level n-gram precision with brevity penalty)
        try:
            bleu_res = sacrebleu.corpus_bleu([candidate], [[r] for r in cleaned_refs])
            bleu_score = round(bleu_res.score, 2)
        except Exception as e:
            logger.warning(f"BLEU computation error: {e}")
            bleu_score = 0.0

        # 2. chrF (Character n-gram F-score - robust to morphological variation)
        try:
            chrf_res = sacrebleu.corpus_chrf([candidate], [[r] for r in cleaned_refs])
            chrf_score = round(chrf_res.score, 2)
        except Exception as e:
            logger.warning(f"chrF computation error: {e}")
            chrf_score = 0.0

        # 3. ROUGE (Recall-Oriented Understudy for Gisting Evaluation)
        try:
            best_rouge1, best_rouge2, best_rougeL = 0.0, 0.0, 0.0
            for ref in cleaned_refs:
                scores = self.rouge.score(ref, candidate)
                best_rouge1 = max(best_rouge1, scores["rouge1"].fmeasure)
                best_rouge2 = max(best_rouge2, scores["rouge2"].fmeasure)
                best_rougeL = max(best_rougeL, scores["rougeL"].fmeasure)
        except Exception as e:
            logger.warning(f"ROUGE computation error: {e}")
            best_rouge1, best_rouge2, best_rougeL = 0.0, 0.0, 0.0

        # Qualitative interpretation
        if chrf_score >= 50.0 or bleu_score >= 35.0:
            interpretation = "High semantic overlap and strong stylistic alignment with gold-standard professional communication."
        elif chrf_score >= 30.0 or bleu_score >= 15.0:
            interpretation = "Moderate alignment; conveys core intent with acceptable vocabulary variety."
        else:
            interpretation = "Distinct or highly novel phrasing compared to references, maintaining personal conversational style."

        return {
            "bleu": bleu_score,
            "chrf": chrf_score,
            "rouge1": round(best_rouge1 * 100, 2),
            "rouge2": round(best_rouge2 * 100, 2),
            "rougeL": round(best_rougeL * 100, 2),
            "reference_count": len(cleaned_refs),
            "interpretation": interpretation
        }

    def run_benchmark_suite(self, candidate_text: str, conversation_type: str) -> Dict[str, Any]:
        """
        Evaluate candidate text against predefined curated professional benchmarks.
        """
        benchmarks = {
            "linkedin_invitation": [
                "Hi Alex, I came across your work on distributed systems and found your recent engineering insights compelling. I would love to connect and follow your journey.",
                "Hello Alex, I noticed our shared interest in AI and cloud architecture. Given your work in scalable infrastructure, I would be glad to connect here on LinkedIn.",
                "Hi Alex, great meeting you at the summit. I really enjoyed our discussion on RAG pipelines and would love to stay in touch on LinkedIn."
            ],
            "follow_up_email": [
                "Subject: Great connecting at the Tech Summit - Follow up\n\nHi Alex,\nThank you for taking the time to speak with me yesterday regarding AI infrastructure. I found your insights on reducing retrieval latency especially helpful. As discussed, I am attaching my latest project overview. Would you be open to a brief 15-minute sync next week?\n\nBest regards,",
                "Subject: Continuing our conversation on distributed machine learning\n\nHi Alex,\nIt was a pleasure meeting you at the conference. Our discussion on model deployment tradeoffs gave me several actionable takeaways. I would love to keep the conversation going when your schedule allows.\n\nWarmly,"
            ],
            "interview_reply": [
                "Thank you for the opportunity to speak with the engineering team today. I thoroughly enjoyed discussing the architecture of your distributed data pipeline and how my experience with Kafka and PyTorch can directly support your roadmap.",
                "I appreciate the insightful conversation during today's technical interview. Hearing about your focus on latency optimization made me even more enthusiastic about the possibility of contributing to your team."
            ],
            "technical_discussion": [
                "In evaluating retrieval strategies for large language models, hybrid search combining dense embeddings with BM25 offers significant advantages by balancing semantic generalization with exact keyword precision.",
                "When scaling microservices under high concurrency, decoupling asynchronous event producers with Kafka provides durability while minimizing consumer latency."
            ],
            "event_icebreaker": [
                "Hello! Are you attending the session on scalable AI architecture? I have been working on similar distributed systems and would love to hear your take.",
                "Hi there! I noticed your company is scaling cloud infrastructure. How are you approaching observability and automated deployments?"
            ]
        }

        refs = benchmarks.get(conversation_type, benchmarks["event_icebreaker"])
        return self.evaluate_text(candidate_text, refs)

evaluation_service = EvaluationService()
