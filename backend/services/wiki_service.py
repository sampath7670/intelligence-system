import re
import requests
import wikipediaapi
import logging
from config.config import WIKI_USER_AGENT

logger = logging.getLogger(__name__)

class WikiService:
    def __init__(self, user_agent=WIKI_USER_AGENT):
        self.wiki = wikipediaapi.Wikipedia(
            user_agent=user_agent,
            language='en'
        )
        self._cache = {}

    def get_candidate_articles(self, query: str, top_k: int = 6) -> list:
        """
        Search Wikipedia for the query and retrieve up to top_k candidate articles
        with their titles, summaries, and URLs.
        """
        if not query.strip():
            return []

        cache_key = f"{query.strip().lower()}_{top_k}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            search_url = "https://en.wikipedia.org/w/api.php"
            headers = {"User-Agent": WIKI_USER_AGENT}
            
            # Determine search terms: subject phrase if applicable, followed by full query
            search_queries = []
            parts = re.split(r'\b(is|are|was|were|refers to|means|uses|used|enables|grounds)\b', query, maxsplit=1, flags=re.IGNORECASE)
            if len(parts) > 1 and len(parts[0].strip()) >= 3:
                subject_term = parts[0].strip()
                search_queries.append(subject_term)
            if query.strip() not in search_queries:
                search_queries.append(query.strip())

            candidate_titles = []
            for sq in search_queries:
                params = {
                    "action": "query",
                    "list": "search",
                    "srsearch": sq,
                    "format": "json",
                    "utf8": 1
                }
                try:
                    response = requests.get(search_url, params=params, headers=headers, timeout=5)
                    response.raise_for_status()
                    data = response.json()
                    search_results = data.get("query", {}).get("search", [])
                    # Take up to 6 titles per query to capture deep-ranked relevant articles
                    for item in search_results[:6]:
                        title = item.get("title")
                        if title and title not in candidate_titles:
                            candidate_titles.append(title)
                except Exception as search_err:
                    logger.warning(f"Wikipedia search failed for '{sq}': {search_err}")

            if not candidate_titles:
                return []

            candidates = []
            for title in candidate_titles[:top_k]:
                try:
                    page = self.wiki.page(title)
                    if page.exists() and page.summary:
                        candidates.append({
                            "success": True,
                            "title": page.title,
                            "summary": page.summary[:800] + ("..." if len(page.summary) > 800 else ""),
                            "url": page.fullurl
                        })
                except Exception as page_err:
                    logger.warning(f"Error fetching Wikipedia page '{title}': {page_err}")
            self._cache[cache_key] = candidates
            return candidates

        except Exception as e:
            logger.error(f"Error retrieving candidate articles from Wikipedia: {e}", exc_info=True)
            return []

    def verify_fact(self, query: str) -> dict:
        """
        Search Wikipedia for the query, retrieve the top article's summary and URL.
        """
        if not query.strip():
            return {
                "success": False,
                "message": "Query cannot be empty."
            }

        candidates = self.get_candidate_articles(query, top_k=1)
        if candidates:
            return candidates[0]

        return {
            "success": False,
            "message": f"No Wikipedia articles found for '{query}'."
        }

# Global wiki service instance
wiki_service = WikiService()
