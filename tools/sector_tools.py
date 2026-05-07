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
    Fetch the rough company sector/industry from yfinance.

    The sector returned here is intentionally raw. SectorAnalyst later maps it
    to the supported Indian sector catalog before fetching the PDF report.
    """
    normalized_ticker = str(ticker).strip().upper()
    logger.info(f"Fetching rough company sector | ticker={normalized_ticker}")

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

        if isinstance(info, dict) and info:
            company_name = info.get("longName", "N/A")
            sector = info.get("sector", "N/A")
            industry = info.get("industry", "N/A")
            business = info.get("longBusinessSummary", "N/A")

            result.update({
                "status": "success",
                "company": company_name,
                "sector": sector,
                "industry": industry,
                "business": business,
            })
        else:
            logger.warning(f"No yfinance info found | ticker={normalized_ticker}")
            result["error"] = "No data found for this ticker"

    except Exception as exc:
        logger.exception(f"Failed to fetch company sector | ticker={normalized_ticker}")
        result["error"] = str(exc)

    return result


@with_retry(retries=3, delay=2.0, backoff=2.0)
def _fetch_sector_api_data(api_url: str, sector_name: str) -> Any:
    with httpx.Client(timeout=120.0) as client:
        response = client.get(api_url)

    if response.status_code >= 400:
        return {"error": f"Sector API returned {response.status_code} for {sector_name}"}

    return response.json()


def fetch_sector_data(sector_name: str) -> dict[str, Any]:
    """
    Fetch the structured PDF/API payload for one validated catalog sector.
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

    valid_sector_names = {sector.value for sector in SectorName}
    if sector_name not in valid_sector_names:
        result["error"] = f"Unknown sector_name: {sector_name!r}"
        return result

    logger.info(f"Fetching sector data | sector={sector_name}")

    try:
        result["data"] = _fetch_sector_api_data(api_url, sector_name)
        result["status"] = "success"
        return result

    except httpx.RequestError as exc:
        logger.error(f"Network error fetching sector data | sector={sector_name} | {exc}")
        result["error"] = f"Network error while fetching sector data: {exc}"
        return result

    except Exception as exc:
        logger.exception(f"Failed to fetch sector data | sector={sector_name}")
        result["error"] = str(exc)
        return result


def fetch_sector_payload(data: dict) -> dict:
    """
    Add sector_data to a resolved-sector payload.

    If sector resolution failed, keep the chain payload structured and mark the
    sector fetch as skipped instead of calling the API with an invalid sector.
    """
    result = {**data}
    resolved_sector = result.get("resolved_sector", {})
    sector_name = resolved_sector.get("sector_name")

    if resolved_sector.get("status") != "success" or not sector_name:
        result["sector_data"] = {
            "status": "skipped",
            "sector": sector_name,
            "api_url": None,
            "data": None,
            "error": resolved_sector.get("error") or "sector_resolution_failed",
        }
        return result

    result["sector_data"] = fetch_sector_data(sector_name)
    return result
