from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

from mandi_api import fetch_prices
from decision_engine import make_decision

app = FastAPI(
    title="AgriSenseAI - Live Mandi Decision API"
)

# Enable frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://agrisenseai-five.vercel.app"
    ],
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
def live_decision(
    commodity: str,
    state: str,
    limit: int = 10
):

    try:

        commodity = commodity.strip().title()
        state = state.strip().title()

        print("API called")

        # Fetch state-level mandi prices
        print("Fetching mandi prices...")

        prices = fetch_prices(
            commodity,
            state=state,
            limit=limit
        )

        print("Fetched prices successfully")
        print(prices)

        data_source = "state"

        # Fallback to national data
        if not prices:

            print("No state data found. Trying national data...")

            prices = fetch_prices(
                commodity,
                state=None,
                limit=limit
            )

            data_source = "national"

        # Demo fallback if government API fails
        if not prices:

            print("Using demo fallback data")

            return {
                "commodity": commodity,
                "state": state,
                "data_source": "demo",
                "prices_used": [2200, 2300, 2400, 2500],
                "decision_result": {
                    "volatility": 12.5,
                    "risk_score": 35,
                    "risk_level": "MEDIUM",
                    "predicted_change": 8.4,
                    "timestamp": datetime.utcnow().isoformat(),
                    "confidence": 0.82,
                    "decision": "BUY",
                    "explanation": (
                        "Tomato prices are expected to rise "
                        "due to low market volatility and "
                        "increasing market demand."
                    )
                }
            }

        print("Running AI decision engine...")

        # Run AI decision engine
        result = make_decision(prices)

        print("AI decision complete")

        return {
            "commodity": commodity,
            "state": state,
            "data_source": data_source,
            "prices_used": prices,
            "decision_result": result
        }

    except Exception as e:

        print("API ERROR:", str(e))

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
                "explanation": (
                    f"Live decision failed safely: {str(e)}"
                )
            }
        }