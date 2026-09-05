"""
RecoverAI Simulation — Metrics Calculation

Computes all simulation metrics from a list of SimulationOutcome records.

==============================================================================
METRIC DEFINITIONS AND FORMULAS
==============================================================================

All metrics are simulation metrics only. They do NOT represent real Razorpay
production metrics or real revenue figures.

─────────────────────────────────────────────────────────────────────────────
TRANSACTION COUNT METRICS
─────────────────────────────────────────────────────────────────────────────

total_transactions : int
    Total number of transactions in the simulation batch.
    = len(outcomes)

successful_recoveries : int
    Transactions where outcome == SUCCESS.
    = count(outcome.outcome == SUCCESS)

failed_recoveries : int
    Transactions where recovery was attempted but outcome == FAILED.
    = count(outcome.outcome == FAILED)

stopped_transactions : int
    Transactions where recovery was STOPPED (opt-out, limits, safety).
    = count(outcome.outcome == STOPPED or outcome.outcome == BLOCKED)

merchant_review_transactions : int
    Transactions escalated to MERCHANT_REVIEW.
    = count(outcome.outcome == MERCHANT_REVIEW)

─────────────────────────────────────────────────────────────────────────────
REVENUE METRICS
─────────────────────────────────────────────────────────────────────────────

revenue_at_risk : float (INR)
    Total transaction value of all failed transactions.
    = sum(outcome.transaction_amount for all transactions)
    Note: This requires access to original transaction data.
    Passed as a parameter computed from the dataset.

eligible_revenue : float (INR)
    Total transaction value of transactions that were eligible for recovery
    (i.e., not BLOCKED — passed initial eligibility checks).
    = sum(amount for outcomes where outcome != BLOCKED)

recovered_revenue : float (INR)
    Total amount actually recovered.
    = sum(outcome.recovered_amount for all outcomes)
    (recovered_amount == 0 for non-SUCCESS outcomes)

─────────────────────────────────────────────────────────────────────────────
RATE METRICS
─────────────────────────────────────────────────────────────────────────────

recovery_rate : float [0, 1]
    Fraction of eligible transactions successfully recovered.
    Formula: successful_recoveries / eligible_count
    Where: eligible_count = total_transactions - blocked_count
    If eligible_count == 0: recovery_rate = 0.0

revenue_recovery_efficiency : float [0, 1]
    Fraction of eligible revenue actually recovered.
    Formula: recovered_revenue / eligible_revenue
    If eligible_revenue == 0: revenue_recovery_efficiency = 0.0

─────────────────────────────────────────────────────────────────────────────
ATTEMPT METRICS
─────────────────────────────────────────────────────────────────────────────

average_recovery_attempts : float
    Mean number of recovery actions per transaction.
    Formula: sum(outcome.attempts) / total_transactions

─────────────────────────────────────────────────────────────────────────────
COST METRICS
─────────────────────────────────────────────────────────────────────────────

total_friction_cost : float
    Sum of all customer friction costs across all transactions and actions.
    = sum(outcome.friction_cost for all outcomes)
    Unit: friction score units (FSU) — simulation assumption

total_action_cost : float
    Sum of all operational action costs.
    = sum(outcome.action_cost for all outcomes)
    Unit: arbitrary cost units (ACU) — simulation assumption

total_risk_cost : float
    Sum of all risk costs.
    = sum(outcome.risk_cost for all outcomes)
    Formula per transaction: risk_score × amount × RISK_COST_MULTIPLIER
    Unit: INR-equivalent — simulation assumption

─────────────────────────────────────────────────────────────────────────────
SAFETY METRICS
─────────────────────────────────────────────────────────────────────────────

safety_violation_count : int
    Number of transactions where a policy violation was recorded.
    = count(outcome.policy_violation == True)

safety_violation_rate : float [0, 1]
    safety_violation_count / total_transactions

─────────────────────────────────────────────────────────────────────────────
NET VALUE METRIC
─────────────────────────────────────────────────────────────────────────────

net_recovery_value : float (INR-equivalent)
    Net value of recovery after costs.

    Formula:
        net_recovery_value = recovered_revenue
                             - total_risk_cost
                             - total_friction_cost
                             - total_action_cost

    IMPORTANT: friction_cost and action_cost are in simulation cost units,
    not INR. This metric is therefore a composite simulation metric, not
    a real financial figure. Interpret comparatively, not absolutely.

    A positive net_recovery_value indicates the strategy is worth running
    relative to its simulated costs. A negative value indicates costs
    exceed recovered revenue under the simulation assumptions.

─────────────────────────────────────────────────────────────────────────────
ALL ASSUMPTIONS
─────────────────────────────────────────────────────────────────────────────

1. All revenue figures are in synthetic INR — not real money.
2. Action costs and friction scores are documented simulation parameters.
3. Risk cost multiplier (0.05) is a simulation assumption.
4. "Eligible" means the transaction entered ANALYZING and was not BLOCKED
   immediately (e.g., opted-out transactions enter but then STOP — still
   counted as eligible for this metric).
5. MERCHANT_REVIEW transactions are not counted as recovered.
"""

import math
import statistics
from typing import List, Dict, Optional

from ml.src.simulation.types import SimulationOutcome, OutcomeType


def compute_metrics(
    outcomes: List[SimulationOutcome],
    transaction_amounts: Dict[str, float],
) -> Dict[str, float]:
    """
    Compute all simulation metrics for a single strategy's outcomes.

    Parameters
    ----------
    outcomes : list[SimulationOutcome]
        All outcomes for one strategy run.
    transaction_amounts : dict[str, float]
        Map of transaction_id → amount (INR). Needed for revenue metrics.
        All transactions, including those that were BLOCKED.

    Returns
    -------
    dict
        All metric names → values. See module docstring for formulas.
    """
    n = len(outcomes)
    if n == 0:
        return _empty_metrics()

    # ── Count metrics ──────────────────────────────────────────────────────
    successful   = [o for o in outcomes if o.outcome == OutcomeType.SUCCESS]
    failed_rec   = [o for o in outcomes if o.outcome == OutcomeType.FAILED]
    blocked      = [o for o in outcomes if o.outcome == OutcomeType.BLOCKED]
    stopped      = [o for o in outcomes
                    if o.outcome in (OutcomeType.STOPPED,)]
    merchant_rev = [o for o in outcomes if o.outcome == OutcomeType.MERCHANT_REVIEW]

    total_transactions       = n
    successful_recoveries    = len(successful)
    failed_recoveries        = len(failed_rec)
    blocked_count            = len(blocked)
    stopped_transactions     = len(stopped)
    merchant_review_count    = len(merchant_rev)

    # ── Revenue metrics ────────────────────────────────────────────────────
    # revenue_at_risk: total value of ALL failed transactions in dataset
    revenue_at_risk = sum(transaction_amounts.values())

    # eligible: non-BLOCKED transactions
    eligible_outcomes = [o for o in outcomes if o.outcome != OutcomeType.BLOCKED]
    eligible_count    = len(eligible_outcomes)
    eligible_revenue  = sum(
        transaction_amounts.get(o.transaction_id, 0.0)
        for o in eligible_outcomes
    )

    recovered_revenue = sum(o.recovered_amount for o in outcomes)

    # ── Rate metrics ───────────────────────────────────────────────────────
    recovery_rate = (
        successful_recoveries / eligible_count
        if eligible_count > 0 else 0.0
    )
    revenue_recovery_efficiency = (
        recovered_revenue / eligible_revenue
        if eligible_revenue > 0 else 0.0
    )

    # ── Attempt metrics ────────────────────────────────────────────────────
    total_attempts = sum(o.attempts for o in outcomes)
    average_recovery_attempts = total_attempts / n

    # ── Cost metrics ───────────────────────────────────────────────────────
    total_friction_cost = sum(o.friction_cost for o in outcomes)
    total_action_cost   = sum(o.action_cost for o in outcomes)
    total_risk_cost     = sum(o.risk_cost for o in outcomes)

    # ── Safety metrics ─────────────────────────────────────────────────────
    safety_violation_count = sum(1 for o in outcomes if o.policy_violation)
    safety_violation_rate  = safety_violation_count / n

    # ── Net value metric ───────────────────────────────────────────────────
    net_recovery_value = (
        recovered_revenue
        - total_risk_cost
        - total_friction_cost
        - total_action_cost
    )

    # ── Time metrics ───────────────────────────────────────────────────────
    recovery_times = [o.time_to_recovery_hours for o in successful]
    avg_time_to_recovery = (
        statistics.mean(recovery_times) if recovery_times else 0.0
    )

    return {
        # Count
        "total_transactions":           total_transactions,
        "successful_recoveries":        successful_recoveries,
        "failed_recoveries":            failed_recoveries,
        "blocked_transactions":         blocked_count,
        "stopped_transactions":         stopped_transactions,
        "merchant_review_transactions": merchant_review_count,
        # Revenue
        "revenue_at_risk":              round(revenue_at_risk, 2),
        "eligible_revenue":             round(eligible_revenue, 2),
        "recovered_revenue":            round(recovered_revenue, 2),
        # Rates
        "recovery_rate":                round(recovery_rate, 6),
        "revenue_recovery_efficiency":  round(revenue_recovery_efficiency, 6),
        # Attempts
        "average_recovery_attempts":    round(average_recovery_attempts, 4),
        "total_attempts":               total_attempts,
        # Costs
        "total_friction_cost":          round(total_friction_cost, 4),
        "total_action_cost":            round(total_action_cost, 4),
        "total_risk_cost":              round(total_risk_cost, 4),
        # Safety
        "safety_violation_count":       safety_violation_count,
        "safety_violation_rate":        round(safety_violation_rate, 6),
        # Net value
        "net_recovery_value":           round(net_recovery_value, 4),
        # Time
        "average_time_to_recovery_hours": round(avg_time_to_recovery, 4),
    }


def _empty_metrics() -> Dict[str, float]:
    """Return zero-valued metrics dict for an empty outcomes list."""
    return {
        "total_transactions":             0,
        "successful_recoveries":          0,
        "failed_recoveries":              0,
        "blocked_transactions":           0,
        "stopped_transactions":           0,
        "merchant_review_transactions":   0,
        "revenue_at_risk":                0.0,
        "eligible_revenue":               0.0,
        "recovered_revenue":              0.0,
        "recovery_rate":                  0.0,
        "revenue_recovery_efficiency":    0.0,
        "average_recovery_attempts":      0.0,
        "total_attempts":                 0,
        "total_friction_cost":            0.0,
        "total_action_cost":              0.0,
        "total_risk_cost":                0.0,
        "safety_violation_count":         0,
        "safety_violation_rate":          0.0,
        "net_recovery_value":             0.0,
        "average_time_to_recovery_hours": 0.0,
    }


def compute_aggregate_stats(per_seed_metrics: List[Dict]) -> Dict[str, Dict]:
    """
    Compute mean, std_dev, min, max across multiple seed runs.

    Parameters
    ----------
    per_seed_metrics : list[dict]
        One metrics dict per seed (from compute_metrics).

    Returns
    -------
    dict
        {metric_name: {"mean": ..., "std_dev": ..., "min": ..., "max": ...}}
    """
    if not per_seed_metrics:
        return {}

    keys = list(per_seed_metrics[0].keys())
    agg: Dict[str, Dict] = {}

    for key in keys:
        values = [float(m[key]) for m in per_seed_metrics if key in m]
        if not values:
            continue
        mean_val = statistics.mean(values)
        std_val  = statistics.stdev(values) if len(values) > 1 else 0.0
        agg[key] = {
            "mean":    round(mean_val, 6),
            "std_dev": round(std_val, 6),
            "min":     round(min(values), 6),
            "max":     round(max(values), 6),
        }
    return agg
