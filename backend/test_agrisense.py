"""
test_agrisense.py  —  Interview-ready unit tests
═══════════════════════════════════════════════════
Run with:  pytest test_agrisense.py -v
"""

import pytest
from datetime import datetime, timedelta
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# risk_model tests
# ─────────────────────────────────────────────────────────────────────────────

from risk_model import calculate_volatility, calculate_risk_score, get_risk_summary

class TestRiskModel:

    def test_volatility_stable_market(self):
        """Identical prices → zero volatility."""
        assert calculate_volatility([2000, 2000, 2000]) == 0.0

    def test_volatility_is_positive(self):
        assert calculate_volatility([1800, 2000, 2200, 2400]) > 0

    def test_risk_score_range(self):
        """Risk score must always be in [0, 1]."""
        prices = [800, 4000, 1200, 5500, 900]
        vol    = calculate_volatility(prices)
        score  = calculate_risk_score(vol, prices)
        assert 0.0 <= score <= 1.0

    def test_old_bug_fixed(self):
        """
        OLD: risk_score = std / 100
        For prices ~2500 Rs, std ~200 → score 2.0 → clamped to 1.0 (always HIGH).
        NEW: uses CV (std/mean) → score ~0.08 → LOW/MEDIUM, not always HIGH.
        """
        prices = [2400, 2450, 2500, 2550, 2600]
        vol    = calculate_volatility(prices)
        score  = calculate_risk_score(vol, prices)
        # std ≈ 70, mean ≈ 2500, CV ≈ 0.028 — should NOT be 1.0
        assert score < 0.5, f"Expected low risk for stable prices, got {score}"

    def test_high_volatility_market(self):
        """Wide price swings → higher risk score."""
        stable   = [2400, 2450, 2500, 2550, 2600]
        volatile = [1000, 3000, 800,  4500, 1200]
        vol_s    = calculate_volatility(stable)
        vol_v    = calculate_volatility(volatile)
        score_s  = calculate_risk_score(vol_s, stable)
        score_v  = calculate_risk_score(vol_v, volatile)
        assert score_v > score_s

    def test_single_price_returns_zero(self):
        """Can't measure volatility from one data point."""
        assert calculate_volatility([2500]) == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# forecast_model tests
# ─────────────────────────────────────────────────────────────────────────────

from forecast_model import forecast_prices, _result

class TestForecastModel:

    def test_return_keys_present(self):
        """Both 'predicted_price' AND 'predicted_change' must be in result."""
        prices = [2100, 2200, 2300, 2400, 2500, 2550]
        result = forecast_prices(prices)
        assert "predicted_price"  in result, "Missing 'predicted_price' — decision_engine will get 0"
        assert "predicted_change" in result
        assert "confidence"       in result
        assert "method"           in result

    def test_insufficient_data_returns_safe_dict(self):
        result = forecast_prices([2500])
        assert result["predicted_price"] == 0.0
        assert result["method"] == "insufficient_data"

    def test_real_dates_accepted(self):
        """Passing real datetime dates should not raise."""
        today  = datetime.today()
        dates  = [today - timedelta(days=i) for i in range(9, -1, -1)]
        prices = [2000 + i * 30 for i in range(10)]
        result = forecast_prices(prices, dates=dates)
        # With real dates the method should be 'prophet' or 'linear_fallback'
        assert result["method"] in ("prophet", "linear_fallback")

    def test_predicted_price_is_positive(self):
        """Forecasted price should always be positive for commodity data."""
        prices = [2000, 2100, 2200, 2300, 2400, 2500]
        result = forecast_prices(prices)
        if result["method"] not in ("insufficient_data", "simple_average"):
            assert result["predicted_price"] > 0


# ─────────────────────────────────────────────────────────────────────────────
# decision_engine tests
# ─────────────────────────────────────────────────────────────────────────────

from decision_engine import make_decision, _determine_decision

class TestDecisionEngine:

    def test_no_data_returns_no_data(self):
        result = make_decision([])
        assert result["decision"] == "NO DATA"

    def test_decision_is_valid_signal(self):
        valid_signals = {"STRONG BUY", "BUY", "HOLD", "SELL", "STRONG SELL",
                         "NO DATA", "ERROR"}
        prices = [2100, 2200, 2300, 2400, 2500, 2600]
        result = make_decision(prices)
        assert result["decision"] in valid_signals

    def test_result_has_all_required_keys(self):
        required = {"volatility", "risk_score", "risk_level", "predicted_price",
                    "predicted_change", "decision", "confidence", "explanation"}
        result   = make_decision([2000, 2100, 2200, 2300, 2400])
        missing  = required - result.keys()
        assert not missing, f"Missing keys: {missing}"

    def test_decision_matrix_high_risk_big_drop(self):
        assert _determine_decision(-100, "HIGH") == "STRONG SELL"

    def test_decision_matrix_low_risk_rising(self):
        assert _determine_decision(80, "LOW") == "STRONG BUY"

    def test_decision_matrix_medium_risk_stable(self):
        assert _determine_decision(20, "MEDIUM") == "HOLD"

    def test_real_dates_flow_through(self):
        """Passing real dates should not raise and should produce a decision."""
        today  = datetime.today()
        dates  = [today - timedelta(days=i) for i in range(9, -1, -1)]
        prices = [2000 + i * 25 for i in range(10)]
        result = make_decision(prices, dates=dates)
        assert result["decision"] != "ERROR"


# ─────────────────────────────────────────────────────────────────────────────
# mandi_api tests (offline — no real HTTP calls)
# ─────────────────────────────────────────────────────────────────────────────

from unittest.mock import patch, MagicMock
from mandi_api import _parse_date, _parse_records, _fallback_df

class TestMandiAPI:

    def test_parse_date_slash_format(self):
        d = _parse_date("15/01/2024")
        assert d is not None
        assert d.day == 15 and d.month == 1 and d.year == 2024

    def test_parse_date_iso_format(self):
        d = _parse_date("2024-03-20")
        assert d is not None and d.month == 3

    def test_parse_date_invalid_returns_none(self):
        assert _parse_date("not-a-date") is None
        assert _parse_date("")           is None

    def test_parse_records_extracts_date_and_price(self):
        records = [
            {"Arrival_Date": "10/01/2024", "Modal_Price": "2500", "State": "Rajasthan"},
            {"Arrival_Date": "11/01/2024", "Modal_Price": "2600", "State": "Rajasthan"},
        ]
        df = _parse_records(records, "Tomato", "Rajasthan")
        assert "ds" in df.columns
        assert "y"  in df.columns
        assert len(df) == 2
        assert df["y"].iloc[0] == 2500.0

    def test_parse_records_skips_zero_price(self):
        records = [
            {"Arrival_Date": "10/01/2024", "Modal_Price": "0",    "State": "RJ"},
            {"Arrival_Date": "11/01/2024", "Modal_Price": "2600", "State": "RJ"},
        ]
        df = _parse_records(records, "Tomato", "RJ")
        assert len(df) == 1   # zero-price record was skipped

    def test_fallback_returns_correct_shape(self):
        df = _fallback_df("Onion", "Maharashtra", days=30)
        assert len(df) == 30
        assert "ds" in df.columns
        assert "y"  in df.columns
        assert (df["source"] == "fallback").all()

    @patch("mandi_api.requests.Session")
    def test_fetch_falls_back_on_timeout(self, mock_session_cls):
        """Simulate a timeout → function returns a fallback DataFrame, not an exception."""
        import requests as req_lib
        mock_session = MagicMock()
        mock_session.get.side_effect = req_lib.exceptions.Timeout()
        mock_session_cls.return_value = mock_session

        from mandi_api import fetch_mandi_data
        df = fetch_mandi_data("Tomato", state="Rajasthan")
        assert not df.empty
        assert df["source"].iloc[0] == "fallback"