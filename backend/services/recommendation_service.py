import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.models.models import User, Conversation, Suggestion

logger = logging.getLogger(__name__)

class RecommendationService:
    def get_recommendations(self, db: Session, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Generate proactive networking tips, recommended topics, and high-impact questions
        tailored to the user's role, goal, and past successful interactions.
        """
        user = None
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()

        role = user.role if user else "Software Engineer"
        goal = user.networking_goal if user else "Career Growth & Collaboration"
        background = user.technical_background if user else "General Technology"

        # 1. Topic recommendations tailored to role and background
        recommended_topics = self._get_topics_by_role(role, background)

        # 2. Strategy guidance based on networking goal
        strategy_guidance = self._get_strategy_by_goal(goal)

        # 3. High-performing starters extracted from past positive feedback
        top_proven_starters = self._get_proven_starters(db)

        # 4. Proactive questions to ask in professional settings
        recommended_questions = self._get_impactful_questions(role, goal)

        return {
            "user_persona": {
                "role": role,
                "goal": goal,
                "background": background
            },
            "recommended_topics": recommended_topics,
            "strategy_guidance": strategy_guidance,
            "proven_starters": top_proven_starters,
            "recommended_questions": recommended_questions
        }

    def _get_topics_by_role(self, role: str, background: str) -> List[Dict[str, str]]:
        role_lower = role.lower()
        if "data" in role_lower or "machine learning" in role_lower or "ai" in role_lower:
            return [
                {"title": "Retrieval-Augmented Generation (RAG)", "reason": "High industry demand for factual LLM pipelines."},
                {"title": "Agentic Workflows & Multi-Agent Systems", "reason": "Emerging paradigm for automating complex reasoning."},
                {"title": "Model Quantization & Inference Optimization", "reason": "Crucial for cost-effective enterprise AI deployment."}
            ]
        elif "product" in role_lower or "manager" in role_lower:
            return [
                {"title": "AI Product Metrics & User Retention", "reason": "Aligns feature roadmaps with tangible business value."},
                {"title": "Ethical AI & Compliance Frameworks", "reason": "Essential for corporate governance and risk management."},
                {"title": "Cross-Functional Engineering Alignment", "reason": "Fosters high-velocity sprint execution and clarity."}
            ]
        elif "student" in role_lower or "junior" in role_lower:
            return [
                {"title": "Open Source Contributions", "reason": "Best demonstration of practical engineering and collaboration."},
                {"title": "System Design Fundamentals", "reason": "Key evaluation metric in mid and senior engineering interviews."},
                {"title": "Modern Cloud & CI/CD Pipelines", "reason": "High-leverage skillset sought after by top engineering teams."}
            ]
        else: # Software / Cloud / Systems
            return [
                {"title": "Distributed Systems Scalability", "reason": "Core architectural focus for enterprise engineering teams."},
                {"title": "Event-Driven Microservices with Kafka", "reason": "Standard for high-throughput, decoupled system topologies."},
                {"title": "Observability & Site Reliability Engineering (SRE)", "reason": "Vital for maintaining low latency and high availability."}
            ]

    def _get_strategy_by_goal(self, goal: str) -> Dict[str, str]:
        goal_lower = goal.lower()
        if "job" in goal_lower or "career" in goal_lower:
            return {
                "mindset": "Focus on mutual problem-solving and demonstrable impact.",
                "action_item": "Inquire about engineering challenges currently facing their team and articulate how your background directly addresses them.",
                "follow_up_window": "Send a crisp, 3-sentence thank-you message within 24 hours attaching your GitHub / portfolio."
            }
        elif "mentor" in goal_lower:
            return {
                "mindset": "Lead with specific curiosity, not broad career questions.",
                "action_item": "Ask about a specific transition (e.g. IC to Tech Lead) or how they evaluated a past architectural tradeoff.",
                "follow_up_window": "Summarize what you applied from their advice within 2 weeks to build long-term rapport."
            }
        else: # Collaboration / Knowledge Sharing
            return {
                "mindset": "Identify overlapping technical interests and open challenges.",
                "action_item": "Exchange insights on toolchains, benchmarks, or recent publications to establish immediate peer credibility.",
                "follow_up_window": "Share a relevant article, repository, or benchmark link within 48 hours."
            }

    def _get_proven_starters(self, db: Session) -> List[str]:
        """Extract starters that received thumbs-up feedback from the database."""
        proven = []
        try:
            # Check modern conversations with positive feedback
            pos_convos = db.query(Conversation).filter(Conversation.feedback == True).limit(5).all()
            for c in pos_convos:
                proven.append(c.title + ": " + c.generated_content[:120] + "...")

            # Also check legacy suggestions with thumbs up
            suggestions = db.query(Suggestion).all()
            for s in suggestions:
                starters = s.starters
                feedback = s.feedback
                for idx, is_useful in enumerate(feedback):
                    if is_useful and idx < len(starters):
                        proven.append(starters[idx])
        except Exception as e:
            logger.warning(f"Error querying proven starters: {e}")

        if not proven:
            return [
                "I enjoyed your talk on scalable microservices. How did your team navigate consistency tradeoffs across distributed nodes?",
                "I noticed your focus on Retrieval-Augmented Generation. What has been your most effective strategy for mitigating hallucinations in production?",
                "Great meeting you at the summit! What engineering initiative are you most excited to tackle this quarter?"
            ]
        return proven[:4]

    def _get_impactful_questions(self, role: str, goal: str) -> List[str]:
        return [
            "What has been the most surprising technical roadblock your engineering organization encountered recently?",
            "How do your teams balance investing in technical debt refactoring versus shipping immediate feature requests?",
            "What skills or mental models do you find distinguish the top 5% of engineers you collaborate with?",
            "If you were tackling this architecture again from scratch today, what would you do differently?"
        ]

recommendation_service = RecommendationService()
