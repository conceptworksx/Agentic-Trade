"""
Sector snapshot tool — exposed to SectorAnalyst via BaseAgent.tools.
"""

import json
import logging
from typing import Any
from urllib.parse import quote

import httpx

from core.error import handle_tool_errors

from config.settings import settings
from core.constants import SectorName, get_sector_catalog
from tools.utils.sector_tool_helper import select_sector_from_catalog

logger = logging.getLogger(__name__)


# ── LangChain tool (used by SectorAnalyst via BaseAgent.tools) ─────────────────

@handle_tool_errors("get_sector_snapshot")
def get_sector_snapshot(sector_input: str) -> str: 

    """
    Resolve a sector name or phrase to one of the 44 supported sectors,
    fetch that sector's PDF report from the internal API, and return
    a structured snapshot string for the agent to analyse.

    Args:
        sector_input: Free-text sector name or phrase, e.g. "banking",
                      "renewable energy", "IT services", "pharma".

    Returns:
        A formatted string containing the resolved sector name,
        resolution confidence, and the full API payload — ready for
        the agent LLM to summarise and reason over.
    """

    # ── Step 1: Resolve free-text input → exact catalog sector ────────────────
    resolved = select_sector_from_catalog(
        sector_input=sector_input,
        sector_catalog=get_sector_catalog(),
    )
    sector_name = resolved["sector_name"]

    # Validate against enum — raises ValueError immediately if somehow bad
    SectorName(sector_name)

    logger.info(
        f"Sector resolved: {sector_input!r} → {sector_name!r} "
        f"(confidence={resolved['confidence']})"
    )

    # ── Step 2: Fetch sector PDF report from internal API ─────────────────────
    api_path = f"/pdf/{quote(sector_name, safe='')}"
    api_url  = f"{settings.API_BASE_URL.rstrip('/')}{api_path}"

    try:
        # sync httpx — no event loop conflict with BaseAgent._invoke()
        with httpx.Client(timeout=120.0) as client:
            response = client.get(api_url)
            response.raise_for_status()
        api_output = response.json()
    except httpx.HTTPStatusError as exc:
        logger.error(f"API call failed for sector {sector_name!r}: {exc}")
        raise RuntimeError(
            f"Sector API returned {exc.response.status_code} for {sector_name!r}. "
            "Cannot generate snapshot."
        ) from exc
    except httpx.RequestError as exc:
        logger.error(f"Network error fetching sector {sector_name!r}: {exc}")
        raise RuntimeError(
            f"Network error while fetching sector data for {sector_name!r}: {exc}"
        ) from exc

    # ── Step 3: Format result as a string for the agent LLM ───────────────────
    #
    # ToolMessage.content must be a string — the agent LLM reads this and
    # decides what to say to the user.  We give it enough structure to reason
    # over without flooding the context window.
    snapshot = {
        "resolved_sector": sector_name,
        "confidence":       resolved["confidence"],
        "resolution_reason": resolved["reason"],
        "api_url":          api_url,
        "data":             api_output,
    }

    return json.dumps(snapshot, ensure_ascii=False, indent=2)


# ── Internal helper (kept for non-agent callers, e.g. REST endpoints) ─────────
#
# resolve_sector_tool() is the original async function used by the FastAPI layer.
# It is preserved here so existing API routes keep working unchanged.
# It does NOT use get_sector_snapshot — it has its own httpx async call.


async def resolve_sector_tool(sector_input: str) -> dict[str, Any]:
    """
    Async version for FastAPI / non-agent callers.

    Resolves sector and calls the PDF API.  Not used by BaseAgent/ToolNode.
    Uses the same select_sector_from_catalog() helper but runs it via
    asyncio.to_thread so the sync Groq call doesn't block the event loop.
    """
    import asyncio

    # Run the sync resolver in a thread — keeps FastAPI event loop unblocked
    resolved = await asyncio.to_thread(
        select_sector_from_catalog,
        sector_input=sector_input,
        sector_catalog=get_sector_catalog(),
    )
    sector_name = resolved["sector_name"]
    SectorName(sector_name)

    api_path = f"/pdf/{quote(sector_name, safe='')}"
    api_url  = f"{settings.API_BASE_URL.rstrip('/')}{api_path}"

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.get(api_url)
        response.raise_for_status()

    return {
        "input_sector":    sector_input,
        "selected_sector": resolved,
        "api_path":        api_path,
        "api_url":         api_url,
        "api_output":      response.json(),
    }