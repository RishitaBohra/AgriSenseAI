import numpy as np

def calculate_volatility(prices):
    return float(np.std(prices))

def calculate_risk_score(volatility: float) -> float:
    risk_score = volatility / 100
    return min(max(risk_score, 0), 1)

def get_risk_level(risk_score):
    if risk_score < 0.1:
        return "LOW"
    elif risk_score < 0.2:
        return "MEDIUM"
    else:
        return "HIGH"

