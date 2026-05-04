import pandas as pd   


def _compute_trend_alignment(above_count : int) -> str:

    if above_count == 4:
        result = "STRONG_BULL"
    elif above_count == 3:
        result = "BULL"
    elif above_count == 1:
        result = "BEAR"
    elif above_count == 0:
        result = "STRONG_BEAR"
    else:
        result = "MIXED"
    
    return result

def _compute_rsi_condition(cur : int) -> str :

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

    return condition

def _compute_mfi_condition_signal(mfi_val: int) -> tuple[str, str]:

    if mfi_val > 80:
        condition, signal = "OVERBOUGHT", "SELL"
    elif mfi_val < 20:
        condition, signal = "OVERSOLD", "BUY"
    else:
        condition, signal = "NEUTRAL", "HOLD"

    return condition, signal
    
