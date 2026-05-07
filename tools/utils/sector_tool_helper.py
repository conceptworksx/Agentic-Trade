"""
Sector helper logic used by SectorAnalyst for mapping and parsing.
Contains internal support functions for API fetching and JSON parsing.
"""

import json
import logging
import re
from typing import Any
from urllib.parse import quote

import httpx

import config.settings as settings
from core.constants import SectorName
from tools.utils.retry_utils import with_retry

logger = logging.getLogger(__name__)


def _parse_json_object(text: str) -> dict[str, Any]:
    """
    Extract and parse the first valid JSON object from a potentially messy LLM response.
    Returns a status dict containing the parsed data or an error message.
    """
    result = {
        "status": "failed",
        "data": None,
        "error": None,
    }

    raw_text = "" if text is None else str(text).strip()

    try:
        # Fast path: exact JSON match
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        # Slow path: find JSON within text blocks or markdown code fences
        match = re.search(r"\{.*\}", raw_text, flags=re.DOTALL)
        if not match:
            result["error"] = "LLM response did not contain a valid JSON object."
            return result

        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            result["error"] = f"Failed to parse identified JSON block: {exc}"
            return result
    except TypeError as exc:
        result["error"] = f"Invalid JSON input type: {exc}"
        return result

    if not isinstance(parsed, dict):
        result["error"] = "Extracted JSON must be an object (dictionary)."
        return result

    result.update({
        "status": "success",
        "data": parsed,
    })
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


def _fetch_sector_data(sector_name: str) -> dict[str, Any]:
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
