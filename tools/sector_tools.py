"""
Sector data tools used by SectorAnalyst and API endpoints.
Contains main functions called directly by the SectorAnalyst agent.
"""

from typing import Any

import yfinance as yf

from core.constants import SectorName
from core.logging import get_logger
from tools.utils.retry_utils import with_retry
from tools.utils.sector_tool_helper import _fetch_sector_data, _parse_json_object

logger = get_logger(__name__)


@with_retry(retries=3, delay=2.0, backoff=2.0)
def get_company_sector(ticker: str) -> dict[str, Any]:
    """
    Fetch raw company metadata (sector, industry, summary) from yfinance.

    This provides the 'rough' classification that the SectorAnalyst will
    later map to the official supported Indian sector catalog.
    """
    logger.info(f"Fetching yfinance metadata | ticker={ticker}")

    result = {
        "status": "failed",
        "ticker": ticker,
        "company": None,
        "sector": None,
        "industry": None,
        "business": None,
        "error": None,
    }

    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # yfinance may return None or a dict containing error info
        if (
            isinstance(info, dict)
            and info
            and info.get("sector") not in [None, "", "N/A"]
            and info.get("industry") not in [None, "", "N/A"]
        ):

            result.update(
                {
                    "status": "success",
                    "company": info.get("longName", "N/A"),
                    "sector": info.get("sector", "N/A"),
                    "industry": info.get("industry", "N/A"),
                    "business": info.get("longBusinessSummary", "N/A"),
                }
            )
        else:
            logger.warning(
                f"Incomplete or missing metadata from yfinance | ticker={ticker}"
            )
            result["error"] = "Ticker metadata is incomplete or not found."

    except Exception as exc:
        logger.error(f"yfinance error | ticker={ticker} | {exc}")
        result["error"] = f"Failed to retrieve company info: {exc}"

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

    result["sector_data"] = _fetch_sector_data(sector_name)
    return result


def parse_sector_resolver_output(text: str) -> dict[str, Any]:
    """
    Parse and validate the output of the Sector Resolver LLM.
    Ensures the identified sector is within the official SectorName catalog.
    """
    result = {
        "status": "failed",
        "sector_name": None,
        "confidence": 0.0,
        "reason": None,
        "raw_output": text,
        "error": None,
    }

    parsed_result = _parse_json_object(text)
    if parsed_result["status"] != "success":
        result["error"] = parsed_result["error"]
        return result

    parsed = parsed_result["data"]
    sector_name = str(parsed.get("sector_name", "")).strip()
    valid_sector_names = {sector.value for sector in SectorName}

    if sector_name not in valid_sector_names:
        result["error"] = (
            f"Identified sector {sector_name!r} is not in the supported catalog"
        )
        return result

    try:
        confidence = float(parsed.get("confidence", 0))
    except (TypeError, ValueError):
        confidence = 0.0

    result.update(
        {
            "status": "success",
            "sector_name": sector_name,
            "confidence": round(max(0.0, min(1.0, confidence)), 4),
            "reason": str(parsed.get("reason", "")).strip(),
        }
    )
    return result
