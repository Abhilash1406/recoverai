"""
RecoverAI Simulation — Ground-Truth Environment

This module implements the simulated world's true outcome model.

PURPOSE:
    The ground-truth environment determines whether a recovery action
    succeeds or fails for a given transaction. This is the "true" model
    of the synthetic world — the thing that ML models in later phases
    will attempt to learn from data.

    Crucially, this model must be:
    1. Documented — every parameter and formula is explained here
    2. Deterministic given a seed — same inputs + same seed → same outcome
    3. Separated from all strategy/ML code — strategies cannot inspect it
    4. Realistic enough to create meaningful differentiation between strategies

IMPORTANT: This model is a SYNTHETIC SIMULATION. It does NOT represent:
    - Real Razorpay recovery success rates
    - Real payment gateway behaviour
    - Real customer behaviour statistics
    - Any empirically validated model

All parameters are simulation assumptions for fair comparative evaluation.

=============================================================================
GROUND-TRUTH PROBABILITY MODEL
=============================================================================

The true recovery probability is computed as:

    p = clamp(base × profile_factor × history_factor × recovery_factor
              × attempt_penalty × velocity_penalty × device_penalty
              × location_penalty × deviation_penalty × delay_bonus,
              0.0, 1.0)

Step 1 — Base probability matrix
---------------------------------
A documented base recovery probability for each (failure_category, action)
pair. This is the foundational "physics" of the simulated world.

    BASE_PROBABILITY[failure_category][action] = float

Intuition:
    - TEMPORARY failures respond well to RETRY (transient issue)
    - CUSTOMER_ACTION failures respond well to PAYMENT_LINK (needs re-engagement)
    - HARD_FAILURE failures do not respond to RETRY (instrument issue)
    - RISK_RELATED failures should go to MERCHANT_REVIEW (not be auto-retried)
    - STOP/WAIT have near-zero probability (not recovery actions)
    - NOTIFICATION has moderate probability (awareness, not commitment)

Step 2 — Profile factor
-------------------------
Each customer profile has a recovery propensity modifier:

    HIGH_SUCCESS_CUSTOMER:           × 1.20  (reliable, responds well)
    PREVIOUSLY_RECOVERED_CUSTOMER:   × 1.15  (familiar with process)
    REGULAR_CUSTOMER:                × 1.00  (baseline)
    NEW_CUSTOMER:                    × 0.90  (uncertain)
    FAILURE_PRONE_CUSTOMER:          × 0.70  (poor instrument or habits)

Step 3 — History factor
--------------------------
Based on historical_success_rate:

    factor = 0.6 + 0.8 × historical_success_rate

    Range: [0.60, 1.40] — customers with better history recover better

Step 4 — Previous recovery factor
-----------------------------------
Based on previous_recovery_success_rate:

    If previous_recovery_success_rate == 0.0 (no prior recovery history):
        factor = 1.0  (neutral — no evidence either way)
    Else:
        factor = 0.7 + 0.6 × previous_recovery_success_rate

    Range: [0.70, 1.30] — prior recovery success strongly predicts future

Step 5 — Attempt penalty
--------------------------
Repeated attempts reduce the marginal recovery probability:

    factor = max(0.40, 1.0 - 0.25 × attempt_count)

    attempt_count=0: 1.00 (first attempt)
    attempt_count=1: 0.75
    attempt_count=2: 0.50
    attempt_count=3: 0.40 (floor)

Step 6 — Velocity penalty
---------------------------
High transaction velocity can indicate stress or abuse:

    factor = max(0.60, 1.0 - 0.04 × max(0, velocity - 5.0))

    Velocity ≤ 5: no penalty
    Velocity > 5: 4% penalty per unit above 5, floor at 0.60

Step 7 — Device change penalty
--------------------------------
Device fingerprint changes increase uncertainty:

    If device_changed: factor = 0.85
    Else:              factor = 1.00

Step 8 — Location change penalty
----------------------------------
Location/IP region changes increase uncertainty:

    If location_changed: factor = 0.88
    Else:                factor = 1.00

Step 9 — Amount deviation penalty
-----------------------------------
Unusually large amounts relative to customer history reduce probability:

    factor = max(0.60, 1.0 - 0.30 × amount_deviation)

    deviation=0.0: 1.00 (typical amount)
    deviation=0.5: 0.85
    deviation=1.0: 0.70
    deviation>1.3: 0.60 (floor)

Step 10 — Delay bonus (for PAYMENT_LINK / NOTIFICATION)
---------------------------------------------------------
For customer-engagement actions, a short delay before delivery
can improve success (customer may have resolved the issue themselves):

    For PAYMENT_LINK and NOTIFICATION only:
        If time_since_last_attempt_hours > 0.5: factor = 1.05
        Else:                                    factor = 1.00

Final clamp
-----------
    p = clamp(product_of_all_factors, 0.0, 1.0)

Outcome sampling
-----------------
    outcome = rng.random() < p

The outcome is sampled once per (transaction, action) call.
The same transaction with the same action and same RNG state always
produces the same outcome.
"""

import math
import random
from typing import Optional

from ml.src.simulation.types import (
    SyntheticTransaction,
    RecoveryAction,
    FailureCategory,
    CustomerProfileType,
    OutcomeType,
)


# =============================================================================
# Base Probability Matrix
# =============================================================================

# BASE_PROBABILITY[failure_category][action] = base recovery probability
#
# These values represent the "physics" of the simulated world.
# They are documented assumptions — NOT real Razorpay statistics.
#
# Key design rationale:
#   TEMPORARY + RETRY = 0.72   — transient issues resolve on retry
#   CUSTOMER_ACTION + PAYMENT_LINK = 0.68  — re-engagement effective
#   HARD_FAILURE + RETRY = 0.08  — instrument is broken; retry won't help
#   RISK_RELATED + MERCHANT_REVIEW = 0.55  — human review can often resolve
#   Any + STOP = 0.0  — stopping never recovers
#   Any + WAIT = 0.05 — waiting alone rarely recovers (small organic rate)

BASE_PROBABILITY: dict[FailureCategory, dict[RecoveryAction, float]] = {
    FailureCategory.TEMPORARY: {
        RecoveryAction.WAIT:            0.10,
        RecoveryAction.RETRY:           0.72,
        RecoveryAction.PAYMENT_LINK:    0.45,
        RecoveryAction.NOTIFICATION:    0.30,
        RecoveryAction.MERCHANT_REVIEW: 0.35,
        RecoveryAction.STOP:            0.00,
    },
    FailureCategory.CUSTOMER_ACTION: {
        RecoveryAction.WAIT:            0.05,
        RecoveryAction.RETRY:           0.15,   # customer must act; auto-retry low value
        RecoveryAction.PAYMENT_LINK:    0.68,
        RecoveryAction.NOTIFICATION:    0.38,
        RecoveryAction.MERCHANT_REVIEW: 0.28,
        RecoveryAction.STOP:            0.00,
    },
    FailureCategory.HARD_FAILURE: {
        RecoveryAction.WAIT:            0.02,
        RecoveryAction.RETRY:           0.08,   # instrument is broken; minimal chance
        RecoveryAction.PAYMENT_LINK:    0.30,   # customer may use different instrument
        RecoveryAction.NOTIFICATION:    0.20,
        RecoveryAction.MERCHANT_REVIEW: 0.25,
        RecoveryAction.STOP:            0.00,
    },
    FailureCategory.RISK_RELATED: {
        RecoveryAction.WAIT:            0.05,
        RecoveryAction.RETRY:           0.05,   # risky to auto-retry
        RecoveryAction.PAYMENT_LINK:    0.15,
        RecoveryAction.NOTIFICATION:    0.10,
        RecoveryAction.MERCHANT_REVIEW: 0.55,   # human review is the right action
        RecoveryAction.STOP:            0.00,
    },
}

# Profile recovery propensity multipliers
# Documented assumptions — see module docstring for rationale
_PROFILE_FACTOR: dict[CustomerProfileType, float] = {
    CustomerProfileType.HIGH_SUCCESS_CUSTOMER:          1.20,
    CustomerProfileType.PREVIOUSLY_RECOVERED_CUSTOMER:  1.15,
    CustomerProfileType.REGULAR_CUSTOMER:               1.00,
    CustomerProfileType.NEW_CUSTOMER:                   0.90,
    CustomerProfileType.FAILURE_PRONE_CUSTOMER:         0.70,
}


class GroundTruthEnvironment:
    """
    The simulated world's probabilistic recovery outcome model.

    This class is the "oracle" — it knows the true recovery probability
    for any (transaction, action) pair. ML models in later phases will
    attempt to approximate this function from observed data.

    SEPARATION PRINCIPLE:
        This class must NEVER be imported or referenced from within any
        strategy or ML model implementation. It is the ground truth,
        not a tool for strategies to exploit.

    Parameters
    ----------
    seed : int
        Random seed for outcome sampling. Derived deterministically
        from the master experiment seed.

    Usage
    -----
    >>> env = GroundTruthEnvironment(seed=42)
    >>> p, outcome = env.sample_outcome(transaction, RecoveryAction.RETRY)
    >>> print(f"p={p:.3f}, outcome={outcome}")
    """

    def __init__(self, seed: int) -> None:
        self.seed = seed
        self._rng = random.Random(seed)

    def compute_recovery_probability(
        self,
        transaction: SyntheticTransaction,
        action: RecoveryAction,
        attempt_count: int = 0,
        time_since_last_hours: float = 0.0,
    ) -> float:
        """
        Compute the true recovery probability for a (transaction, action) pair.

        This is the ground-truth probability that the payment will be
        successfully recovered if this action is taken.

        See module docstring for the complete formula documentation.

        Parameters
        ----------
        transaction : SyntheticTransaction
            The failed transaction.
        action : RecoveryAction
            The proposed recovery action.
        attempt_count : int
            Number of recovery actions already taken (0-indexed).
        time_since_last_hours : float
            Hours since the last recovery attempt (0.0 for first attempt).

        Returns
        -------
        float
            True recovery probability in [0.0, 1.0].
        """
        # STOP always has zero probability — it is not a recovery action
        if action == RecoveryAction.STOP:
            return 0.0

        # --- Step 1: Base probability ---
        base = BASE_PROBABILITY[transaction.failure_category][action]

        # --- Step 2: Profile factor ---
        profile_factor = _PROFILE_FACTOR.get(transaction.profile_type, 1.0)

        # --- Step 3: History factor ---
        # factor = 0.6 + 0.8 * historical_success_rate → [0.60, 1.40]
        history_factor = 0.6 + 0.8 * transaction.historical_success_rate

        # --- Step 4: Previous recovery factor ---
        if transaction.previous_recovery_success_rate == 0.0:
            recovery_factor = 1.0
        else:
            recovery_factor = 0.7 + 0.6 * transaction.previous_recovery_success_rate

        # --- Step 5: Attempt penalty ---
        # max(0.40, 1.0 - 0.25 * attempt_count)
        attempt_penalty = max(0.40, 1.0 - 0.25 * attempt_count)

        # --- Step 6: Velocity penalty ---
        # max(0.60, 1.0 - 0.04 * max(0, velocity - 5.0))
        velocity_excess = max(0.0, transaction.transaction_velocity - 5.0)
        velocity_penalty = max(0.60, 1.0 - 0.04 * velocity_excess)

        # --- Step 7: Device change penalty ---
        device_penalty = 0.85 if transaction.device_changed else 1.00

        # --- Step 8: Location change penalty ---
        location_penalty = 0.88 if transaction.location_changed else 1.00

        # --- Step 9: Amount deviation penalty ---
        # max(0.60, 1.0 - 0.30 * amount_deviation)
        deviation_penalty = max(0.60, 1.0 - 0.30 * transaction.amount_deviation)

        # --- Step 10: Delay bonus (PAYMENT_LINK and NOTIFICATION only) ---
        if action in (RecoveryAction.PAYMENT_LINK, RecoveryAction.NOTIFICATION):
            delay_bonus = 1.05 if time_since_last_hours > 0.5 else 1.00
        else:
            delay_bonus = 1.00

        # --- Compute product ---
        p = (
            base
            * profile_factor
            * history_factor
            * recovery_factor
            * attempt_penalty
            * velocity_penalty
            * device_penalty
            * location_penalty
            * deviation_penalty
            * delay_bonus
        )

        # --- Clamp to [0, 1] ---
        return max(0.0, min(1.0, p))

    def sample_outcome(
        self,
        transaction: SyntheticTransaction,
        action: RecoveryAction,
        attempt_count: int = 0,
        time_since_last_hours: float = 0.0,
    ) -> tuple[float, OutcomeType]:
        """
        Sample a recovery outcome for a (transaction, action) pair.

        Computes the true probability then draws a Bernoulli sample.

        Parameters
        ----------
        transaction : SyntheticTransaction
            The failed transaction.
        action : RecoveryAction
            The recovery action being taken.
        attempt_count : int
            Number of recovery actions already taken.
        time_since_last_hours : float
            Hours since last attempt.

        Returns
        -------
        tuple[float, OutcomeType]
            (true_recovery_probability, outcome)
        """
        if action == RecoveryAction.STOP:
            return 0.0, OutcomeType.STOPPED

        if action == RecoveryAction.MERCHANT_REVIEW:
            p = self.compute_recovery_probability(
                transaction, action, attempt_count, time_since_last_hours
            )
            # Merchant review → outcome is MERCHANT_REVIEW (terminal, not success/fail)
            return p, OutcomeType.MERCHANT_REVIEW

        p = self.compute_recovery_probability(
            transaction, action, attempt_count, time_since_last_hours
        )

        outcome = OutcomeType.SUCCESS if self._rng.random() < p else OutcomeType.FAILED
        return p, outcome

    def compute_risk_score(self, transaction: SyntheticTransaction) -> float:
        """
        Compute a synthetic risk score for a transaction (0.0–1.0).

        This is a simple heuristic risk score used by the state machine
        to determine whether to escalate. In Phase 3+, this will be
        replaced by a trained ML risk model.

        Formula:
            risk = 0.0
            + 0.30 if RISK_RELATED failure
            + 0.15 if device_changed
            + 0.15 if location_changed
            + 0.20 × amount_deviation (capped at 0.20)
            + 0.10 if transaction_velocity > 10
            + 0.10 × (1 - historical_success_rate)

        All components are simulation assumptions.
        """
        risk = 0.0

        if transaction.failure_category.value == "RISK_RELATED":
            risk += 0.30

        if transaction.device_changed:
            risk += 0.15

        if transaction.location_changed:
            risk += 0.15

        risk += min(0.20, 0.20 * transaction.amount_deviation)

        if transaction.transaction_velocity > 10.0:
            risk += 0.10

        risk += 0.10 * (1.0 - transaction.historical_success_rate)

        return max(0.0, min(1.0, risk))

    def simulate_time_to_action_hours(self, action: RecoveryAction) -> float:
        """
        Simulate the time elapsed by taking an action.

        These are synthetic time estimates for simulation purposes.
        They represent the delay before the outcome can be assessed.

        ASSUMPTION: These times are purely for simulation; they do not
        represent real Razorpay processing times.
        """
        time_map = {
            RecoveryAction.WAIT:            self._rng.uniform(1.0, 4.0),
            RecoveryAction.RETRY:           self._rng.uniform(0.1, 0.5),
            RecoveryAction.PAYMENT_LINK:    self._rng.uniform(0.5, 6.0),
            RecoveryAction.NOTIFICATION:    self._rng.uniform(0.5, 3.0),
            RecoveryAction.MERCHANT_REVIEW: self._rng.uniform(2.0, 24.0),
            RecoveryAction.STOP:            0.0,
        }
        return time_map.get(action, 0.0)
