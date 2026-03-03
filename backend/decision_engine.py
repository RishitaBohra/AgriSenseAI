from risk_model import calculate_volatility, calculate_risk_score
from forecast_model import forecast_prices


def determine_risk_level(risk_score):
    if risk_score < 0.3:
        return "LOW"
    elif risk_score < 0.7:
        return "MEDIUM"
    return "HIGH"


def determine_decision(predicted_change, risk_level):
    if risk_level == "HIGH" and predicted_change < -50:
        return "STRONG SELL"
    elif predicted_change < 0:
        return "SELL"
    elif predicted_change > 50:
        return "STRONG BUY"
    elif predicted_change > 0:
        return "BUY"
    else:
        return "HOLD"

def make_decision(prices):
    try:
        # Safety check
        if not prices or len(prices) < 2:
            return {
                "volatility": 0,
                "risk_score": 0,
                "risk_level": "LOW",
                "predicted_change": 0,
                "confidence": 0.1,
                "decision": "NO DATA",
                "explanation": "Not enough price data."
            }

        # Ensure all are floats
        prices = [float(p) for p in prices]

        volatility = calculate_volatility(prices)
        risk_score = calculate_risk_score(volatility)
        risk_level = determine_risk_level(risk_score)

        # 🔥 IMPORTANT FIX HERE
        forecast_result = forecast_prices(prices)

        # If forecast returns dict → extract value
        if isinstance(forecast_result, dict):
            forecasted_price = float(
                forecast_result.get("predicted_price", 0)
            )
        else:
            forecasted_price = float(forecast_result)

        last_actual = float(prices[-1])
        predicted_change = forecasted_price - last_actual

        confidence = round(max(0.1, 1 - risk_score), 2)

        decision = determine_decision(predicted_change, risk_level)

        explanation = (
            f"Volatility is {volatility:.2f}, "
            f"risk level is {risk_level}, "
            f"predicted change is {predicted_change:.2f}."
        )

        trend = "UPTREND" if predicted_change > 0 else "DOWNTREND"

        return {
            "volatility": round(volatility, 2),
            "risk_score": round(risk_score, 3),
            "risk_level": risk_level,
            "predicted_change": round(predicted_change, 2),
            "trend": trend,
            "confidence": round(confidence, 2),
            "decision": decision,
            "explanation": explanation
        }

    except Exception as e:
        return {
            "volatility": 0,
            "risk_score": 0,
            "risk_level": "LOW",
            "predicted_change": 0,
            "confidence": 0,
            "decision": "ERROR",
            "explanation": f"Decision engine failed safely: {str(e)}"
        }
