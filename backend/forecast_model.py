"""
forecast_model.py  —  Prophet price forecasting on REAL trade dates
════════════════════════════════════════════════════════════════════

THE CORE BUG (explain this in every interview):
───────────────────────────────────────────────
  OLD CODE:
      df = pd.DataFrame({
          "ds": pd.date_range(start="2024-01-01", periods=len(cleaned_prices)),
          "y":  cleaned_prices
      })

  WHY THAT'S WRONG:
    1. The fake date axis starts 2024-01-01 regardless of when prices were
       actually recorded. If real data spans Oct 2023–Mar 2024, Prophet
       "sees" Jan–Apr 2024 and learns the wrong seasonality.
    2. Gaps between trading days (weekends, holidays, mandi closures) are
       erased. Prophet uses these gaps to understand market rhythms.
    3. The forecast horizon extends from the FAKE last date, not today,
       so "predict next 30 days" is forecasting fictional future dates.

  NEW CODE:
      df = mandi_api.fetch_mandi_data(...)   # has real 'ds' column
      model.fit(df[["ds", "y"]])             # Prophet sees genuine dates

  WHY THAT'S BETTER:
    - Annual harvest cycles (kharif/rabi) are reflected in real dates
    - Market closure gaps teach Prophet that missing days are normal
    - The 30-day forecast truly starts from the last REAL trade date

SECOND BUG FIXED — broken return contract:
───────────────────────────────────────────
  OLD:  returned {"predicted_change": ..., "confidence": ...}
  decision_engine.py called:  forecast_result.get("predicted_price", 0)
  Result: always got 0 → decision engine was ALWAYS comparing last_price to 0

  NEW:  returns {"predicted_price": ..., "predicted_change": ..., ...}
        Both keys present so decision_engine works correctly.
"""

import logging
import warnings

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Public function (called by decision_engine.py)
# ─────────────────────────────────────────────────────────────────────────────

def forecast_prices(prices: list[float], dates: list = None) -> dict:
    """
    Forecast the next price given a list of historical prices.

    Parameters
    ──────────
    prices : list[float]
        Historical modal prices in chronological order.
    dates  : list[str | datetime] | None
        Real trade dates matching each price.
        If None, a WARNING is logged and we fall back to a spaced date index
        (still better than always starting 2024-01-01, but less accurate).

    Returns
    ───────
    dict with keys:
        predicted_price  float   — absolute forecasted price (Rs/quintal)
        predicted_change float   — forecasted price minus last actual price
        confidence       float   — 0.0–1.0
        method           str     — 'prophet' | 'linear_fallback' | etc.
    """
    # ── 1. Clean input ────────────────────────────────────────────────────────
    cleaned_prices = []
    cleaned_dates  = []

    for i, p in enumerate(prices):
        try:
            val = float(p)
            if val > 0:
                cleaned_prices.append(val)
                if dates is not None and i < len(dates):
                    cleaned_dates.append(dates[i])
        except (ValueError, TypeError):
            continue

    # ── 2. Hard minimum checks ────────────────────────────────────────────────
    if len(cleaned_prices) < 2:
        return _result(0.0, 0.0, 0.1, "insufficient_data")

    if len(cleaned_prices) < 5:
        # Not enough points for Prophet; use simple linear extrapolation
        return _linear_forecast(cleaned_prices)

    # ── 3. Build date index ───────────────────────────────────────────────────
    if cleaned_dates and len(cleaned_dates) == len(cleaned_prices):
        ds_series = pd.to_datetime(cleaned_dates)
        log.info("Prophet training on REAL dates: %s → %s",
                 ds_series.min().date(), ds_series.max().date())
    else:
        # Fallback: evenly-spaced weekly dates ending today.
        # Still wrong, but far less wrong than always starting 2024-01-01.
        log.warning(
            "No real dates supplied — using synthetic weekly date index. "
            "Pass dates from mandi_api.fetch_mandi_data() for accurate forecasts."
        )
        ds_series = pd.date_range(
            end    = pd.Timestamp.today(),
            periods= len(cleaned_prices),
            freq   = "W",   # weekly spacing matches typical mandi data density
        )

    # ── 4. Prophet ────────────────────────────────────────────────────────────
    try:
        from prophet import Prophet
    except ImportError:
        log.error("Prophet not installed → linear fallback")
        return _linear_forecast(cleaned_prices)

    try:
        prophet_df = pd.DataFrame({"ds": ds_series, "y": cleaned_prices})

        model = Prophet(
            yearly_seasonality  = True,    # harvest cycles matter for crops
            weekly_seasonality  = False,   # mandis don't trade 7 days/week
            daily_seasonality   = False,   # no intra-day data
            changepoint_prior_scale = 0.05,  # moderate trend flexibility
            interval_width      = 0.80,    # 80 % confidence band
        )

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model.fit(prophet_df)

        future   = model.make_future_dataframe(periods=1, freq="D")
        forecast = model.predict(future)

        predicted_price  = float(forecast["yhat"].iloc[-1])
        predicted_change = predicted_price - float(cleaned_prices[-1])

        return _result(predicted_price, predicted_change, 0.80, "prophet")

    except Exception as e:
        log.error("Prophet failed (%s) → linear fallback", e)
        return _linear_forecast(cleaned_prices)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _linear_forecast(prices: list[float]) -> dict:
    """
    Simple least-squares linear regression as a lightweight fallback.
    Works with as few as 2 data points. No external dependencies beyond numpy.

    Interview answer: "When Prophet can't run (too few points, install error,
    Stan crash), I fall back to fitting a line through the price history and
    extrapolating one step. It's less accurate but never crashes."
    """
    x = np.arange(len(prices), dtype=float)
    y = np.array(prices, dtype=float)

    # np.polyfit degree=1 → y = mx + b
    m, b             = np.polyfit(x, y, 1)
    predicted_price  = float(m * len(prices) + b)   # one step ahead
    predicted_change = predicted_price - prices[-1]

    return _result(predicted_price, predicted_change, 0.50, "linear_fallback")


def _result(
    predicted_price : float,
    predicted_change: float,
    confidence      : float,
    method          : str,
) -> dict:
    """
    Single place that constructs the return dict so the key names are
    consistent across every code path.

    WHY THIS MATTERS:
      The old code had three different return sites with subtly different keys.
      decision_engine.py looked for 'predicted_price' but forecast_model.py
      returned 'predicted_change'. Result: forecast was silently 0 every time.
    """
    return {
        "predicted_price" : round(predicted_price,  2),   # ← key decision_engine needs
        "predicted_change": round(predicted_change, 2),
        "confidence"      : round(confidence,       2),
        "method"          : method,
    }