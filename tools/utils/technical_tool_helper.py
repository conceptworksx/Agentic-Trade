import pandas as pd
import ta
from typing import Any


def fetch_df(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """
    Fetch historical OHLCV data for a given ticker symbol.

    Args:
        symbol   (str): Yahoo Finance ticker (e.g. 'RELIANCE.NS', 'AAPL').
        period   (str): Lookback window (default '1y').
        interval (str): Bar granularity (default '1d').

    Returns:
        pd.DataFrame: Time-sorted OHLCV DataFrame with timezone stripped.
    """
    import yfinance as yf
    df = yf.download(symbol, period=period, interval=interval,
                     auto_adjust=True, progress=False)
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df.sort_index(inplace=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def compute_moving_averages(df: pd.DataFrame) -> dict[str, Any]:
    """
    Compute 10, 50, 100, and 200-day simple moving averages.

    Returns:
        ma10, ma50, ma100, ma200       : float — current MA value
        price_vs_ma{N}                 : "ABOVE" | "BELOW"
        golden_cross                   : bool — MA50 > MA200
        death_cross                    : bool — MA50 < MA200
        trend_alignment                : "STRONG_BULL" | "BULL" | "MIXED" | "BEAR" | "STRONG_BEAR"
    """
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

    return result


def compute_rsi(df: pd.DataFrame, window: int = 14) -> dict[str, Any]:
    """
    Compute RSI and derive overbought / oversold / divergence signals.

    Returns:
        value           : float — latest RSI reading
        condition       : "OVERBOUGHT" | "BULLISH_ZONE" | "NEUTRAL" | "BEARISH_ZONE" | "OVERSOLD"
        trending_up     : bool
        bull_divergence : bool — price lower low, RSI higher low
        bear_divergence : bool — price higher high, RSI lower high
    """
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

    return {
        "value":           round(cur, 2),
        "condition":       condition,
        "trending_up":     cur > prv,
        "bull_divergence": bull_div,
        "bear_divergence": bear_div,
    }


def compute_macd(df: pd.DataFrame) -> dict[str, Any]:
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
    ind = ta.trend.MACD(df["Close"])
    m   = ind.macd()
    s   = ind.macd_signal()
    h   = ind.macd_diff()

    cur_m, prv_m = float(m.iloc[-1]), float(m.iloc[-2])
    cur_s, prv_s = float(s.iloc[-1]), float(s.iloc[-2])
    cur_h, prv_h = float(h.iloc[-1]), float(h.iloc[-2])

    return {
        "macd":                 round(cur_m, 4),
        "signal":               round(cur_s, 4),
        "histogram":            round(cur_h, 4),
        "above_signal":         cur_m > cur_s,
        "bullish_cross":        prv_m < prv_s and cur_m >= cur_s,
        "bearish_cross":        prv_m > prv_s and cur_m <= cur_s,
        "histogram_expanding":  abs(cur_h) > abs(prv_h),
        "bias":                 "BULLISH" if cur_m > cur_s else "BEARISH",
    }


def compute_bollinger(df: pd.DataFrame) -> dict[str, Any]:
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

    return {
        "upper":                 round(ub, 2),
        "mid":                   round(mid, 2),
        "lower":                 round(lb, 2),
        "bandwidth_pct":         round(bw, 2),
        "percent_b":             round(pct_b, 3),
        "bandwidth_trend":       "EXPANDING" if bw > bw_ma10 else "CONTRACTING",
        "squeeze_active":        bool(bw < bw_q20),
        "breakout_up":           bool(price > ub and vol_surge),
        "breakout_down":         bool(price < lb and vol_surge),
        "upside_to_upper_pct":   round((ub - price) / price * 100, 2),
        "downside_to_lower_pct": round((price - lb) / price * 100, 2),
    }


def compute_atr(df: pd.DataFrame, window: int = 14) -> dict[str, Any]:
    """
    Compute ATR and classify volatility regime.

    Returns:
        value            : float — ATR in price units
        atr_pct          : float — ATR as % of current price
        volatility       : "HIGH" | "MODERATE" | "LOW"
        daily_move_range : {"low": float, "high": float}
    """
    atr_val = float(
        ta.volatility.AverageTrueRange(
            df["High"], df["Low"], df["Close"], window=window
        ).average_true_range().iloc[-1]
    )
    price   = float(df["Close"].iloc[-1])
    atr_pct = atr_val / price * 100

    return {
        "value":    round(atr_val, 2),
        "atr_pct":  round(atr_pct, 2),
        "volatility": (
            "HIGH"     if atr_pct > 2 else
            "MODERATE" if atr_pct > 1 else
            "LOW"
        ),
        "daily_move_range": {
            "low":  round(price - atr_val, 2),
            "high": round(price + atr_val, 2),
        },
    }


def compute_vwma(df: pd.DataFrame, window: int = 20) -> dict[str, Any]:
    """
    Compute Volume-Weighted Moving Average (VWMA).

    Returns:
        value           : float — VWMA price level
        price_vs_vwma   : "ABOVE" | "BELOW"
        signal          : "BULLISH" | "BEARISH"
    """
    vwma_series = (
        (df["Close"] * df["Volume"]).rolling(window).sum()
        / df["Volume"].rolling(window).sum()
    )
    vwma_val = float(vwma_series.iloc[-1])
    price    = float(df["Close"].iloc[-1])
    pos      = "ABOVE" if price > vwma_val else "BELOW"

    return {
        "value":         round(vwma_val, 2),
        "price_vs_vwma": pos,
        "signal":        "BULLISH" if pos == "ABOVE" else "BEARISH",
    }


def compute_mfi(df: pd.DataFrame, window: int = 14) -> dict[str, Any]:
    """
    Compute Money Flow Index (MFI), a volume-weighted RSI.

    Returns:
        value     : float — MFI reading (0–100)
        condition : "OVERBOUGHT" | "NEUTRAL" | "OVERSOLD"
        signal    : "SELL" | "HOLD" | "BUY"
    """
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

    return {
        "value":     round(mfi_val, 2),
        "condition": condition,
        "signal":    signal,
    }


def compute_volume(df: pd.DataFrame) -> dict[str, Any]:
    """
    Compute volume trend metrics.

    Returns:
        latest        : int — most recent bar volume
        avg_20d       : int — 20-day average volume
        ratio_5d_20d  : float — 5-day avg vs 20-day avg
        surge         : bool — 5-day avg > 1.5× 20-day avg
    """
    avg20 = float(df["Volume"].rolling(20).mean().iloc[-1])
    avg5  = float(df["Volume"].iloc[-5:].mean())

    return {
        "latest":       int(df["Volume"].iloc[-1]),
        "avg_20d":      int(avg20),
        "ratio_5d_20d": round(avg5 / avg20, 2) if avg20 else None,
        "surge":        bool(avg5 > avg20 * 1.5),
    }


def compute_price_levels(df: pd.DataFrame) -> dict[str, Any]:
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
    close = df["Close"]
    close = close.dropna()
    price = float(close.iloc[-1])
    h52   = float(close.rolling(250).max().iloc[-1])
    l52   = float(close.rolling(250).min().iloc[-1])

    return {
        "current":           round(price, 2),
        "high_52w":          round(h52, 2),
        "low_52w":           round(l52, 2),
        "pct_from_52w_high": round((price / h52 - 1) * 100, 2),
        "pct_from_52w_low":  round((price / l52 - 1) * 100, 2),
        "rs_20d_pct":        round((price / float(close.iloc[-20]) - 1) * 100, 2),
    }