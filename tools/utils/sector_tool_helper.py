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
        result["error"] = f"Identified sector {sector_name!r} is not in the supported catalog"
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
