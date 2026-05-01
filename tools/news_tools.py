import os
import yfinance as yf
from typing import List, Dict, Optional, Any
from tavily import TavilyClient
from tools.utils.news_tool_helper import (
    _extract_news_fields,
    _to_iso,
    _get_top5,
    _deduplicate,
    _format_articles,
    _map_priority,
    _score_global,
    _score_indian,
)
from dotenv import load_dotenv
from core.error import handle_tool_errors, DataFetchError, DataParseError
from tools.utils.retry_utils import retry_fetch
from core.logging import get_logger
logger = get_logger(__name__)

load_dotenv(dotenv_path="../.env")  

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
client = TavilyClient(api_key=TAVILY_API_KEY)


INDIAN_QUERIES = [
    ("index_movement", "India stock market news Sensex Nifty today"),
    ("macro_policy",   "India economy RBI policy inflation FII rupee news"),
]
INDIAN_DOMAINS = ["reuters.com", "moneycontrol.com", "business-standard.com", "livemint.com", "m.economictimes.com", "economictimes.indiatimes.com", "financialexpress.com", "cnbctv18.com"]

GLOBAL_QUERIES = [
    ("indices",    "S&P 500 Nasdaq global stock markets trading today"),
    ("fed_macro",  "Federal Reserve interest rates inflation bond yields outlook"),
    ("commodities","oil crude gold dollar global markets today"),
]
GLOBAL_DOMAINS = ["reuters.com", "bloomberg.com", "cnbc.com", "wsj.com", "marketwatch.com", "ft.com"]


def _safe_tavily_search(query: str, domains: List[str], tag: str) -> Dict[str, Any]:
    """Helper to handle raw Tavily network calls with error logging."""
    try:
        return client.search(
            query=query,
            search_depth="advanced",
            topic="news",
            max_results=7,
            include_domains=domains,
            include_answer=True,
        )
    except Exception as exc:
        logger.error(f"Tavily API call failed for query '{query}': {exc}")
        return {"results": [], "answer": None}


def get_indian_market_news() -> Dict[str, Any]:
    """Fetch broad Indian stock market news."""
    all_articles = []
    summaries = []

    for tag, query in INDIAN_QUERIES:
        response = _safe_tavily_search(query, INDIAN_DOMAINS, tag)
        
        if response.get("answer"):
            summaries.append(response["answer"])
        
        formatted = _format_articles(response.get("results", []), tag)
        all_articles.extend(formatted)

    if not all_articles:
        return {"status": "no_news", "articles": []}

    try:
        unique = _deduplicate(all_articles)
        for a in unique:
            a["score"] = _score_indian(a)
            a["priority"] = _map_priority(a["score"], thresholds=(8, 5))

        filtered = [
            {
                "title": a["title"],
                "source": a["source"],
                "published_at": _to_iso(a["date"]),
                "summary": a["snippet"],
                "priority": a["priority"],
            }
            for a in unique if a["score"] >= 3
        ]
        

        return {
            "status": "success",
            "ai_summary": summaries[0] if summaries else None,
            "articles": _get_top5(filtered),
        }
    except Exception as exc:
        logger.exception("Failed to parse Indian market news")
        raise DataParseError("Failed to parse Indian market news", original=exc)


def get_global_market_news() -> Dict[str, Any]:
    """Fetch global financial market news."""
    all_articles = []
    summaries = []
    
    for tag, query in GLOBAL_QUERIES:
        response = _safe_tavily_search(query, GLOBAL_DOMAINS, tag)
        
        if response.get("answer"):
            summaries.append(response["answer"])
            
        formatted = _format_articles(response.get("results", []), tag)
        all_articles.extend(formatted)

    if not all_articles:
        return {"status": "no_news", "articles": []}

    try:
        unique = _deduplicate(all_articles)
        for a in unique:
            a["score"] = _score_global(a)
            a["priority"] = _map_priority(a["score"], thresholds=(8, 5))
    
        filtered = [
            {
                "title": a["title"],
                "source": a["source"],
                "published_at": _to_iso(a["date"]),
                "summary": a["snippet"],
                "priority": a["priority"]
            }
            for a in unique if a["score"] >= 3
        ]
    
        return {
            "status": "success",
            "ai_summary": summaries[0] if summaries else None,
            "articles": _get_top5(filtered),
        }
    except Exception as exc:
        logger.exception("Failed to parse global market news")
        raise DataParseError("Failed to parse global market news", original=exc)


@handle_tool_errors("get_news_snapshot")
def get_news_snapshot(ticker: str) -> dict[str, Any]:
    """
    Fetch a unified news snapshot for a stock.

    Combines:
    - Company news (Yahoo Finance)
    - Indian market news (Tavily)
    - Global market news (Tavily)

    Args:
        ticker: Yahoo Finance ticker (e.g. RELIANCE.NS)

    Returns:
        {
            "ticker": str,
            "company_news": { "status", "ai_summary", "articles" },
            "indian_news": { "status", "ai_summary", "articles" },
            "global_news": { "status", "ai_summary", "articles" }
        }

    Notes:
        - Articles are pre-scored and filtered (only high-signal included)
        - Each article has: title, source, published_at, summary, priority
        - Use for sentiment + macro + catalyst detection
    """
    logger.info(f"Compiling full news snapshot for {ticker}")
    
    try:
   
        yf_news = retry_fetch(
            lambda: yf.Ticker(ticker).get_news(),
            retries=3,
            label=f"yf_news_{ticker}",
            caller="get_news_snapshot"
        )
        company_results = {
            "status": "success",
            "articles": _extract_news_fields(yf_news[:5])
        }
    except Exception as e:
        logger.warning(f"Company news failed after retries for {ticker}: {e}")
        company_results = {"status": "no_news", "articles": []}

    indian_news = get_indian_market_news()
    logger.info("get_indian_news processed successfully")
    global_news = get_global_market_news()
    logger.info("get_global_market_news processed successfully")

    return {
        "ticker": ticker,
        "company_news": company_results,
        "indian_news": indian_news,
        "global_news": global_news,
    }

if __name__ == "__main__":
    from core.logging import bootstrap_standalone
    bootstrap_standalone(__file__)
    import json

    logger.info("Starting news snapshot test run...")

    test_ticker = "RELIANCE.NS"

    try:
        logger.info(f"Fetching full news snapshot for {test_ticker}")
        snapshot = get_news_snapshot(test_ticker)

    except Exception:
        logger.exception("News snapshot generation failed")
        raise 

    def safe_json(obj):
        if hasattr(obj, "tolist"): 
            return obj.tolist()
        return str(obj)

    try:
        output = json.dumps(snapshot, indent=2, ensure_ascii=False, default=safe_json)
    except Exception:
        logger.exception("JSON serialization failed")
        raise

  
    try:
        logger.info("Printing summarized output...")

        logger.info(f"Ticker: {snapshot.get('ticker')}")

        for section in ["company_news", "indian_news", "global_news"]:
            data = snapshot.get(section, {})
            logger.info(f"{section} → status: {data.get('status')} | articles: {len(data.get('articles', []))}")

    except Exception:
        logger.warning("Failed to print summary view")


    output_path = "news_snapshot.json"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output)
    logger.info(f"Saved → {output_path}")


    logger.info("News snapshot pipeline completed successfully")

