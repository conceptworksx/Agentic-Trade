import yfinance as yf


def extract_news_fields(news_json):
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
                "link": content.get("canonicalUrl", {}).get("url")
            })

        except Exception:
            continue

    return extracted



def get_company_news(ticker_symbol: str, limit: int = 5):
    """
    Fetch latest news for a given stock ticker from Yahoo Finance.

    Args:
        ticker_symbol (str): Stock ticker (e.g., "RELIANCE.NS")
        limit (int): Max number of articles to return

    Returns:
        dict: {
            "status": "success" | "no_news" | "error",
            "articles": List[dict]
        }

    Notes:
        Assumes news is returned in descending chronological order.
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        news = ticker.get_news()

        if not news:
            return {
                "status": "no_news",
                "articles": []
            }

        news = news[:limit]

        return {
            "status": "success",
            "articles": extract_news_fields(news)
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


# Example
if __name__ == "__main__":
    print(get_company_news("RELIANCE.NS", limit=5))