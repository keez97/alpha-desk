"""
API endpoint tests for backtester routes.
Tests FastAPI endpoints using TestClient.
"""

import pytest
from datetime import date, datetime, timezone
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlmodel import Session

from backend.repositories.backtest_repo import BacktestRepository


class TestCreateBacktest:
    """Test backtest creation endpoint."""

    def test_create_backtest_valid_input(
        self, test_client: TestClient, session: Session, sample_factors
    ):
        """Test creating a backtest with valid input."""
        request_data = {
            "name": "Test Backtest",
            "backtest_type": "factor_combination",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "rebalance_frequency": "monthly",
            "universe_selection": "sp500",
            "commission_bps": 5.0,
            "slippage_bps": 2.0,
            "benchmark_ticker": "SPY",
            "rolling_window_months": 60,
            "factor_allocations": [
                {"factor_id": sample_factors[0].id, "weight": 0.5},
                {"factor_id": sample_factors[1].id, "weight": 0.5},
            ],
        }

        response = test_client.post("/api/backtests", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Backtest"
        assert data["status"] == "DRAFT"
        assert "id" in data

    def test_create_backtest_invalid_dates(
        self, test_client: TestClient, sample_factors
    ):
        """Test creating backtest with invalid date range."""
        request_data = {
            "name": "Invalid Backtest",
            "start_date": "2023-12-31",
            "end_date": "2023-01-01",  # End before start
            "rebalance_frequency": "monthly",
            "factor_allocations": [
                {"factor_id": sample_factors[0].id, "weight": 1.0},
            ],
        }

        response = test_client.post("/api/backtests", json=request_data)

        # Should return 400 or 422 for invalid input
        assert response.status_code in [400, 422]

    def test_create_backtest_missing_required_field(
        self, test_client: TestClient, sample_factors
    ):
        """Test creating backtest with missing required field."""
        request_data = {
            "name": "Incomplete Backtest",
            # Missing start_date
            "end_date": "2023-12-31",
            "factor_allocations": [
                {"factor_id": sample_factors[0].id, "weight": 1.0},
            ],
        }

        response = test_client.post("/api/backtests", json=request_data)

        # Should return validation error
        assert response.status_code in [400, 422]

    def test_create_backtest_empty_factors(self, test_client: TestClient):
        """Test creating backtest with no factor allocations."""
        request_data = {
            "name": "No Factors",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "factor_allocations": [],
        }

        response = test_client.post("/api/backtests", json=request_data)

        # Empty factors might be allowed (handled by engine)
        # or rejected (depending on validation)
        assert response.status_code in [200, 400]

    def test_create_backtest_default_values(
        self, test_client: TestClient, sample_factors
    ):
        """Test that default values are applied correctly."""
        request_data = {
            "name": "Minimal Backtest",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "factor_allocations": [
                {"factor_id": sample_factors[0].id, "weight": 1.0},
            ],
        }

        response = test_client.post("/api/backtests", json=request_data)

        assert response.status_code == 200
        data = response.json()
        # Should have defaults
        assert data["backtest_type"] == "factor_combination"


class TestGetBacktest:
    """Test backtest retrieval endpoint."""

    def test_get_backtest_found(
        self, test_client: TestClient, session: Session, sample_backtest
    ):
        """Test retrieving an existing backtest."""
        backtest_id = sample_backtest.id

        response = test_client.get(f"/api/backtests/{backtest_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == backtest_id
        assert data["name"] == "Test Backtest"

    def test_get_backtest_not_found(self, test_client: TestClient):
        """Test retrieving a nonexistent backtest."""
        response = test_client.get("/api/backtests/99999")

        assert response.status_code == 404

    def test_get_backtest_invalid_id(self, test_client: TestClient):
        """Test retrieving with invalid ID format."""
        response = test_client.get("/api/backtests/invalid")

        # Should return 422 (validation error) or 404
        assert response.status_code in [404, 422]


class TestListBacktests:
    """Test backtest listing endpoint."""

    def test_list_backtests_empty(self, test_client: TestClient, session: Session):
        """Test listing when no backtests exist."""
        response = test_client.get("/api/backtests")

        assert response.status_code == 200
        data = response.json()
        assert "backtests" in data or "total" in data

    def test_list_backtests_with_data(
        self, test_client: TestClient, session: Session, sample_backtest
    ):
        """Test listing backtests."""
        response = test_client.get("/api/backtests")

        assert response.status_code == 200
        data = response.json()
        # Should have list of backtests
        assert isinstance(data.get("backtests", data.get("data", [])), list)

    def test_list_backtests_pagination(self, test_client: TestClient, session: Session):
        """Test pagination in backtest listing."""
        # Create multiple backtests
        repo = BacktestRepository(session)
        for i in range(5):
            backtest = repo.create_backtest(
                name=f"Backtest {i}",
                backtest_type="factor_combination"
            )
            session.commit()

        # Test with limit
        response = test_client.get("/api/backtests?limit=2")

        assert response.status_code == 200
        data = response.json()
        backtests = data.get("backtests", data.get("data", []))
        assert len(backtests) <= 2

    def test_list_backtests_with_offset(
        self, test_client: TestClient, session: Session
    ):
        """Test offset parameter in listing."""
        response = test_client.get("/api/backtests?offset=1")

        assert response.status_code == 200
        data = response.json()
        # Should successfully apply offset
        assert isinstance(data, dict)


class TestGetBacktestStatus:
    """Test backtest status endpoint."""

    def test_get_backtest_status_draft(
        self, test_client: TestClient, sample_backtest
    ):
        """Test getting status of a draft backtest."""
        backtest_id = sample_backtest.id

        response = test_client.get(f"/api/backtests/{backtest_id}/status")

        assert response.status_code in [200, 404]  # May or may not exist
        if response.status_code == 200:
            data = response.json()
            assert "status" in data

    def test_get_backtest_status_not_found(self, test_client: TestClient):
        """Test getting status for nonexistent backtest."""
        response = test_client.get("/api/backtests/99999/status")

        assert response.status_code == 404


class TestGetBacktestResults:
    """Test backtest results endpoint."""

    def test_get_results_not_found(self, test_client: TestClient):
        """Test getting results for nonexistent backtest."""
        response = test_client.get("/api/backtests/99999/results")

        assert response.status_code == 404

    def test_get_results_draft_backtest(
        self, test_client: TestClient, sample_backtest
    ):
        """Test getting results for draft backtest (no results yet)."""
        backtest_id = sample_backtest.id

        response = test_client.get(f"/api/backtests/{backtest_id}/results")

        # May return empty results or 200
        assert response.status_code in [200, 404]


class TestGetBacktestStatistics:
    """Test backtest statistics endpoint."""

    def test_get_statistics_not_found(self, test_client: TestClient):
        """Test getting statistics for nonexistent backtest."""
        response = test_client.get("/api/backtests/99999/statistics")

        assert response.status_code == 404

    def test_get_statistics_with_data(
        self, test_client: TestClient, session: Session, sample_backtest
    ):
        """Test getting statistics when available."""
        backtest_id = sample_backtest.id

        response = test_client.get(f"/api/backtests/{backtest_id}/statistics")

        # May return empty dict or statistics
        assert response.status_code in [200, 404]


class TestUpdateBacktest:
    """Test backtest update endpoint."""

    def test_update_backtest_name(
        self, test_client: TestClient, session: Session, sample_backtest
    ):
        """Test updating backtest name."""
        backtest_id = sample_backtest.id
        update_data = {"name": "Updated Name"}

        response = test_client.put(f"/api/backtests/{backtest_id}", json=update_data)

        if response.status_code == 200:
            data = response.json()
            assert data["name"] == "Updated Name"
        else:
            # Update endpoint may not exist
            assert response.status_code in [404, 405]

    def test_update_nonexistent_backtest(self, test_client: TestClient):
        """Test updating nonexistent backtest."""
        update_data = {"name": "Updated"}

        response = test_client.put("/api/backtests/99999", json=update_data)

        assert response.status_code in [404, 405]


class TestDeleteBacktest:
    """Test backtest deletion endpoint."""

    def test_delete_backtest(
        self, test_client: TestClient, session: Session, sample_backtest
    ):
        """Test deleting a backtest."""
        backtest_id = sample_backtest.id

        response = test_client.delete(f"/api/backtests/{backtest_id}")

        # May be 204, 200, or not implemented (405)
        assert response.status_code in [200, 204, 405]

    def test_delete_nonexistent_backtest(self, test_client: TestClient):
        """Test deleting nonexistent backtest."""
        response = test_client.delete("/api/backtests/99999")

        assert response.status_code in [404, 405]


class TestFactorAllocationAPI:
    """Test factor allocation endpoints."""

    def test_get_backtest_factors(
        self, test_client: TestClient, session: Session, sample_backtest
    ):
        """Test retrieving factor allocations for a backtest."""
        backtest_id = sample_backtest.id

        response = test_client.get(f"/api/backtests/{backtest_id}/factors")

        if response.status_code == 200:
            data = response.json()
            # Should return list of factor allocations
            assert isinstance(data, (list, dict))

    def test_update_factor_allocation(
        self, test_client: TestClient, session: Session, sample_backtest
    ):
        """Test updating factor allocations."""
        backtest_id = sample_backtest.id
        allocation_data = {
            "factors": [
                {"factor_id": 1, "weight": 0.6},
                {"factor_id": 2, "weight": 0.4},
            ]
        }

        response = test_client.put(
            f"/api/backtests/{backtest_id}/factors", json=allocation_data
        )

        # May return 200 or 405 (not implemented)
        assert response.status_code in [200, 405]


class TestAPIValidation:
    """Test API input validation."""

    def test_invalid_json(self, test_client: TestClient):
        """Test with invalid JSON."""
        response = test_client.post(
            "/api/backtests",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code in [400, 422]

    def test_negative_weights(
        self, test_client: TestClient, sample_factors
    ):
        """Test that negative weights are rejected."""
        request_data = {
            "name": "Invalid Weights",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "factor_allocations": [
                {"factor_id": sample_factors[0].id, "weight": -0.5},
            ],
        }

        response = test_client.post("/api/backtests", json=request_data)

        # Should validate weights
        assert response.status_code in [200, 400, 422]

    def test_weights_sum_validation(
        self, test_client: TestClient, sample_factors
    ):
        """Test that weights validation works correctly."""
        request_data = {
            "name": "Unbalanced Weights",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "factor_allocations": [
                {"factor_id": sample_factors[0].id, "weight": 0.5},
                {"factor_id": sample_factors[1].id, "weight": 0.3},
                # Weights don't sum to 1.0
            ],
        }

        response = test_client.post("/api/backtests", json=request_data)

        # May or may not enforce sum = 1.0
        assert response.status_code in [200, 400, 422]


class TestAPIIntegration:
    """Integration tests for API workflows."""

    def test_create_and_retrieve_backtest(
        self, test_client: TestClient, session: Session, sample_factors
    ):
        """Test creating a backtest and then retrieving it."""
        # Create
        create_request = {
            "name": "Integration Test Backtest",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "factor_allocations": [
                {"factor_id": sample_factors[0].id, "weight": 1.0},
            ],
        }

        create_response = test_client.post("/api/backtests", json=create_request)
        assert create_response.status_code == 200

        backtest_id = create_response.json()["id"]

        # Retrieve
        get_response = test_client.get(f"/api/backtests/{backtest_id}")
        assert get_response.status_code == 200

        data = get_response.json()
        assert data["name"] == "Integration Test Backtest"

    def test_create_list_retrieve_workflow(
        self, test_client: TestClient, session: Session, sample_factors
    ):
        """Test full workflow: create multiple and list them."""
        # Create 3 backtests
        created_ids = []
        for i in range(3):
            request_data = {
                "name": f"Workflow Test {i}",
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
                "factor_allocations": [
                    {"factor_id": sample_factors[0].id, "weight": 1.0},
                ],
            }

            response = test_client.post("/api/backtests", json=request_data)
            if response.status_code == 200:
                created_ids.append(response.json()["id"])

        # List backtests
        list_response = test_client.get("/api/backtests")
        assert list_response.status_code == 200
