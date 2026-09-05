"""
Tests — Metrics Calculation

Covers:
- Empty outcomes returns zero metrics
- All required metric keys present
- Recovery rate formula
- Revenue recovery efficiency formula
- Net recovery value formula
- Safety violation count
- compute_aggregate_stats across seeds
"""

import pytest
from typing import List

from ml.src.simulation.types import (
    SimulationOutcome,
    OutcomeType,
    RecoveryAction,
    RecoveryState,
)
from ml.src.simulation.scoring.metrics import compute_metrics, compute_aggregate_stats


REQUIRED_METRIC_KEYS = {
    "total_transactions",
    "successful_recoveries",
    "failed_recoveries",
    "blocked_transactions",
    "stopped_transactions",
    "merchant_review_transactions",
    "revenue_at_risk",
    "eligible_revenue",
    "recovered_revenue",
    "recovery_rate",
    "revenue_recovery_efficiency",
    "average_recovery_attempts",
    "total_attempts",
    "total_friction_cost",
    "total_action_cost",
    "total_risk_cost",
    "safety_violation_count",
    "safety_violation_rate",
    "net_recovery_value",
    "average_time_to_recovery_hours",
}


def _make_outcome(
    txn_id: str,
    outcome: OutcomeType,
    recovered: float,
    attempts: int = 1,
    friction: float = 1.0,
    action_cost: float = 0.5,
    risk_cost: float = 10.0,
    policy_violation: bool = False,
) -> SimulationOutcome:
    return SimulationOutcome(
        transaction_id=txn_id,
        strategy_name="TestStrategy",
        selected_actions=[RecoveryAction.RETRY],
        true_recovery_probability=0.70,
        outcome=outcome,
        recovered_amount=recovered,
        attempts=attempts,
        retry_count=attempts,
        time_to_recovery_hours=0.5,
        friction_cost=friction,
        action_cost=action_cost,
        risk_cost=risk_cost,
        policy_violation=policy_violation,
        state_history=[RecoveryState.FAILED, RecoveryState.RECOVERED],
        timestamp="2026-01-01T00:00:00Z",
    )


class TestEmptyMetrics:

    def test_empty_outcomes_returns_zeros(self):
        m = compute_metrics([], {})
        assert m["total_transactions"] == 0
        assert m["recovery_rate"] == 0.0
        assert m["recovered_revenue"] == 0.0

    def test_empty_metrics_has_all_required_keys(self):
        m = compute_metrics([], {})
        for key in REQUIRED_METRIC_KEYS:
            assert key in m, f"Missing metric key: {key}"


class TestMetricKeys:

    def test_all_required_keys_present(self):
        outcomes = [_make_outcome("txn_1", OutcomeType.SUCCESS, 1000.0)]
        amounts  = {"txn_1": 1000.0}
        m        = compute_metrics(outcomes, amounts)
        for key in REQUIRED_METRIC_KEYS:
            assert key in m, f"Missing metric key: {key}"


class TestCountMetrics:

    def test_total_transactions(self):
        outcomes = [
            _make_outcome("t1", OutcomeType.SUCCESS, 1000.0),
            _make_outcome("t2", OutcomeType.FAILED,  0.0),
            _make_outcome("t3", OutcomeType.STOPPED, 0.0),
        ]
        amounts = {"t1": 1000.0, "t2": 500.0, "t3": 750.0}
        m = compute_metrics(outcomes, amounts)
        assert m["total_transactions"] == 3

    def test_successful_recoveries_count(self):
        outcomes = [
            _make_outcome("t1", OutcomeType.SUCCESS, 1000.0),
            _make_outcome("t2", OutcomeType.SUCCESS, 2000.0),
            _make_outcome("t3", OutcomeType.FAILED,  0.0),
        ]
        amounts = {"t1": 1000.0, "t2": 2000.0, "t3": 500.0}
        m = compute_metrics(outcomes, amounts)
        assert m["successful_recoveries"] == 2

    def test_stopped_transactions_count(self):
        outcomes = [
            _make_outcome("t1", OutcomeType.STOPPED,    0.0),
            _make_outcome("t2", OutcomeType.STOPPED,    0.0),
            _make_outcome("t3", OutcomeType.SUCCESS,  500.0),
        ]
        amounts = {"t1": 300.0, "t2": 400.0, "t3": 500.0}
        m = compute_metrics(outcomes, amounts)
        assert m["stopped_transactions"] == 2


class TestRevenueMetrics:

    def test_revenue_at_risk_is_sum_of_all_amounts(self):
        outcomes = [
            _make_outcome("t1", OutcomeType.SUCCESS, 1000.0),
            _make_outcome("t2", OutcomeType.FAILED,  0.0),
        ]
        amounts = {"t1": 1000.0, "t2": 500.0}
        m = compute_metrics(outcomes, amounts)
        assert m["revenue_at_risk"] == pytest.approx(1500.0)

    def test_recovered_revenue_sum(self):
        outcomes = [
            _make_outcome("t1", OutcomeType.SUCCESS, 1000.0),
            _make_outcome("t2", OutcomeType.SUCCESS, 2000.0),
            _make_outcome("t3", OutcomeType.FAILED,  0.0),
        ]
        amounts = {"t1": 1000.0, "t2": 2000.0, "t3": 500.0}
        m = compute_metrics(outcomes, amounts)
        assert m["recovered_revenue"] == pytest.approx(3000.0)


class TestRateMetrics:

    def test_recovery_rate_formula(self):
        """recovery_rate = successful / eligible (non-BLOCKED)"""
        outcomes = [
            _make_outcome("t1", OutcomeType.SUCCESS, 1000.0),
            _make_outcome("t2", OutcomeType.FAILED,  0.0),
            _make_outcome("t3", OutcomeType.FAILED,  0.0),
            _make_outcome("t4", OutcomeType.BLOCKED,  0.0),
        ]
        amounts = {"t1": 1000.0, "t2": 500.0, "t3": 300.0, "t4": 400.0}
        m = compute_metrics(outcomes, amounts)
        # eligible = 3 (t1, t2, t3 — t4 is BLOCKED)
        # successful = 1 (t1)
        expected_rate = 1 / 3
        assert m["recovery_rate"] == pytest.approx(expected_rate, abs=1e-6)

    def test_revenue_recovery_efficiency_formula(self):
        """revenue_recovery_efficiency = recovered / eligible_revenue"""
        outcomes = [
            _make_outcome("t1", OutcomeType.SUCCESS, 1000.0),
            _make_outcome("t2", OutcomeType.FAILED,  0.0),
            _make_outcome("t3", OutcomeType.BLOCKED, 0.0),  # not eligible
        ]
        amounts = {"t1": 1000.0, "t2": 500.0, "t3": 999.0}
        m = compute_metrics(outcomes, amounts)
        # eligible_revenue = 1000 + 500 = 1500
        # recovered = 1000
        expected = 1000.0 / 1500.0
        assert m["revenue_recovery_efficiency"] == pytest.approx(expected, abs=1e-6)

    def test_zero_eligible_returns_zero_rate(self):
        """If all transactions are BLOCKED, rates must be 0."""
        outcomes = [
            _make_outcome("t1", OutcomeType.BLOCKED, 0.0),
            _make_outcome("t2", OutcomeType.BLOCKED, 0.0),
        ]
        amounts = {"t1": 1000.0, "t2": 500.0}
        m = compute_metrics(outcomes, amounts)
        assert m["recovery_rate"] == 0.0
        assert m["revenue_recovery_efficiency"] == 0.0


class TestCostMetrics:

    def test_total_friction_cost_sum(self):
        outcomes = [
            _make_outcome("t1", OutcomeType.SUCCESS, 1000.0, friction=3.0),
            _make_outcome("t2", OutcomeType.FAILED,  0.0,    friction=1.0),
        ]
        amounts = {"t1": 1000.0, "t2": 500.0}
        m = compute_metrics(outcomes, amounts)
        assert m["total_friction_cost"] == pytest.approx(4.0)

    def test_total_action_cost_sum(self):
        outcomes = [
            _make_outcome("t1", OutcomeType.SUCCESS, 1000.0, action_cost=1.0),
            _make_outcome("t2", OutcomeType.FAILED,  0.0,    action_cost=0.5),
        ]
        amounts = {"t1": 1000.0, "t2": 500.0}
        m = compute_metrics(outcomes, amounts)
        assert m["total_action_cost"] == pytest.approx(1.5)

    def test_net_recovery_value_formula(self):
        """net_recovery_value = recovered - risk_cost - friction - action_cost"""
        outcomes = [
            _make_outcome("t1", OutcomeType.SUCCESS, 1000.0,
                          friction=3.0, action_cost=1.0, risk_cost=50.0),
        ]
        amounts = {"t1": 1000.0}
        m = compute_metrics(outcomes, amounts)
        expected = 1000.0 - 50.0 - 3.0 - 1.0
        assert m["net_recovery_value"] == pytest.approx(expected, abs=0.01)


class TestSafetyMetrics:

    def test_safety_violation_count(self):
        outcomes = [
            _make_outcome("t1", OutcomeType.SUCCESS, 1000.0, policy_violation=True),
            _make_outcome("t2", OutcomeType.FAILED,  0.0,    policy_violation=False),
            _make_outcome("t3", OutcomeType.STOPPED, 0.0,    policy_violation=True),
        ]
        amounts = {"t1": 1000.0, "t2": 500.0, "t3": 300.0}
        m = compute_metrics(outcomes, amounts)
        assert m["safety_violation_count"] == 2

    def test_safety_violation_rate_formula(self):
        outcomes = [
            _make_outcome("t1", OutcomeType.SUCCESS, 1000.0, policy_violation=True),
            _make_outcome("t2", OutcomeType.FAILED,  0.0,    policy_violation=False),
        ]
        amounts = {"t1": 1000.0, "t2": 500.0}
        m = compute_metrics(outcomes, amounts)
        assert m["safety_violation_rate"] == pytest.approx(0.5)


class TestAggregateStats:

    def test_aggregate_stats_mean(self):
        per_seed = [
            {"recovery_rate": 0.40},
            {"recovery_rate": 0.60},
        ]
        agg = compute_aggregate_stats(per_seed)
        assert agg["recovery_rate"]["mean"] == pytest.approx(0.50)

    def test_aggregate_stats_min_max(self):
        per_seed = [
            {"recovery_rate": 0.40},
            {"recovery_rate": 0.60},
            {"recovery_rate": 0.50},
        ]
        agg = compute_aggregate_stats(per_seed)
        assert agg["recovery_rate"]["min"] == pytest.approx(0.40)
        assert agg["recovery_rate"]["max"] == pytest.approx(0.60)

    def test_aggregate_stats_std_dev(self):
        per_seed = [
            {"v": 10.0},
            {"v": 10.0},
        ]
        agg = compute_aggregate_stats(per_seed)
        assert agg["v"]["std_dev"] == pytest.approx(0.0)

    def test_empty_per_seed_returns_empty(self):
        agg = compute_aggregate_stats([])
        assert agg == {}
