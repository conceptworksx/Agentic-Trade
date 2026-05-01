import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Literal


LOG_DIR      = Path("logs")
LOG_LEVEL    = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT   = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT  = "%Y-%m-%d %H:%M:%S"

LOG_FILES = {
    "agent":   LOG_DIR / "agent.log",      # agent reasoning, LLM calls
    "tool":    LOG_DIR / "tool.log",       # tool execution, data fetches
    "retry":   LOG_DIR / "retry.log",      # all retry attempts
    "error":   LOG_DIR / "error.log",      # ERROR and CRITICAL only
    "main":    LOG_DIR / "main.log",       # full run log, all levels
}


_MODULE_ROUTING = {
    "agents":                    "agent",
    "graph":                     "agent",
    "tools":                     "tool",
    "tools.utils.retry_utils":   "retry",
    "core.errors":               "error",
    "__main__":                  "main",
    "main":                      "main",
}


# ─────────────────────────────────────────────────────────────
#  FORMATTERS
# ─────────────────────────────────────────────────────────────

class _ConsoleFormatter(logging.Formatter):
    """
    Coloured formatter for terminal output.
    Uses ANSI codes — works on Linux/Mac terminals and VS Code.
    """
    _COLOURS = {
        logging.DEBUG:    "\033[37m",      # white
        logging.INFO:     "\033[36m",      # cyan
        logging.WARNING:  "\033[33m",      # yellow
        logging.ERROR:    "\033[31m",      # red
        logging.CRITICAL: "\033[1;31m",    # bold red
    }
    _RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        colour  = self._COLOURS.get(record.levelno, self._RESET)
        message = super().format(record)
        return f"{colour}{message}{self._RESET}"


class _FileFormatter(logging.Formatter):
    """Plain formatter for file output — no ANSI codes."""
    pass


# ─────────────────────────────────────────────────────────────
#  HANDLER BUILDERS
# ─────────────────────────────────────────────────────────────

def _make_console_handler(level: int = logging.INFO) -> logging.StreamHandler:
    """Coloured console handler for stdout."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(_ConsoleFormatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    return handler


def _make_file_handler(
    filepath: Path,
    level:    int = logging.DEBUG,
) -> logging.handlers.RotatingFileHandler:
    """
    Rotating file handler.
    Each file rotates at 5MB, keeps 3 backups.
    e.g. agent.log → agent.log.1 → agent.log.2 → agent.log.3
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        filename    = filepath,
        maxBytes    = 5 * 1024 * 1024,   # 5 MB
        backupCount = 3,
        encoding    = "utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(_FileFormatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    return handler


def _make_error_file_handler(filepath: Path) -> logging.handlers.RotatingFileHandler:
    """ERROR-only handler — writes to error.log regardless of which module logs it."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        filename    = filepath,
        maxBytes    = 5 * 1024 * 1024,
        backupCount = 3,
        encoding    = "utf-8",
    )
    handler.setLevel(logging.ERROR)
    handler.setFormatter(_FileFormatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    return handler


# ─────────────────────────────────────────────────────────────
#  SETUP  —  call once at startup in main.py
# ─────────────────────────────────────────────────────────────

def setup_logging(
    level:       str  = LOG_LEVEL,
    console:     bool = True,
    file_output: bool = True,
) -> None:
    """
    Configure logging for the entire project.

    Call this ONCE at the top of main.py before anything else.

    Args:
        level       : Root log level — "DEBUG" | "INFO" | "WARNING" | "ERROR"
                      Overridden by LOG_LEVEL environment variable if set.
        console     : Show coloured logs in terminal (default True).
        file_output : Write logs to files in logs/ directory (default True).

    Log files created (all in logs/):
        main.log    — full run log, every level
        agent.log   — agent reasoning, LLM calls, graph nodes
        tool.log    — tool execution, data fetches, yfinance calls
        retry.log   — every retry attempt with delays
        error.log   — ERROR and CRITICAL from ALL modules

    Example:
        # main.py
        from core.logging_config import setup_logging
        setup_logging()                          # INFO to console + all files
        setup_logging(level="DEBUG")             # verbose mode
        setup_logging(file_output=False)         # console only
    """
    numeric_level = getattr(logging, level, logging.INFO)

    # ── Root logger ───────────────────────────────────────────
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)   # capture everything, handlers filter
    root.handlers.clear()

    # ── Console handler ───────────────────────────────────────
    if console:
        root.addHandler(_make_console_handler(level=numeric_level))

    # ── Per-module file handlers ──────────────────────────────
    if file_output:
        # Full log — everything goes here
        root.addHandler(_make_file_handler(LOG_FILES["main"], level=logging.DEBUG))

        # Error-only — aggregates errors from ALL modules
        root.addHandler(_make_error_file_handler(LOG_FILES["error"]))

        # Per-layer loggers write to their own file AND propagate to root
        # so they also appear in main.log and console
        for module_prefix, file_key in _MODULE_ROUTING.items():
            if file_key in ("main", "error"):
                continue     # already handled by root

            log_path = LOG_FILES[file_key]
            logger   = logging.getLogger(module_prefix)
            logger.addHandler(
                _make_file_handler(log_path, level=logging.DEBUG)
            )
            logger.propagate = True   # still reaches root → console + main.log

    # ── Suppress noisy third-party loggers ───────────────────
    for noisy in ["yfinance", "urllib3", "requests",
                  "peewee", "charset_normalizer"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # ── Startup banner ────────────────────────────────────────
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info(f"  Agentic Trade — logging initialised")
    logger.info(f"  Level   : {level}")
    logger.info(f"  Console : {console}")
    logger.info(f"  Files   : {file_output} → {LOG_DIR.resolve()}")
    logger.info("=" * 60)


# ─────────────────────────────────────────────────────────────
#  get_logger  —  use this everywhere instead of logging.getLogger
# ─────────────────────────────────────────────────────────────

def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger for the calling module.

    Args:
        name (str): Always pass __name__ so the logger
                    is named after the module automatically.

    Usage:
        from core.logging_config import get_logger
        logger = get_logger(__name__)

        logger.debug("Detailed trace — visible only in DEBUG mode")
        logger.info("Normal operation message")
        logger.warning("Something unexpected but recoverable")
        logger.error("Something failed", exc_info=True)   # includes traceback
        logger.critical("Fatal — system cannot continue")
    """
    return logging.getLogger(name)

def bootstrap_standalone(file: str) -> None:
    """
    Call from __main__ blocks when running a file directly.
    Fixes sys.path and initialises logging in one call.

    Usage:
        if __name__ == "__main__":
            from core.logging_config import bootstrap_standalone
            bootstrap_standalone(__file__)
    """
    import sys
    from pathlib import Path

    # Walk up until we find the project root (contains main.py)
    path = Path(file).resolve()
    for parent in path.parents:
        if (parent / "main.py").exists():
            if str(parent) not in sys.path:
                sys.path.insert(0, str(parent))
            break

    setup_logging()