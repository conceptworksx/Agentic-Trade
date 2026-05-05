"""
Sector catalog, LLM builder, and sector-resolution logic.
"""

import json
import logging
import os
import re
from core.constants import SectorName, SECTOR_CATALOG, get_sector_catalog
from functools import lru_cache
from typing import Any

from langchain_core.messages import SystemMessage, HumanMessage

from config.settings import settings, model

logger = logging.getLogger(__name__)


# ── LLM Helpers ───────────────────────────────────
#
# These are intentionally SYNC.
# BaseAgent._invoke() is sync; ToolNode calls tools sync.
# Groq's .invoke() (not .ainvoke()) is used throughout.


def configure_langsmith() -> None:
    """Apply LangSmith env vars before any LangChain model call."""
    os.environ["LANGCHAIN_TRACING_V2"] = str(settings.LANGCHAIN_TRACING_V2).lower()
    os.environ["LANGCHAIN_API_KEY"]     = settings.LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"]     = settings.LANGCHAIN_PROJECT
    os.environ["LANGCHAIN_ENDPOINT"]    = settings.LANGCHAIN_ENDPOINT



def _parse_json_object(text: str) -> dict[str, Any]:
    """Parse the first JSON object out of an LLM response string."""
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise ValueError("LLM did not return a JSON object.")
        parsed = json.loads(match.group(0))

    if not isinstance(parsed, dict):
        raise ValueError("LLM JSON response must be a dict.")
    return parsed


# ── Core resolver (sync) ───────────────────────────────────────────────────────

def select_sector_from_catalog(
    sector_input: str,
    sector_catalog: list[dict[str, str]],
) -> dict[str, Any]:
    """
    Resolve a free-text sector phrase to exactly one catalog sector name.

    Uses a bare Groq call (sync .invoke()) so it is safe to call from
    ToolNode and BaseAgent._invoke() without async / event-loop conflicts.

    Returns:
        {
            "sector_name": str,   # exact SectorName value
            "confidence":  float, # 0.0-1.0
            "reason":      str,
        }

    Raises:
        ValueError if catalog is empty or LLM returns an unknown sector.
    """
    if not sector_catalog:
        raise ValueError("Sector catalog is empty — cannot resolve sector.")

    configure_langsmith()
    llm = model

    sector_names = [s["name"] for s in sector_catalog]
    sectors_block = "\n".join(
        f"- name: {s['name']}\n  description: {s['description']}"
        for s in sector_catalog
    )

    system_content = (
        "You select the single best matching sector for a user input.\n"
        "Choose exactly one sector from the provided sector list.\n"
        "Return strict JSON only — no markdown, no preamble — with these keys:\n"
        '  "sector_name": string  — one exact name from the sector list\n'
        '  "confidence":  number  — between 0 and 1\n'
        '  "reason":      string  — one short sentence\n'
    )

    human_content = (
        f"Sector list:\n{sectors_block}\n\n"
        f"User sector input:\n{sector_input}"
    )

    config = {
        "run_name": "select_sector_from_catalog",
        "tags": ["sector-resolution"],
        "metadata": {
            "sector_input":  sector_input,
            "sector_count":  len(sector_catalog),
            "model":         settings.GROQ_MODEL,
        },
    }

    logger.info(f"Resolving sector for input: {sector_input!r}")
    response = llm.invoke(                          # ← sync, not ainvoke
        [
            SystemMessage(content=system_content),
            HumanMessage(content=human_content),
        ],
        config=config,
    )

    parsed      = _parse_json_object(response.content)
    sector_name = str(parsed.get("sector_name", "")).strip()

    if sector_name not in sector_names:
        raise ValueError(
            f"LLM returned unknown sector_name {sector_name!r}. "
            f"Expected one of: {sector_names}"
        )

    try:
        confidence = float(parsed.get("confidence", 0))
    except (TypeError, ValueError):
        confidence = 0.0

    return {
        "sector_name": sector_name,
        "confidence":  round(max(0.0, min(1.0, confidence)), 4),
        "reason":      str(parsed.get("reason", "")).strip(),
    }