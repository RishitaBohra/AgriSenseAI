import pandas as pd
from prophet import Prophet
import numpy as np

def forecast_prices(prices):

    # Convert safely
    cleaned_prices = []

    for p in prices:
        try:
            val = float(p)
            if val > 0:
                cleaned_prices.append(val)
        except:
            continue

    # 🔴 HARD SAFETY CHECK
    if len(cleaned_prices) < 2:
        return {
            "predicted_change": 0.0,
            "confidence": 0.1,
            "method": "insufficient_data"
        }

    if len(cleaned_prices) < 5:
        avg_price = np.mean(cleaned_prices)
        return {
            "predicted_change": 0.0,
            "confidence": 0.3,
            "method": "simple_average"
        }

    # Prophet safe execution
    try:
        df = pd.DataFrame({
            "ds": pd.date_range(start="2024-01-01", periods=len(cleaned_prices)),
            "y": cleaned_prices
        })

        model = Prophet()
        model.fit(df)

        future = model.make_future_dataframe(periods=1)
        forecast = model.predict(future)

        predicted_price = forecast["yhat"].iloc[-1]
        last_price = cleaned_prices[-1]

        change = predicted_price - last_price

        return {
            "predicted_change": float(change),
            "confidence": 0.8,
            "method": "prophet"
        }

    except Exception as e:
        return {
            "predicted_change": 0.0,
            "confidence": 0.2,
            "method": "prophet_failed_fallback"
        }
