import pandas as pd
import ta
from typing import Any
from tools.utils.retry_utils import with_retry
from core.error import DataFetchError, DataParseError         
from core.logging import get_logger                     
logger = get_logger(__name__)


@with_retry(retries=3, delay=2.0, backoff=2.0)
def _fetch_df(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """Fetch historical OHLCV data for a given ticker symbol."""
    import yfinance as yf

    logger.debug(f"Downloading OHLCV data | symbol={symbol} period={period} interval={interval}")

    try:
        df = yf.download(symbol, period=period, interval=interval,
                         auto_adjust=True, progress=False)
    except Exception as exc:
        logger.error(f"yfinance.download failed | symbol={symbol} | {exc}")
        raise DataFetchError(source="yfinance.download", symbol=symbol, original=exc)

    if df is None or df.empty:
        logger.warning(f"Empty DataFrame returned | symbol={symbol}")
        raise DataFetchError(source="yfinance.download", symbol=symbol)

    try:
        df.index = pd.to_datetime(df.index).tz_localize(None)
        df.sort_index(inplace=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
    except Exception as exc:
        logger.error(f"DataFrame normalisation failed | symbol={symbol} | {exc}")
        raise DataParseError(
            f"Failed to normalize DataFrame for {symbol}: {exc}", original=exc
        )

    logger.info(f"Fetched {len(df)} bars | symbol={symbol} period={period}")
    return df


def _compute_moving_averages(df: pd.DataFrame) -> dict[str, Any]:
    """
    Compute 10, 50, 100, and 200-day simple moving averages.

    Returns:
        ma10, ma50, ma100, ma200       : float — current MA value
        price_vs_ma{N}                 : "ABOVE" | "BELOW"
        golden_cross                   : bool — MA50 > MA200
        death_cross                    : bool — MA50 < MA200
        trend_alignment                : "STRONG_BULL" | "BULL" | "MIXED" | "BEAR" | "STRONG_BEAR"
    """
    logger.debug("Computing moving averages")
    try:
        close = df["Close"]
        price = float(close.iloc[-1])

        result      = {}
        above_count = 0

        for w in [10, 50, 100, 200]:
            raw = close.rolling(w).mean().iloc[-1]
            val = round(float(raw), 2) if not pd.isna(raw) else None
            result[f"ma{w}"] = val
            if val is not None:
                result[f"price_vs_ma{w}"] = "ABOVE" if price > val else "BELOW"
                if price > val:
                    above_count += 1

        ma50  = result.get("ma50")
        ma200 = result.get("ma200")
        result["golden_cross"] = bool(ma50 and ma200 and ma50 > ma200)
        result["death_cross"]  = bool(ma50 and ma200 and ma50 < ma200)

        if above_count == 4:
            result["trend_alignment"] = "STRONG_BULL"
        elif above_count == 3:
            result["trend_alignment"] = "BULL"
        elif above_count == 1:
            result["trend_alignment"] = "BEAR"
        elif above_count == 0:
            result["trend_alignment"] = "STRONG_BEAR"
        else:
            result["trend_alignment"] = "MIXED"

        logger.debug(f"Moving averages computed | alignment={result['trend_alignment']} "
                     f"golden_cross={result['golden_cross']} death_cross={result['death_cross']}")
        return result

    except (DataParseError, DataFetchError):
        raise
    except Exception as exc:
        logger.error(f"Moving averages computation failed | {exc}")
        raise DataParseError(
            f"Failed to compute moving averages: {exc}", original=exc
        )


def _compute_rsi(df: pd.DataFrame, window: int = 14) -> dict[str, Any]:
    """
    Compute RSI and derive overbought / oversold / divergence signals.

    Returns:
        value           : float — latest RSI reading
        condition       : "OVERBOUGHT" | "BULLISH_ZONE" | "NEUTRAL" | "BEARISH_ZONE" | "OVERSOLD"
        trending_up     : bool
        bull_divergence : bool — price lower low, RSI higher low
        bear_divergence : bool — price higher high, RSI lower high
    """
    logger.debug(f"Computing RSI | window={window}")
    try:
        rsi_series = ta.momentum.RSIIndicator(df["Close"], window=window).rsi()
        cur = float(rsi_series.iloc[-1])
        prv = float(rsi_series.iloc[-2])

        if cur > 70:
            condition = "OVERBOUGHT"
        elif cur >= 60:
            condition = "BULLISH_ZONE"
        elif cur <= 30:
            condition = "OVERSOLD"
        elif cur <= 40:
            condition = "BEARISH_ZONE"
        else:
            condition = "NEUTRAL"

        lkbk     = 10
        price_ll = df["Close"].rolling(lkbk).min().iloc[-1] == df["Close"].iloc[-1]
        rsi_hl   = rsi_series.rolling(lkbk).min().iloc[-1] > rsi_series.shift(lkbk).iloc[-1]
        bull_div = bool(price_ll and rsi_hl)

        price_hh = df["Close"].rolling(lkbk).max().iloc[-1] == df["Close"].iloc[-1]
        rsi_lh   = rsi_series.rolling(lkbk).max().iloc[-1] < rsi_series.shift(lkbk).iloc[-1]
        bear_div = bool(price_hh and rsi_lh)

        logger.debug(f"RSI computed | value={cur:.2f} condition={condition} "
                     f"bull_div={bull_div} bear_div={bear_div}")

        if condition in ("OVERBOUGHT", "OVERSOLD"):
            logger.warning(f"RSI extreme zone | condition={condition} value={cur:.2f}")

        return {
            "value":           round(cur, 2),
            "condition":       condition,
            "trending_up":     cur > prv,
            "bull_divergence": bull_div,
            "bear_divergence": bear_div,
        }

    except (DataParseError, DataFetchError):
        raise
    except Exception as exc:
        logger.error(f"RSI computation failed | {exc}")
        raise DataParseError(
            f"Failed to compute RSI: {exc}", original=exc
        )


def _compute_macd(df: pd.DataFrame) -> dict[str, Any]:
    """
    Compute MACD (12, 26, 9) and derive crossover / momentum signals.

    Returns:
        macd                : float
        signal              : float
        histogram           : float
        above_signal        : bool
        bullish_cross       : bool — fresh bullish crossover
        bearish_cross       : bool — fresh bearish crossover
        histogram_expanding : bool — momentum increasing
        bias                : "BULLISH" | "BEARISH"
    """
    logger.debug("Computing MACD (12, 26, 9)")
    try:
        ind = ta.trend.MACD(df["Close"])
        m   = ind.macd()
        s   = ind.macd_signal()
        h   = ind.macd_diff()

        cur_m, prv_m = float(m.iloc[-1]), float(m.iloc[-2])
        cur_s, prv_s = float(s.iloc[-1]), float(s.iloc[-2])
        cur_h, prv_h = float(h.iloc[-1]), float(h.iloc[-2])

        bullish_cross = prv_m < prv_s and cur_m >= cur_s
        bearish_cross = prv_m > prv_s and cur_m <= cur_s

        logger.debug(f"MACD computed | macd={cur_m:.4f} signal={cur_s:.4f} "
                     f"histogram={cur_h:.4f} bullish_cross={bullish_cross} "
                     f"bearish_cross={bearish_cross}")

        if bullish_cross:
            logger.info("MACD bullish crossover detected")
        if bearish_cross:
            logger.info("MACD bearish crossover detected")

        return {
            "macd":                 round(cur_m, 4),
            "signal":               round(cur_s, 4),
            "histogram":            round(cur_h, 4),
            "above_signal":         cur_m > cur_s,
            "bullish_cross":        bullish_cross,
            "bearish_cross":        bearish_cross,
            "histogram_expanding":  abs(cur_h) > abs(prv_h),
            "bias":                 "BULLISH" if cur_m > cur_s else "BEARISH",
        }

    except (DataParseError, DataFetchError):
        raise
    except Exception as exc:
        logger.error(f"MACD computation failed | {exc}")
        raise DataParseError(
            f"Failed to compute MACD: {exc}", original=exc
        )


def _compute_bollinger(df: pd.DataFrame) -> dict[str, Any]:
    """
    Compute Bollinger Bands (20, 2σ) with bandwidth / squeeze / breakout signals.

    Returns:
        upper, mid, lower        : float — band price levels
        bandwidth_pct            : float — (upper-lower)/mid * 100
        percent_b                : float — price position within bands [0..1]
        bandwidth_trend          : "EXPANDING" | "CONTRACTING"
        squeeze_active           : bool — bandwidth at 20-period low
        breakout_up              : bool — close above upper + volume surge
        breakout_down            : bool — close below lower + volume surge
        upside_to_upper_pct      : float
        downside_to_lower_pct    : float
    """
    logger.debug("Computing Bollinger Bands (20, 2σ)")
    try:
        bb    = ta.volatility.BollingerBands(df["Close"])
        price = float(df["Close"].iloc[-1])

        ub  = float(bb.bollinger_hband().iloc[-1])
        mid = float(bb.bollinger_mavg().iloc[-1])
        lb  = float(bb.bollinger_lband().iloc[-1])

        bw    = (ub - lb) / mid * 100 if mid else 0
        pct_b = (price - lb) / (ub - lb) if (ub - lb) != 0 else 0.5

        bw_series = (
            (bb.bollinger_hband() - bb.bollinger_lband()) / bb.bollinger_mavg() * 100
        )
        bw_ma10 = float(bw_series.rolling(10).mean().iloc[-1])
        bw_q20  = float(bw_series.rolling(20).quantile(0.20).iloc[-1])

        vol_avg20 = float(df["Volume"].rolling(20).mean().iloc[-1])
        vol_surge = float(df["Volume"].iloc[-1]) > vol_avg20 * 1.5

        squeeze_active = bool(bw < bw_q20)
        breakout_up    = bool(price > ub and vol_surge)
        breakout_down  = bool(price < lb and vol_surge)
        bw_trend       = "EXPANDING" if bw > bw_ma10 else "CONTRACTING"

        logger.debug(f"Bollinger computed | bandwidth={bw:.2f}% trend={bw_trend} "
                     f"percent_b={pct_b:.3f} squeeze={squeeze_active}")

        if squeeze_active:
            logger.info(f"Bollinger squeeze active | bandwidth={bw:.2f}% — breakout may be imminent")
        if breakout_up:
            logger.info(f"Bollinger breakout UP detected | price={price} upper={ub}")
        if breakout_down:
            logger.info(f"Bollinger breakout DOWN detected | price={price} lower={lb}")

        return {
            "upper":                 round(ub, 2),
            "mid":                   round(mid, 2),
            "lower":                 round(lb, 2),
            "bandwidth_pct":         round(bw, 2),
            "percent_b":             round(pct_b, 3),
            "bandwidth_trend":       bw_trend,
            "squeeze_active":        squeeze_active,
            "breakout_up":           breakout_up,
            "breakout_down":         breakout_down,
            "upside_to_upper_pct":   round((ub - price) / price * 100, 2),
            "downside_to_lower_pct": round((price - lb) / price * 100, 2),
        }

    except (DataParseError, DataFetchError):
        raise
    except Exception as exc:
        logger.error(f"Bollinger Bands computation failed | {exc}")
        raise DataParseError(
            f"Failed to compute Bollinger Bands: {exc}", original=exc
        )


def _compute_atr(df: pd.DataFrame, window: int = 14) -> dict[str, Any]:
    """
    Compute ATR and classify volatility regime.

    Returns:
        value            : float — ATR in price units
        atr_pct          : float — ATR as % of current price
        volatility       : "HIGH" | "MODERATE" | "LOW"
        daily_move_range : {"low": float, "high": float}
    """
    logger.debug(f"Computing ATR | window={window}")
    try:
        atr_val = float(
            ta.volatility.AverageTrueRange(
                df["High"], df["Low"], df["Close"], window=window
            ).average_true_range().iloc[-1]
        )
        price   = float(df["Close"].iloc[-1])
        atr_pct = atr_val / price * 100

        volatility = "HIGH" if atr_pct > 2 else "MODERATE" if atr_pct > 1 else "LOW"

        logger.debug(f"ATR computed | value={atr_val:.2f} atr_pct={atr_pct:.2f}% "
                     f"volatility={volatility}")

        if volatility == "HIGH":
            logger.warning(f"HIGH volatility detected | ATR={atr_pct:.2f}% of price")

        return {
            "value":    round(atr_val, 2),
            "atr_pct":  round(atr_pct, 2),
            "volatility": volatility,
            "daily_move_range": {
                "low":  round(price - atr_val, 2),
                "high": round(price + atr_val, 2),
            },
        }

    except (DataParseError, DataFetchError):
        raise
    except Exception as exc:
        logger.error(f"ATR computation failed | {exc}")
        raise DataParseError(
            f"Failed to compute ATR: {exc}", original=exc
        )


def _compute_vwma(df: pd.DataFrame, window: int = 20) -> dict[str, Any]:
    """
    Compute Volume-Weighted Moving Average (VWMA).

    Returns:
        value           : float — VWMA price level
        price_vs_vwma   : "ABOVE" | "BELOW"
        signal          : "BULLISH" | "BEARISH"
    """
    logger.debug(f"Computing VWMA | window={window}")
    try:
        vwma_series = (
            (df["Close"] * df["Volume"]).rolling(window).sum()
            / df["Volume"].rolling(window).sum()
        )
        vwma_val = float(vwma_series.iloc[-1])
        price    = float(df["Close"].iloc[-1])
        pos      = "ABOVE" if price > vwma_val else "BELOW"

        logger.debug(f"VWMA computed | vwma={vwma_val:.2f} price={price:.2f} "
                     f"position={pos}")

        return {
            "value":         round(vwma_val, 2),
            "price_vs_vwma": pos,
            "signal":        "BULLISH" if pos == "ABOVE" else "BEARISH",
        }

    except (DataParseError, DataFetchError):
        raise
    except Exception as exc:
        logger.error(f"VWMA computation failed | {exc}")
        raise DataParseError(
            f"Failed to compute VWMA: {exc}", original=exc
        )


def _compute_mfi(df: pd.DataFrame, window: int = 14) -> dict[str, Any]:
    """
    Compute Money Flow Index (MFI), a volume-weighted RSI.

    Returns:
        value     : float — MFI reading (0–100)
        condition : "OVERBOUGHT" | "NEUTRAL" | "OVERSOLD"
        signal    : "SELL" | "HOLD" | "BUY"
    """
    logger.debug(f"Computing MFI | window={window}")
    try:
        mfi_val = float(
            ta.volume.MFIIndicator(
                high=df["High"], low=df["Low"],
                close=df["Close"], volume=df["Volume"],
                window=window,
            ).money_flow_index().iloc[-1]
        )

        if mfi_val > 80:
            condition, signal = "OVERBOUGHT", "SELL"
        elif mfi_val < 20:
            condition, signal = "OVERSOLD", "BUY"
        else:
            condition, signal = "NEUTRAL", "HOLD"

        logger.debug(f"MFI computed | value={mfi_val:.2f} condition={condition}")

        if condition in ("OVERBOUGHT", "OVERSOLD"):
            logger.warning(f"MFI extreme zone | condition={condition} value={mfi_val:.2f}")

        return {
            "value":     round(mfi_val, 2),
            "condition": condition,
            "signal":    signal,
        }

    except (DataParseError, DataFetchError):
        raise
    except Exception as exc:
        logger.error(f"MFI computation failed | {exc}")
        raise DataParseError(
            f"Failed to compute MFI: {exc}", original=exc
        )


def _compute_volume(df: pd.DataFrame) -> dict[str, Any]:
    """
    Compute volume trend metrics.

    Returns:
        latest        : int — most recent bar volume
        avg_20d       : int — 20-day average volume
        ratio_5d_20d  : float — 5-day avg vs 20-day avg
        surge         : bool — 5-day avg > 1.5× 20-day avg
    """
    logger.debug("Computing volume metrics")
    try:
        avg20 = float(df["Volume"].rolling(20).mean().iloc[-1])
        avg5  = float(df["Volume"].iloc[-5:].mean())
        ratio = round(avg5 / avg20, 2) if avg20 else None
        surge = bool(avg5 > avg20 * 1.5)

        logger.debug(f"Volume computed | latest={int(df['Volume'].iloc[-1])} "
                     f"avg_20d={int(avg20)} ratio={ratio} surge={surge}")

        if surge:
            logger.info(f"Volume surge detected | 5d/20d ratio={ratio}")

        return {
            "latest":       int(df["Volume"].iloc[-1]),
            "avg_20d":      int(avg20),
            "ratio_5d_20d": ratio,
            "surge":        surge,
        }

    except (DataParseError, DataFetchError):
        raise
    except Exception as exc:
        logger.error(f"Volume computation failed | {exc}")
        raise DataParseError(
            f"Failed to compute volume metrics: {exc}", original=exc
        )


def _compute_price_levels(df: pd.DataFrame) -> dict[str, Any]:
    """
    Compute key price reference levels.

    Returns:
        current             : float
        high_52w            : float
        low_52w             : float
        pct_from_52w_high   : float
        pct_from_52w_low    : float
        rs_20d_pct          : float — 20-day return %
    """
    logger.debug("Computing price levels")
    try:
        close = df["Close"].dropna()
        price = float(close.iloc[-1])
        h52   = float(close.tail(252).max())
        l52   = float(close.tail(252).min())
        pct_from_high = round((price / h52 - 1) * 100, 2)

        logger.debug(f"Price levels computed | current={price} 52w_high={h52} "
                     f"52w_low={l52} pct_from_high={pct_from_high}%")

        if pct_from_high < -20:
            logger.warning(f"Price is {pct_from_high}% below 52-week high — significant drawdown")

        return {
            "current":           round(price, 2),
            "high_52w":          round(h52, 2),
            "low_52w":           round(l52, 2),
            "pct_from_52w_high": pct_from_high,
            "pct_from_52w_low":  round((price / l52 - 1) * 100, 2),
            "rs_20d_pct":        round((price / float(close.iloc[-20]) - 1) * 100, 2),
        }

    except (DataParseError, DataFetchError):
        raise
    except Exception as exc:
        logger.error(f"Price levels computation failed | {exc}")
        raise DataParseError(
            f"Failed to compute price levels: {exc}", original=exc
        )