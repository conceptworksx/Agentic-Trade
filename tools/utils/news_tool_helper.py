from typing import List, Dict, Optional
import yfinance as yf
from email.utils import parsedate_to_datetime
from core.logging import get_logger
logger = get_logger(__name__)



PRIORITY_ORDER = {"high": 3, "medium": 2, "low": 1}

def _extract_news_fields(news_json):
    """
    Extract and normalize relevant fields from raw Yahoo Finance news data.

    Args:
        news_json (list): Raw news list from yfinance

    Returns:
        List[dict]: Cleaned articles with title, summary, published_at, source, link
    """

    extracted = []

    for item in news_json:
        try:
            content = item.get("content", {})

            extracted.append({
                "title": content.get("title"),
                "summary": content.get("summary") or "No summary available",
                "published_at": content.get("pubDate"),
                "source": content.get("provider", {}).get("displayName"),
            })

        except Exception:
            logger.exception("Extracting news is causing the error.")
            continue

    return extracted


def _to_iso(date_str: str) -> str:
    """Convert Tavily RFC 2822 date to ISO 8601 — same format as yfinance pubDate."""
    try:
        return parsedate_to_datetime(date_str).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        logger.exception("Tavily _to_iso format is confilcting.")
        return None
    

def _get_top5(articles: list) -> list:
    """
    Sort articles by:
      1. Priority descending  (high > medium > low)
      2. Recency descending   (most recent first, used as tiebreaker)
 
    Returns top 5 only.
    """
    return sorted(
        articles,
        key=lambda a: (
            PRIORITY_ORDER.get(a.get("priority", "low"), 0),  # primary sort
            a.get("published_at") or "",            # tiebreaker
        ),
        reverse=True,
    )[:5]


def _format_articles(results: List[Dict], tag: str) -> List[Dict]:
    """Clean and normalize raw Tavily results into uniform article dicts."""
    articles = []
    for r in results:
        snippet = (r.get("content", "") or "").strip()[:300]
        articles.append({
            "title"        : r.get("title", "N/A"),
            "url"          : r.get("url", "N/A"),
            "source"       : r.get("url", "").split("/")[2],
            "date"         : r.get("published_date", "N/A"),
            "snippet"      : snippet,
            "query_source" : tag,
        })
    return articles


def _deduplicate(articles: List[Dict]) -> List[Dict]:
    """Remove duplicate articles by URL."""
    seen, unique = set(), []
    for a in articles:
        if a["url"] not in seen:
            seen.add(a["url"])
            unique.append(a)
    return unique


def _map_priority(score: int, thresholds: tuple) -> str:
    """
    Convert raw score to agent-friendly priority label.
    thresholds = (high_min, medium_min)
    """
    high_min, medium_min = thresholds
    if score >= high_min:
        return "high"
    elif score >= medium_min:
        return "medium"
    else:
        return "low"
    

def _score_indian(article: Dict) -> int:
    """
    Score an article for Indian market relevance.
    Checks title + snippet for signal keywords.
    Penalizes articles clearly about other markets.
    Max possible: 10
    """
    text  = (article["title"] + " " + article["snippet"]).lower()
    score = 0

    if any(k in text for k in ["india", "indian"]):
        score += 3
    if any(k in text for k in ["nifty", "sensex", "nse", "bse"]):
        score += 3
    if any(k in text for k in ["stock", "shares", "earnings", "results", "profit"]):
        score += 2
    if any(k in text for k in ["rbi", "inflation", "rupee", "fii", "dii", "sebi", "policy"]):
        score += 2

    # Penalize articles clearly about non-Indian markets
    if any(k in text for k in ["europe", "wall street", "us markets", "nasdaq", "s&p 500"]):
        score -= 2

    return score


def _score_global(article: Dict) -> int:
    """
    Score an article for global market relevance.
    Uses full phrases instead of short substrings like 'us'
    to avoid false matches inside other words.
    Max possible: 10
    """
    text  = (article["title"] + " " + article["snippet"]).lower()
    score = 0

    # Fed and monetary policy signals
    if any(k in text for k in ["federal reserve", "fed ", "interest rate", "bond yield", "treasury"]):
        score += 3

    # Commodity and macro signals
    if any(k in text for k in ["oil", "crude", "gold", "dollar index", "dxy", "inflation"]):
        score += 3

    # Broad market signals
    if any(k in text for k in ["s&p 500", "nasdaq", "dow jones", "global market", "wall street"]):
        score += 2

    # Major economy mentions — full phrases only, not substrings
    if any(k in text for k in ["united states", "china", "europe", "eurozone", "japan"]):
        score += 2

    # Penalize articles with zero market relevance
    if score == 0:
        score -= 2

    return score