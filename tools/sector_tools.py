"""
Sector data tools used by SectorAnalyst and API endpoints.
"""

from typing import Any
from urllib.parse import quote

import httpx
import yfinance as yf

from core.logging import get_logger

import config.settings as settings
from core.constants import SectorName
from tools.utils.retry_utils import with_retry

logger = get_logger(__name__)


@with_retry(retries=3, delay=2.0, backoff=2.0)
def get_company_sector(ticker: str) -> dict[str, Any]:
    """
    Fetch raw company metadata (sector, industry, summary) from yfinance.
    
    This provides the 'rough' classification that the SectorAnalyst will 
    later map to the official supported Indian sector catalog.
    """
    normalized_ticker = str(ticker).strip().upper()
    logger.info(f"Fetching yfinance metadata | ticker={normalized_ticker}")

    result = {
        "status": "failed",
        "ticker": normalized_ticker,
        "company": None,
        "sector": None,
        "industry": None,
        "business": None,
        "error": None,
    }

    try:
        stock = yf.Ticker(normalized_ticker)
        info = stock.info

        # yfinance may return None or a dict containing error info
        if info and isinstance(info, dict) :
            result.update({
                "status": "success",
                "company": info.get("longName", "N/A"),
                "sector": info.get("sector", "N/A"),
                "industry": info.get("industry", "N/A"),
                "business": info.get("longBusinessSummary", "N/A"),
            })
        else:
            logger.warning(f"Incomplete or missing metadata from yfinance | ticker={normalized_ticker}")
            result["error"] = "Ticker metadata is incomplete or not found."

    except Exception as exc:
        logger.error(f"yfinance error | ticker={normalized_ticker} | {exc}")
        result["error"] = f"Failed to retrieve company info: {exc}"

    return result


@with_retry(retries=3, delay=2.0, backoff=2.0)
def _fetch_sector_api_data(api_url: str, sector_name: str) -> Any:
    """Internal helper to execute the HTTP request to the PDF/Sector API."""
    with httpx.Client(timeout=120.0) as client:
        response = client.get(api_url)

    if response.status_code >= 400:
        logger.error(f"API error {response.status_code} | sector={sector_name}")
        return {"error": f"Sector API returned {response.status_code}"}

    return response.json()


def fetch_sector_data(sector_name: str) -> dict[str, Any]:
    """
    Fetch the structured PDF analysis payload for a validated catalog sector.
    """
    sector_name = str(sector_name).strip()
    api_path = f"/pdf/{quote(sector_name, safe='')}"
    api_url = f"{settings.API_BASE_URL.rstrip('/')}{api_path}"
    
    result = {
        "status": "failed",
        "sector": sector_name,
        "api_url": api_url,
        "data": None,
        "error": None,
    }

    # Final safety check against the official sector list
    valid_sector_names = {sector.value for sector in SectorName}
    if sector_name not in valid_sector_names:
        result["error"] = f"Sector {sector_name!r} is not in the supported catalog"
        return result

    logger.info(f"Requesting sector report | sector={sector_name}")

    try:
        result["data"] = _fetch_sector_api_data(api_url, sector_name)
        if isinstance(result["data"], dict) and "error" in result["data"]:
             result["error"] = result["data"]["error"]
        else:
            result["status"] = "success"
        return result

    except httpx.RequestError as exc:
        logger.error(f"Network error | sector={sector_name} | {exc}")
        result["error"] = f"Network connection failed: {exc}"
        return result

    except Exception as exc:
        logger.exception(f"Unexpected error fetching sector data | sector={sector_name}")
        result["error"] = f"An unexpected error occurred: {exc}"
        return result


def fetch_sector_payload(data: dict) -> dict:
    """
    Adapter function for the LangChain pipeline to inject sector_data.
    
    If prior sector resolution failed, it skips the API call to maintain 
    efficiency and structured error reporting.
    """
    result = {**data}
    resolved_sector = result.get("resolved_sector", {})
    sector_name = resolved_sector.get("sector_name")

    if resolved_sector.get("status") != "success" or not sector_name:
        logger.warning(f"Skipping sector fetch | reason=resolution_failed")
        result["sector_data"] = {
            "status": "skipped",
            "sector": sector_name,
            "api_url": None,
            "data": None,
            "error": resolved_sector.get("error") or "Sector resolution failed",
        }
        return result

    result["sector_data"] = fetch_sector_data(sector_name)
    return result
