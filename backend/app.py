from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from mandi_api import fetch_prices
from decision_engine import make_decision

app = FastAPI(title="AgriSenseAI - Live Mandi Decision API")

# Allow frontend later
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "message": "AgriSenseAI Live Decision API Running",
        "status": "success"
    }


@app.get("/live-decision")
def live_decision(commodity: str, state: str, limit: int = 10):

    try:
        commodity = commodity.strip().title()
        state = state.strip().title()

        # Try state-level data first
        prices = fetch_prices(commodity, state=state, limit=limit)
        data_source = "state"

        # If no state data → fallback to national
        if not prices:
            prices = fetch_prices(commodity, state=None, limit=limit)
            data_source = "national"

        # If still no data
        if not prices:
            return {
                "commodity": commodity,
                "state": state,
                "data_source": "none",
                "prices_used": [],
                "decision_result": {
                    "volatility": 0,
                    "risk_score": 0,
                    "risk_level": "LOW",
                    "predicted_change": 0,
                    "timestamp": datetime.utcnow().isoformat(),
                    "confidence": 0.1,
                    "decision": "NO DATA",
                    "explanation": "No valid market data available."
                }
            }

        # Run AI decision engine
        result = make_decision(prices)

        return {
            "commodity": commodity,
            "state": state,
            "data_source": data_source,
            "prices_used": prices,
            "decision_result": result
        }

    except Exception as e:
        return {
            "commodity": commodity,
            "state": state,
            "data_source": "error",
            "prices_used": [],
            "decision_result": {
                "volatility": 0,
                "risk_score": 0,
                "risk_level": "LOW",
                "predicted_change": 0,
                "confidence": 0.0,
                "decision": "ERROR",
                "explanation": f"Live decision failed safely: {str(e)}"
            }
        }
