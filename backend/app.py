"""
app.py  —  FastAPI entry point for AgriSense AI
═════════════════════════════════════════════════

BUGS FIXED vs old app.py:
──────────────────────────
1. CORSMiddleware was imported TWICE (duplicate import at line 6 and 13).
   Python silently ignores the duplicate but it signals sloppy code to
   an interviewer reading it.

2. MongoDB credentials were hardcoded:
       MONGO_URL = "mongodb+srv://rishitabohra1575:ganeshji123@..."
   Anyone who opens the file (or sees it in a GitHub repo) has full DB access.
   Fixed: MONGO_URL lives in .env only; database.py reads os.getenv("MONGO_URL").

3. The bare `except Exception as e` at the route level swallowed ALL errors
   including import errors and typos, returning a fake "success" response.
   Fixed: we still catch broad exceptions to keep the API alive, but now we
   log the full traceback so errors are findable.

4. mandi_api.fetch_prices() only returned prices (list[float]), so decision_engine
   never received real dates → Prophet used fake dates.
   Fixed: we now call fetch_mandi_data() which returns a DataFrame with both
   'ds' (real dates) and 'y' (prices), and pass both into make_decision().

5. data_source logic assumed empty list = fallback, but fetch_prices() already
   returns a fallback internally. We now read the 'source' column from the
   DataFrame to know truthfully whether data came from the API or a fallback.

Architecture you can explain:
  Request → app.py → mandi_api (prices + dates)
                    → decision_engine (risk + forecast)
                    → database (async write, fire-and-forget)
                    → JSON response
"""

import logging
import traceback

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from mandi_api      import fetch_mandi_data
from decision_engine import make_decision
from database        import save_decision

log = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title       = "AgriSense AI — Live Mandi Decision API",
    description = "Real-time buy/sell/hold signals for Indian agricultural commodities",
    version     = "2.0.0",
)

# ── CORS (single import, single add_middleware call) ──────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://agrisenseai-five.vercel.app",
    ],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def home():
    return {
        "message": "AgriSense AI API is running",
        "status" : "ok",
        "docs"   : "/docs",
    }


@app.get("/live-decision")
def live_decision(
    commodity: str = Query(..., description="e.g. Tomato, Onion, Potato"),
    state    : str = Query(..., description="e.g. Rajasthan, Maharashtra"),
    limit    : int = Query(50,  description="Max price records to fetch"),
):
    """
    Main endpoint: fetch mandi prices and return a trading decision.

    Flow:
      1. Try state-level data
      2. If empty → try national data
      3. Pass BOTH prices AND real dates to make_decision()
      4. Persist result to MongoDB (best-effort, won't crash if DB is down)
      5. Return decision JSON

    The key improvement over v1:
      We pass df["ds"] (real arrival dates) into make_decision() →
      forecast_model passes them into Prophet → Prophet trains on a
      genuine time axis instead of a fake date_range("2024-01-01").
    """
    commodity = commodity.strip().title()
    state     = state.strip().title()

    try:
        # ── Step 1: state-level data ─────────────────────────────────────────
        df = fetch_mandi_data(commodity, state=state, limit=limit)

        # ── Step 2: national fallback if state returned nothing ───────────────
        if df.empty or (df["source"] == "fallback").all():
            log.info("No state data for %s/%s — trying national.", commodity, state)
            df = fetch_mandi_data(commodity, state=None, limit=limit)

        data_source = df["source"].iloc[0] if not df.empty else "unknown"
        prices      = df["y"].tolist()
        dates       = df["ds"].tolist()   # ← REAL DATES (the core fix)

        # ── Step 3: run decision engine ───────────────────────────────────────
        result = make_decision(prices, dates=dates)

        # ── Step 4: persist (fire-and-forget; never crash the response) ───────
        saved = save_decision(commodity, state, result)
        if not saved:
            log.warning("DB write skipped for %s/%s", commodity, state)

        # ── Step 5: return ────────────────────────────────────────────────────
        return {
            "commodity"      : commodity,
            "state"          : state,
            "data_source"    : data_source,
            "n_records"      : len(prices),
            "prices_used"    : prices[-10:],   # last 10 only — keep response small
            "decision_result": result,
        }

    except Exception as e:
        # Log the full traceback so we can debug — but return a safe JSON response
        log.error("Unhandled error in /live-decision:\n%s", traceback.format_exc())
        return {
            "commodity"      : commodity,
            "state"          : state,
            "data_source"    : "error",
            "n_records"      : 0,
            "prices_used"    : [],
            "decision_result": {
                "decision"   : "ERROR",
                "explanation": f"Request failed safely: {str(e)}",
                "confidence" : 0.0,
            },
        }