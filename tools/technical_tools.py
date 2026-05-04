import json
import warnings
import pandas as pd 
import yfinance as yf 
import ta
from typing import Any
from tools.utils.technical_tool_helper import (
    _compute_mfi_condition_signal,
    _compute_rsi_condition,
    _compute_trend_alignment

)
from core.error import (
    handle_tool_errors,
    DataFetchError,
    DataParseError,
    MaxRetriesExceeded,
    AgentError,
)
from tools.utils.retry_utils import with_retry
from core.logging import get_logger
logger = get_logger(__name__)

warnings.filterwarnings("ignore")


@with_retry(retries=3, delay=2.0, backoff=2.0)
def fetch_df(ticker: str, period: str = "1y", interval: str = "1d") -> dict[str, Any]:
    """Fetch historical OHLCV data safely for agent pipelines."""

    logger.debug(f"Downloading OHLCV data | ticker={ticker}")

    result = {
        "data": None,
        "status": "failed",
        "error": None,
        "ticker": ticker,
        "source": "yfinance",
    }

    try:
        df = yf.download(
            ticker,
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False,
        )
    except Exception as exc:
        logger.exception(f"yfinance.download failed | ticker={ticker} | {exc}")
        result["error"] = f"download_failed: {exc}"
        return result

    if df is None or df.empty:
        logger.warning(f"Empty DataFrame | ticker={ticker}")
        result["error"] = "empty_dataframe"
        return result

    try:
        df.index = pd.to_datetime(df.index).tz_localize(None)
        df.sort_index(inplace=True)

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

    except Exception as exc:
        logger.exception(f"Normalization failed | ticker={ticker} | {exc}")
        result["error"] = f"parse_error: {exc}"
        result["data"] = df 
        result["status"] = "partial"
        return result

    logger.info(f"Fetched {len(df)} bars | ticker={ticker}")

    result["data"] = df
    result["status"] = "ok"
    return result


def compute_moving_averages(df: pd.DataFrame) -> dict[str, Any]:
    """
    Compute 10, 50, 100, and 200-day simple moving averages.
    """

    logger.debug("Computing moving averages")

    result = {
        "ma10": None,
        "ma50": None,
        "ma100": None,
        "ma200": None,
        "price_vs_ma10": None,
        "price_vs_ma50": None,
        "price_vs_ma100": None,
        "price_vs_ma200": None,
        "golden_cross": None,
        "death_cross": None,
        "trend_alignment": None,
        "status": "failed",
        "error": None,
    }

    try:
        if "Close" not in df:
            result["error"] = "Invalid Dataframe"
            return result

        close = df["Close"]
        if len(close) == 0:
            result["error"] = "No price data available"
            return result

        price = float(close.iloc[-1])
        above_count = 0
        valid_mas = 0

        for w in [10, 50, 100, 200]:
            try:
                raw = close.rolling(w).mean().iloc[-1]
                val = float(raw) if not pd.isna(raw) else None

                result[f"ma{w}"] = round(val, 2) if val is not None else None

                if val is not None:
                    result[f"price_vs_ma{w}"] = "ABOVE" if price > val else "BELOW"
                    above_count += int(price > val)
                    valid_mas += 1

            except Exception as e:
                logger.warning(f"MA{w} computation failed: {e}")
                continue

        ma50 = result["ma50"]
        ma200 = result["ma200"]

        result["golden_cross"] = bool(ma50 is not None and ma200 is not None and ma50 > ma200)
        result["death_cross"] = bool(ma50 is not None and ma200 is not None and ma50 < ma200)

        result["trend_alignment"] = (
            _compute_trend_alignment(above_count) if valid_mas > 0 else "UNKNOWN"
        )

        result["status"] = "ok" if valid_mas == 4 else "partial"

        logger.debug(
            f"Moving averages computed | status={result['status']} "
            f"alignment={result['trend_alignment']}"
        )

        return result

    except Exception as exc:
        logger.exception(f"Unexpected failure in MA computation: {exc}")
        result["error"] = str(exc)
        result["status"] = "failed"
        return result


def compute_rsi(df: pd.DataFrame, window: int = 14) -> dict[str, Any]:
    """
    Compute RSI and derive overbought / oversold / divergence signals.
    """

    logger.debug(f"Computing RSI | window={window}")

    result = {
        "value": None,
        "condition": None,
        "trending_up": None,
        "bull_divergence": None,
        "bear_divergence": None,
        "status": "failed",
        "error": None,
    }

    try:
        if "Close" not in df:
            result["error"] = "invalid_dataframe_Close_is_not_present"
            return result

        close = df["Close"]

        if len(close) < window + 2:
            result["error"] = "insufficient_data_for_rsi"
            return result

        rsi_series = ta.momentum.RSIIndicator(close, window=window).rsi()

        if rsi_series.isna().all():
            result["error"] = "rsi_all_nan"
            return result

        cur = float(rsi_series.iloc[-1])
        prv = float(rsi_series.iloc[-2])

        condition = _compute_rsi_condition(cur)

        lkbk = 10

        if len(close) < lkbk + 2:
            bull_div = False
            bear_div = False
        else:
            try:
                price_ll = close.iloc[-1] == close.rolling(lkbk).min().iloc[-1]
                rsi_hl = rsi_series.rolling(lkbk).min().iloc[-1] > rsi_series.shift(lkbk).iloc[-1]
                bull_div = bool(price_ll and rsi_hl)

                price_hh = close.iloc[-1] == close.rolling(lkbk).max().iloc[-1]
                rsi_lh = rsi_series.rolling(lkbk).max().iloc[-1] < rsi_series.shift(lkbk).iloc[-1]
                bear_div = bool(price_hh and rsi_lh)

            except Exception as div_err:
                logger.warning(f"Divergence calc failed: {div_err}")
                bull_div, bear_div = False, False

        result.update({
            "value": round(cur, 2),
            "condition": condition,
            "trending_up": cur > prv,
            "bull_divergence": bull_div,
            "bear_divergence": bear_div,
            "status": "ok",
        })

        if condition in ("OVERBOUGHT", "OVERSOLD"):
            logger.warning(f"RSI extreme zone | value={cur:.2f} condition={condition}")

        logger.debug(
            f"RSI computed | value={cur:.2f} condition={condition} "
            f"bull_div={bull_div} bear_div={bear_div}"
        )

        return result

    except Exception as exc:
        logger.exception(f"RSI computation failed: {exc}")
        result["error"] = str(exc)
        result["status"] = "failed"
        return result


def compute_macd(df: pd.DataFrame) -> dict[str, Any]:
    """
    Compute MACD (12, 26, 9) and derive crossover / momentum signals.
    """

    logger.debug("Computing MACD (12, 26, 9)")

    result = {
        "macd": None,
        "signal": None,
        "histogram": None,
        "above_signal": None,
        "bullish_cross": None,
        "bearish_cross": None,
        "histogram_expanding": None,
        "bias": None,
        "status": "failed",
        "error": None,
    }

    try:
        if df is None or df.empty or "Close" not in df:
            result["error"] = "invalid_or_empty_dataframe"
            return result

        close = df["Close"]

        if len(close) < 30:
            result["error"] = "insufficient_data_for_macd"
            return result

        ind = ta.trend.MACD(close)

        m = ind.macd()
        s = ind.macd_signal()
        h = ind.macd_diff()

        # guard against NaNs
        if m.isna().all() or s.isna().all() or h.isna().all():
            result["error"] = "macd_all_nan"
            return result

        # safe indexing
        if len(m) < 2 or len(s) < 2 or len(h) < 2:
            result["error"] = "insufficient_indicator_history"
            return result

        cur_m, prv_m = float(m.iloc[-1]), float(m.iloc[-2])
        cur_s, prv_s = float(s.iloc[-1]), float(s.iloc[-2])
        cur_h, prv_h = float(h.iloc[-1]), float(h.iloc[-2])

        bullish_cross = prv_m < prv_s and cur_m >= cur_s
        bearish_cross = prv_m > prv_s and cur_m <= cur_s

        result.update({
            "macd": round(cur_m, 4),
            "signal": round(cur_s, 4),
            "histogram": round(cur_h, 4),
            "above_signal": cur_m > cur_s,
            "bullish_cross": bool(bullish_cross),
            "bearish_cross": bool(bearish_cross),
            "histogram_expanding": abs(cur_h) > abs(prv_h),
            "bias": "BULLISH" if cur_m > cur_s else "BEARISH",
            "status": "ok",
        })

        if bullish_cross:
            logger.info("MACD bullish crossover detected")
        if bearish_cross:
            logger.info("MACD bearish crossover detected")

        logger.debug(
            f"MACD computed | macd={cur_m:.4f} signal={cur_s:.4f} "
            f"hist={cur_h:.4f}"
        )

        return result

    except Exception as exc:
        logger.exception(f"MACD computation failed: {exc}")
        result["error"] = str(exc)
        result["status"] = "failed"
        return result


def compute_bollinger(df: pd.DataFrame) -> dict[str, Any]:
    """
    Compute Bollinger Bands (20, 2σ) with bandwidth / squeeze / breakout signals.
    """

    logger.debug("Computing Bollinger Bands (20, 2σ)")

    result = {
        "upper": None,
        "mid": None,
        "lower": None,
        "bandwidth_pct": None,
        "percent_b": None,
        "bandwidth_trend": None,
        "squeeze_active": None,
        "breakout_up": None,
        "breakout_down": None,
        "upside_to_upper_pct": None,
        "downside_to_lower_pct": None,
        "status": "failed",
        "error": None,
    }

    try:
        if df is None or df.empty:
            result["error"] = "empty_dataframe"
            return result

        if "Close" not in df:
            result["error"] = "missing_close_column"
            return result

        close = df["Close"]

        if len(close) < 20:
            result["error"] = "insufficient_data_for_bollinger"
            return result

        bb = ta.volatility.BollingerBands(close)

        ub_series = bb.bollinger_hband()
        mid_series = bb.bollinger_mavg()
        lb_series = bb.bollinger_lband()

        if ub_series.isna().all():
            result["error"] = "bollinger_all_nan"
            return result

        price = float(close.iloc[-1])

        ub = float(ub_series.iloc[-1])
        mid = float(mid_series.iloc[-1])
        lb = float(lb_series.iloc[-1])

        # --- safe division guards ---
        band_width = (ub - lb)
        bw = (band_width / mid * 100) if mid else 0

        pct_b = (price - lb) / band_width if band_width != 0 else 0.5

        bw_series = (ub_series - lb_series) / mid_series * 100

        bw_ma10 = float(bw_series.rolling(10).mean().iloc[-1]) if len(bw_series) >= 10 else bw
        bw_q20 = float(bw_series.rolling(20).quantile(0.20).iloc[-1]) if len(bw_series) >= 20 else bw

        # --- volume safety ---
        if "Volume" in df and len(df["Volume"]) >= 20:
            vol_avg20 = float(df["Volume"].rolling(20).mean().iloc[-1])
            vol_surge = float(df["Volume"].iloc[-1]) > vol_avg20 * 1.5
        else:
            vol_surge = False

        squeeze_active = bw < bw_q20
        breakout_up = price > ub and vol_surge
        breakout_down = price < lb and vol_surge

        bw_trend = "EXPANDING" if bw > bw_ma10 else "CONTRACTING"

        result.update({
            "upper": round(ub, 2),
            "mid": round(mid, 2),
            "lower": round(lb, 2),
            "bandwidth_pct": round(bw, 2),
            "percent_b": round(pct_b, 3),
            "bandwidth_trend": bw_trend,
            "squeeze_active": bool(squeeze_active),
            "breakout_up": bool(breakout_up),
            "breakout_down": bool(breakout_down),
            "upside_to_upper_pct": round((ub - price) / price * 100, 2) if price else None,
            "downside_to_lower_pct": round((price - lb) / price * 100, 2) if price else None,
            "status": "ok",
        })

        # --- logs ---
        logger.debug(
            f"Bollinger computed | bw={bw:.2f}% trend={bw_trend} pct_b={pct_b:.3f}"
        )

        if squeeze_active:
            logger.info(f"Bollinger squeeze active | bw={bw:.2f}%")
        if breakout_up:
            logger.info(f"Bollinger breakout UP | price={price}")
        if breakout_down:
            logger.info(f"Bollinger breakout DOWN | price={price}")

        return result

    except Exception as exc:
        logger.exception(f"Bollinger computation failed: {exc}")
        result["error"] = str(exc)
        result["status"] = "failed"
        return result


def compute_atr(df: pd.DataFrame, window: int = 14) -> dict[str, Any]:
    """
    Compute ATR and classify volatility regime.

    """

    logger.debug(f"Computing ATR | window={window}")

    result = {
        "value": None,
        "atr_pct": None,
        "volatility": None,
        "daily_move_range": None,
        "status": "failed",
        "error": None,
    }

    try:
        if df is None or df.empty:
            result["error"] = "empty_dataframe"
            return result

        required_cols = {"High", "Low", "Close"}
        if not required_cols.issubset(df.columns):
            result["error"] = "missing_required_columns"
            return result

        if len(df) < window + 1:
            result["error"] = "insufficient_data_for_atr"
            return result

        atr_series = ta.volatility.AverageTrueRange(
            df["High"], df["Low"], df["Close"], window=window
        ).average_true_range()

        if atr_series.isna().all():
            result["error"] = "atr_all_nan"
            return result

        atr_val = float(atr_series.iloc[-1])
        price = float(df["Close"].iloc[-1])

        if price == 0:
            result["error"] = "invalid_price_zero"
            return result

        atr_pct = (atr_val / price) * 100

        # volatility regime
        if atr_pct > 2:
            volatility = "HIGH"
        elif atr_pct > 1:
            volatility = "MODERATE"
        else:
            volatility = "LOW"

        result.update({
            "value": round(atr_val, 2),
            "atr_pct": round(atr_pct, 2),
            "volatility": volatility,
            "daily_move_range": {
                "low": round(price - atr_val, 2),
                "high": round(price + atr_val, 2),
            },
            "status": "ok",
        })

        logger.debug(
            f"ATR computed | value={atr_val:.2f} atr_pct={atr_pct:.2f}% "
            f"volatility={volatility}"
        )

        if volatility == "HIGH":
            logger.warning(f"HIGH volatility detected | ATR={atr_pct:.2f}%")

        return result

    except Exception as exc:
        logger.exception(f"ATR computation failed: {exc}")
        result["error"] = str(exc)
        result["status"] = "failed"
        return result


def compute_vwma(df: pd.DataFrame, window: int = 20) -> dict[str, Any]:
    """
    Compute Volume-Weighted Moving Average (VWMA).
    """

    logger.debug(f"Computing VWMA | window={window}")

    result = {
        "value": None,
        "price_vs_vwma": None,
        "signal": None,
        "status": "failed",
        "error": None,
    }

    try:
        if df is None or df.empty:
            result["error"] = "empty_dataframe"
            return result

        required_cols = {"Close", "Volume"}
        if not required_cols.issubset(df.columns):
            result["error"] = "missing_required_columns"
            return result

        if len(df) < window:
            result["error"] = "insufficient_data_for_vwma"
            return result

        volume_sum = df["Volume"].rolling(window).sum()
        price_vol_sum = (df["Close"] * df["Volume"]).rolling(window).sum()

        if volume_sum.isna().all() or volume_sum.iloc[-1] == 0:
            result["error"] = "invalid_volume_data"
            return result

        vwma_series = price_vol_sum / volume_sum

        vwma_val = float(vwma_series.iloc[-1])
        price = float(df["Close"].iloc[-1])

        pos = "ABOVE" if price > vwma_val else "BELOW"

        result.update({
            "value": round(vwma_val, 2),
            "price_vs_vwma": pos,
            "signal": "BULLISH" if pos == "ABOVE" else "BEARISH",
            "status": "ok",
        })

        logger.debug(
            f"VWMA computed | vwma={vwma_val:.2f} price={price:.2f} position={pos}"
        )

        return result

    except Exception as exc:
        logger.exception(f"VWMA computation failed: {exc}")
        result["error"] = str(exc)
        result["status"] = "failed"
        return result
    

def compute_mfi(df: pd.DataFrame, window: int = 14) -> dict[str, Any]:
    """
    Compute Money Flow Index (MFI), a volume-weighted RSI.
    """

    logger.debug(f"Computing MFI | window={window}")

    result = {
        "value": None,
        "condition": None,
        "signal": None,
        "status": "failed",
        "error": None,
    }

    try:
        if df is None or df.empty:
            result["error"] = "empty_dataframe"
            return result

        required_cols = {"High", "Low", "Close", "Volume"}
        if not required_cols.issubset(df.columns):
            result["error"] = "missing_required_columns"
            return result

        if len(df) < window + 1:
            result["error"] = "insufficient_data_for_mfi"
            return result

        mfi_series = ta.volume.MFIIndicator(
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            volume=df["Volume"],
            window=window,
        ).money_flow_index()

        if mfi_series.isna().all():
            result["error"] = "mfi_all_nan"
            return result

        mfi_val = float(mfi_series.iloc[-1])

        condition, signal = _compute_mfi_condition_signal(mfi_val)

        result.update({
            "value": round(mfi_val, 2),
            "condition": condition,
            "signal": signal,
            "status": "ok",
        })

        if condition in ("OVERBOUGHT", "OVERSOLD"):
            logger.warning(
                f"MFI extreme zone | condition={condition} value={mfi_val:.2f}"
            )

        logger.debug(f"MFI computed | value={mfi_val:.2f} condition={condition}")

        return result

    except Exception as exc:
        logger.exception(f"MFI computation failed: {exc}")
        result["error"] = str(exc)
        result["status"] = "failed"
        return result


def compute_volume(df: pd.DataFrame) -> dict[str, Any]:
    """
    Volume metrics designed for agentic workflows.
    """

    logger.debug("Computing volume metrics")

    result = {
        "latest": None,
        "avg_20d": None,
        "ratio_5d_20d": None,
        "surge": None,
        "status": "failed",
        "error": None,
    }

    try:
        if df is None or df.empty:
            result["error"] = "empty_dataframe"
            return result

        if "Volume" not in df.columns:
            result["error"] = "missing_volume_column"
            return result

        volume = df["Volume"]

        if len(volume) < 20:
            result["error"] = "insufficient_data_for_volume_metrics"
            return result

        latest = int(volume.iloc[-1])

        avg20 = float(volume.rolling(20).mean().iloc[-1])

        # safe 5-day handling
        if len(volume) >= 5:
            avg5 = float(volume.iloc[-5:].mean())
        else:
            avg5 = float(volume.mean())

        ratio = (avg5 / avg20) if avg20 else None

        surge = bool(avg20 and avg5 > avg20 * 1.5)

        result.update({
            "latest": latest,
            "avg_20d": round(avg20, 2),
            "ratio_5d_20d": round(ratio, 2) if ratio is not None else None,
            "surge": surge,
            "status": "ok",
        })

        logger.debug(
            f"Volume computed | latest={latest} avg20={avg20:.2f} "
            f"ratio={ratio} surge={surge}"
        )

        if surge:
            logger.info(f"Volume surge detected | ratio={ratio:.2f}")

        return result

    except Exception as exc:
        logger.exception(f"Volume computation failed: {exc}")
        result["error"] = str(exc)
        result["status"] = "failed"
        return result
    

def compute_price_levels(df: pd.DataFrame) -> dict[str, Any]:
    """
    Price level computation designed for agentic workflows.
    """

    logger.debug("Computing price levels")

    result = {
        "current": None,
        "high_52w": None,
        "low_52w": None,
        "pct_from_52w_high": None,
        "pct_from_52w_low": None,
        "rs_20d_pct": None,
        "status": "failed",
        "error": None,
    }

    try:
        if df is None or df.empty:
            result["error"] = "empty_dataframe"
            return result

        if "Close" not in df.columns:
            result["error"] = "missing_close_column"
            return result

        close = df["Close"].dropna()

        if len(close) < 20:
            result["error"] = "insufficient_data_for_price_levels"
            return result

        price = float(close.iloc[-1])

        # --- 52-week logic (guarded) ---
        lookback_52w = min(252, len(close))
        window_52w = close.tail(lookback_52w)

        h52 = float(window_52w.max())
        l52 = float(window_52w.min())

        pct_from_high = ((price / h52) - 1) * 100 if h52 else None
        pct_from_low = ((price / l52) - 1) * 100 if l52 else None

        # --- 20-day return (safe) ---
        if len(close) >= 20:
            rs_20d = ((price / float(close.iloc[-20])) - 1) * 100
        else:
            rs_20d = None

        result.update({
            "current": round(price, 2),
            "high_52w": round(h52, 2),
            "low_52w": round(l52, 2),
            "pct_from_52w_high": round(pct_from_high, 2) if pct_from_high is not None else None,
            "pct_from_52w_low": round(pct_from_low, 2) if pct_from_low is not None else None,
            "rs_20d_pct": round(rs_20d, 2) if rs_20d is not None else None,
            "status": "ok",
        })

        logger.debug(
            f"Price levels computed | current={price:.2f} "
            f"52w_high={h52:.2f} 52w_low={l52:.2f}"
        )

        if pct_from_high is not None and pct_from_high < -20:
            logger.warning(
                f"Significant drawdown | {pct_from_high:.2f}% from 52W high"
            )

        return result

    except Exception as exc:
        logger.exception(f"Price levels computation failed: {exc}")
        result["error"] = str(exc)
        result["status"] = "failed"
        return result
    

if __name__ == "__main__":

    print("Fetching technical snapshot \n")
    ticker="RELIANCE.NS"
    df=fetch_df(ticker)
    snapshot= {
        "ticker":          ticker,
        "price_levels":    compute_price_levels(df['data']),
        "moving_averages": compute_moving_averages(df['data']),
        "rsi":             compute_rsi(df['data']),
        "macd":            compute_macd(df['data']),
        "bollinger":       compute_bollinger(df['data']),
        "atr":             compute_atr(df['data']),
        "vwma":            compute_vwma(df['data']),
        "mfi":             compute_mfi(df['data']),
        "volume":          compute_volume(df['data']),
    }
    output = json.dumps(snapshot, indent=2)
    print(output)

    with open("technical_snapshot.json", "w") as f:
        f.write(output)

    print("\nSaved : technical_snapshot.json")