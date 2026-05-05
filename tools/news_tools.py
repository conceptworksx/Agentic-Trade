import os
import yfinance as yf
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
    _safe_tavily_search
)
from dotenv import load_dotenv
from tools.utils.retry_utils import retry_fetch
from core.logging import get_logger
from pathlib import Path

logger = get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent  # go to project root
load_dotenv(BASE_DIR / ".env")
 

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



def get_company_news(ticker: str) -> dict:
    """
    Fetch recent company-specific news using Yahoo Finance.

    Args:
        ticker (str): Stock ticker (e.g., "RELIANCE.NS")

    Returns:
        dict with status, ai_summary (empty), articles, and error (if any).
    """
    logger.info(f"Fetching company news for {ticker}")

    result = {
        "status": "",
        "ai_summary": "",   
        "articles": [],
        "error": None
    }

    try:
        yf_news = retry_fetch(
            lambda: yf.Ticker(ticker).get_news(),
            retries=3,
            label=f"yf_news_{ticker}",
            caller="get_company_news"
        )

        if not yf_news:
            result["status"] = "no_news"
            return result

        articles = _extract_news_fields(yf_news[:5])

        result["status"] = "success"
        result["articles"] = articles
        return result

    except Exception as e:
        logger.exception(f"Company news failed for {ticker}")

        result["status"] = "error"
        result["error"] = str(e)
        return result


def get_indian_market_news() -> dict:
    """
    Fetch Indian market news using Tavily.

    Returns:
        dict with status, ai_summary, articles, and error (if any).
    """
    logger.info("Fetching Indian market news")

    result = {
        "status": "",
        "ai_summary": "",
        "articles": [],
        "error": None
    }

    all_articles = []
    summaries = []

    try:
        for tag, query in INDIAN_QUERIES:
            response = _safe_tavily_search(client, query, INDIAN_DOMAINS, tag)

            if response.get("answer"):
                summaries.append(response["answer"])

            formatted = _format_articles(response.get("results", []), tag)
            all_articles.extend(formatted)

        if not all_articles:
            result["status"] = "no_news"
            return result

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

        result["status"] = "success"
        result["ai_summary"] = summaries[0] if summaries else ""
        result["articles"] = _get_top5(filtered)

        return result

    except Exception as e:
        logger.exception("Indian market news failed")

        result["status"] = "error"
        result["error"] = str(e)
        return result


def get_global_market_news() -> dict:
    """
    Fetch global market news using Tavily.

    Returns:
        dict with status, ai_summary, articles, and error (if any).
    """
    logger.info("Fetching global market news")

    result = {
        "status": "",
        "ai_summary": "",
        "articles": [],
        "error": None
    }

    all_articles = []
    summaries = []

    try:
        for tag, query in GLOBAL_QUERIES:
            response = _safe_tavily_search(client, query, GLOBAL_DOMAINS, tag)

            if response.get("answer"):
                summaries.append(response["answer"])

            formatted = _format_articles(response.get("results", []), tag)
            all_articles.extend(formatted)

        if not all_articles:
            result["status"] = "no_news"
            return result

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
                "priority": a["priority"],
            }
            for a in unique if a["score"] >= 3
        ]

        result["status"] = "success"
        result["ai_summary"] = summaries[0] if summaries else ""
        result["articles"] = _get_top5(filtered)

        return result

    except Exception as e:
        logger.exception("Global market news failed")

        result["status"] = "error"
        result["error"] = str(e)
        return result



if __name__ == "__main__":
    import json

    ticker = "RELIANCE.NS"

    print("\n" + "="*60)
    print("TEST 1 — Company News")
    print("="*60)

    company = get_company_news(ticker)
    print("Status:", company["status"])
    for a in company["articles"]:
        print(f"- {a['title']} ({a['source']})")

    print("\n" + "="*60)
    print("TEST 2 — Indian Market News")
    print("="*60)

    india = get_indian_market_news()
    print("Status:", india["status"])
    print("Summary:", (india["ai_summary"][:120] + "...") if india["ai_summary"] else "None")
    for a in india["articles"]:
        print(f"[{a['priority']}] {a['title']}")

    print("\n" + "="*60)
    print("TEST 3 — Global Market News")
    print("="*60)

    global_news = get_global_market_news()
    print("Status:", global_news["status"])
    print("Summary:", (global_news["ai_summary"][:120] + "...") if global_news["ai_summary"] else "None")
    for a in global_news["articles"]:
        print(f"[{a['priority']}] {a['title']}")

    print("\nSaving output to news_test_output.json...")

    with open("news_test_output.json", "w", encoding="utf-8") as f:
        json.dump({
            "company_news": company,
            "indian_news": india,
            "global_news": global_news,
        }, f, indent=2, ensure_ascii=False)

    print("Saved")
