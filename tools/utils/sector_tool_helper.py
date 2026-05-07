"""
Sector helper logic used by SectorAnalyst for mapping and parsing.
"""

import json
import logging
import re
from typing import Any

from core.constants import SectorName

logger = logging.getLogger(__name__)


def _parse_json_object(text: str) -> dict[str, Any]:
    """Parse the first JSON object out of an LLM response string."""
    result = {
        "status": "failed",
        "data": None,
        "error": None,
    }

    raw_text = "" if text is None else str(text)

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw_text, flags=re.DOTALL)
        if not match:
            result["error"] = "LLM did not return a JSON object."
            return result

        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            result["error"] = f"Failed to parse JSON object: {exc}"
            return result
    except TypeError as exc:
        result["error"] = f"Invalid JSON input: {exc}"
        return result

    if not isinstance(parsed, dict):
        result["error"] = "LLM JSON response must be a dict."
        return result

    result.update({
        "status": "success",
        "data": parsed,
    })
    return result


def _is_missing(value: Any) -> bool:
    return value is None or str(value).strip().lower() in {"", "n/a", "na", "none", "unknown"}


def build_company_sector_input(company: str, company_sector: dict[str, Any]) -> str:
    """
    Build the free-text sector resolver input from the rough yfinance sector.
    Falls back to the original company/ticker when yfinance has no sector.
    """
    company_sector = company_sector or {}
    parts = []

    if not _is_missing(company_sector.get("sector")):
        parts.append(f"rough_sector: {company_sector['sector']}")

    if not _is_missing(company_sector.get("industry")):
        parts.append(f"industry: {company_sector['industry']}")

    if not _is_missing(company_sector.get("company")):
        parts.append(f"company: {company_sector['company']}")

    if not _is_missing(company_sector.get("business")):
        parts.append(f"business_summary: {company_sector['business']}")

    if not parts:
        parts.append(f"company_or_ticker: {company}")

    return "\n".join(parts)


def format_sector_catalog(sector_catalog: list[dict[str, str]]) -> str:
    """Format the supported sector catalog for the resolver prompt."""
    sector_catalog = sector_catalog or []
    return "\n".join(
        f"- {sector.get('name')}: {sector.get('description')}"
        for sector in sector_catalog
        if isinstance(sector, dict)
    )


def parse_sector_resolver_output(text: str) -> dict[str, Any]:
    """
    Parse and validate the explicit SectorAnalyst resolver LLM output.
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
        result["error"] = f"Unknown sector_name: {sector_name!r}"
        return result

    try:
        confidence = float(parsed.get("confidence", 0))
    except (TypeError, ValueError):
        confidence = 0.0

    result.update({
        "status": "success",
        "sector_name": sector_name,
        "confidence": round(max(0.0, min(1.0, confidence)), 4),
        "reason": str(parsed.get("reason", "")).strip(),
    })
    return result
