"""
decision_engine.py  —  Turn price data into a BUY / SELL / HOLD signal
═══════════════════════════════════════════════════════════════════════

BUG FIXED — wrong dict key caused forecast to always be 0:
──────────────────────────────────────────────────────────
  OLD CODE (decision_engine.py):
      forecasted_price = float(forecast_result.get("predicted_price", 0))

  OLD CODE (forecast_model.py) actually returned:
      {"predicted_change": ..., "confidence": ..., "method": ...}
      # "predicted_price" key did NOT exist

  Result: .get("predicted_price", 0) → always 0
          predicted_change = 0 - last_price = always negative
          Decision was almost always SELL regardless of real trend.

  FIX: forecast_model.py now returns BOTH "predicted_price" AND
       "predicted_change". This file reads "predicted_price" correctly.

BUG FIXED — risk_model signature changed:
─────────────────────────────────────────
  Old risk_model.calculate_risk_score(volatility) took 1 arg.
  New version takes (volatility, prices) so it can compute CV properly.
  This file now passes both arguments.

Design decisions you can defend:
  - We pass dates from mandi_api into forecast so Prophet gets real time axis
  - get_risk_summary() does volatility + CV + risk_level in one clean call
  - Decision thresholds (50 Rs) are absolute, not percentage — easier for
    a farmer to understand "price expected to rise Rs 60" than "up 2.4 %"
"""

import logging
from datetime import datetime, timezone

from risk_model    import get_risk_summary
from forecast_model import forecast_prices

log = logging.getLogger(__name__)


# ── Decision thresholds (Rs/quintal) ─────────────────────────────────────────
# Centralised here so an interviewer can ask "why 50?" and you can say:
# "Farmers' transaction cost (transport + commission) is roughly Rs 40–60/q,
#  so a predicted move smaller than that isn't worth acting on."
STRONG_SIGNAL_THRESHOLD = 50   # Rs — defines STRONG BUY / STRONG SELL


def make_decision(prices: list[float], dates: list = None) -> dict:
    """
    Core decision pipeline.

    Parameters
    ──────────
    prices : list[float]  — historical modal prices, chronological order
    dates  : list | None  — real trade dates from mandi_api (PASS THESE!)
                            If None, forecast falls back to synthetic dates.

    Returns
    ───────
    dict with keys:
        volatility, cv, risk_score, risk_level,
        predicted_price, predicted_change, trend,
        confidence, decision, explanation,
        data_warning (present only when dates=None)
    """
    # ── 1. Validate ───────────────────────────────────────────────────────────
    if not prices or len(prices) < 2:
        return _error_result("Not enough price data (need ≥ 2 records).")

    try:
        prices = [float(p) for p in prices]
    except (ValueError, TypeError) as e:
        return _error_result(f"Invalid price values: {e}")

    # ── 2. Risk assessment ────────────────────────────────────────────────────
    risk = get_risk_summary(prices)   # volatility + CV + risk_score + risk_level

    # ── 3. Forecast ───────────────────────────────────────────────────────────
    forecast = forecast_prices(prices, dates=dates)

    predicted_price  = forecast["predicted_price"]    # ← fixed key
    predicted_change = forecast["predicted_change"]
    confidence       = forecast["confidence"]
    method           = forecast["method"]

    last_actual = prices[-1]
    trend       = "UPTREND" if predicted_change > 0 else "DOWNTREND"

    # ── 4. Decision logic ─────────────────────────────────────────────────────
    decision = _determine_decision(predicted_change, risk["risk_level"])

    # ── 5. Human-readable explanation ────────────────────────────────────────
    explanation = _build_explanation(
        risk["risk_level"], risk["volatility"], risk["cv"],
        predicted_price, predicted_change, decision, method
    )

    result = {
        # Risk metrics
        "volatility"      : risk["volatility"],
        "cv"              : risk["cv"],           # coefficient of variation
        "risk_score"      : risk["risk_score"],
        "risk_level"      : risk["risk_level"],
        "mean_price"      : risk["mean_price"],
        # Forecast
        "predicted_price" : predicted_price,
        "predicted_change": predicted_change,
        "last_actual_price": round(last_actual, 2),
        "trend"           : trend,
        "forecast_method" : method,
        # Decision
        "confidence"      : round(confidence, 2),
        "decision"        : decision,
        "explanation"     : explanation,
        "timestamp"       : datetime.now(timezone.utc).isoformat(),
    }

    # Warn if we had to use synthetic dates
    if dates is None:
        result["data_warning"] = (
            "Forecast used synthetic date index — pass real arrival_dates "
            "from mandi_api.fetch_mandi_data() for higher accuracy."
        )

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Decision matrix
# ─────────────────────────────────────────────────────────────────────────────

def _determine_decision(predicted_change: float, risk_level: str) -> str:
    """
    Map (predicted_change, risk_level) → trading signal.

    Matrix (interview-ready):

                        change > +50  | 0 to +50 | -50 to 0 | < -50
    risk HIGH           BUY           | HOLD      | SELL      | STRONG SELL
    risk MEDIUM         BUY           | HOLD      | HOLD      | SELL
    risk LOW            STRONG BUY    | BUY       | HOLD      | SELL

    Rationale: in a HIGH-risk market even a small predicted drop warrants
    selling because we have low confidence in the forecast. In a LOW-risk
    stable market even a modest predicted uptick justifies buying because
    the model's signal is more reliable.
    """
    T = STRONG_SIGNAL_THRESHOLD

    if risk_level == "HIGH":
        if predicted_change >  T:  return "BUY"
        if predicted_change > 0:   return "HOLD"
        if predicted_change > -T:  return "SELL"
        return "STRONG SELL"

    if risk_level == "MEDIUM":
        if predicted_change >  T:  return "BUY"
        if predicted_change > -T:  return "HOLD"
        return "SELL"

    # LOW risk
    if predicted_change >  T:  return "STRONG BUY"
    if predicted_change >  0:  return "BUY"
    if predicted_change > -T:  return "HOLD"
    return "SELL"


def _build_explanation(
    risk_level, volatility, cv, predicted_price,
    predicted_change, decision, method
) -> str:
    direction = "rise" if predicted_change >= 0 else "fall"
    return (
        f"Market risk is {risk_level} "
        f"(price std ≈ Rs {volatility:.0f}, CV = {cv:.2%}). "
        f"Model ({method}) forecasts price to {direction} "
        f"by Rs {abs(predicted_change):.0f} to ~Rs {predicted_price:.0f}/quintal. "
        f"Recommendation: {decision}."
    )


def _error_result(message: str) -> dict:
    return {
        "volatility": 0, "cv": 0, "risk_score": 0,
        "risk_level": "LOW", "mean_price": 0,
        "predicted_price": 0, "predicted_change": 0,
        "last_actual_price": 0, "trend": "UNKNOWN",
        "forecast_method": "none",
        "confidence": 0.0, "decision": "NO DATA",
        "explanation": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }