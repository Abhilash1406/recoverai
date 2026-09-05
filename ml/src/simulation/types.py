"""
RecoverAI Simulation — Domain Types

Strongly-typed Python dataclasses and enums for the simulation domain.

These types mirror the TypeScript types in packages/shared-types/src/index.ts
but are adapted for the Python simulation environment.

IMPORTANT: These types are for simulation ONLY. They do NOT represent
Razorpay production data models or real transaction records.

No PII is stored anywhere in these types. All identifiers are pseudonymous
UUIDs. No names, phone numbers, email addresses, or payment credentials.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# =============================================================================
# Failure Taxonomy
# =============================================================================

class FailureCategory(Enum):
    """
    Root-cause category of a simulated payment failure.

    Each category has different recovery characteristics and appropriate
    recovery actions. See docs/ml/simulation.md for full taxonomy rationale.

    TEMPORARY:
        Failures caused by transient infrastructure issues. High retry success
        rate when retried after a delay.
    CUSTOMER_ACTION:
        Failures caused by customer behaviour or input. Require customer
        re-engagement (e.g., payment link) rather than automatic retry.
    HARD_FAILURE:
        Failures caused by fundamental issues with the payment instrument.
        Cannot be retried; require instrument change or escalation.
    RISK_RELATED:
        Failures triggered by fraud/risk signals. Require human review.
        Automatic retry is inappropriate and may increase risk exposure.
    """
    TEMPORARY = "TEMPORARY"
    CUSTOMER_ACTION = "CUSTOMER_ACTION"
    HARD_FAILURE = "HARD_FAILURE"
    RISK_RELATED = "RISK_RELATED"


class FailureCode(Enum):
    """
    Specific failure code within a category.

    TEMPORARY codes:
        NETWORK_TIMEOUT     — request timed out at network layer
        GATEWAY_TIMEOUT     — payment gateway did not respond
        BANK_UNAVAILABLE    — issuing bank temporarily unreachable

    CUSTOMER_ACTION codes:
        AUTHENTICATION_FAILURE — 3DS/OTP authentication failed or timed out
        PAYMENT_ABANDONED      — customer closed the payment page
        INVALID_DETAILS        — incorrect card details entered

    HARD_FAILURE codes:
        EXPIRED_INSTRUMENT          — card/UPI/wallet has expired
        INSUFFICIENT_FUNDS          — insufficient balance in account
        INVALID_PAYMENT_INSTRUMENT  — instrument blocked or closed

    RISK_RELATED codes:
        SUSPICIOUS_PATTERN — transaction flagged by risk engine
    """
    # TEMPORARY
    NETWORK_TIMEOUT = "network_timeout"
    GATEWAY_TIMEOUT = "gateway_timeout"
    BANK_UNAVAILABLE = "bank_unavailable"

    # CUSTOMER_ACTION
    AUTHENTICATION_FAILURE = "authentication_failure"
    PAYMENT_ABANDONED = "payment_abandoned"
    INVALID_DETAILS = "invalid_details"

    # HARD_FAILURE
    EXPIRED_INSTRUMENT = "expired_instrument"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    INVALID_PAYMENT_INSTRUMENT = "invalid_payment_instrument"

    # RISK_RELATED
    SUSPICIOUS_PATTERN = "suspicious_pattern"


# Mapping from FailureCode → FailureCategory (strongly typed, no magic strings)
FAILURE_CODE_TO_CATEGORY: dict[FailureCode, FailureCategory] = {
    FailureCode.NETWORK_TIMEOUT:           FailureCategory.TEMPORARY,
    FailureCode.GATEWAY_TIMEOUT:           FailureCategory.TEMPORARY,
    FailureCode.BANK_UNAVAILABLE:          FailureCategory.TEMPORARY,
    FailureCode.AUTHENTICATION_FAILURE:    FailureCategory.CUSTOMER_ACTION,
    FailureCode.PAYMENT_ABANDONED:         FailureCategory.CUSTOMER_ACTION,
    FailureCode.INVALID_DETAILS:           FailureCategory.CUSTOMER_ACTION,
    FailureCode.EXPIRED_INSTRUMENT:        FailureCategory.HARD_FAILURE,
    FailureCode.INSUFFICIENT_FUNDS:        FailureCategory.HARD_FAILURE,
    FailureCode.INVALID_PAYMENT_INSTRUMENT: FailureCategory.HARD_FAILURE,
    FailureCode.SUSPICIOUS_PATTERN:        FailureCategory.RISK_RELATED,
}


# =============================================================================
# Risk Types
# =============================================================================

class RiskLevel(Enum):
    """
    Categorical risk level assigned to a transaction.
    Mirrors packages/shared-types/src/index.ts RiskLevel enum.
    """
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# =============================================================================
# Customer Profiles
# =============================================================================

class CustomerProfileType(Enum):
    """
    Behavioural profile assigned to each synthetic customer.

    Profiles influence failure rates, recovery rates, and transaction patterns.
    See generator/profiles.py for the full quantitative specification.

    NEW_CUSTOMER:
        Low historical data. Unknown reliability. Moderate failure rate.
    REGULAR_CUSTOMER:
        Established history. Moderate success rate. Standard behaviour.
    HIGH_SUCCESS_CUSTOMER:
        Consistently successful transactions. Low failure rate.
    FAILURE_PRONE_CUSTOMER:
        High historical failure rate. Poor instrument quality or behaviour.
    PREVIOUSLY_RECOVERED_CUSTOMER:
        Has been successfully recovered before. Higher recovery success rate.
    """
    NEW_CUSTOMER = "NEW_CUSTOMER"
    REGULAR_CUSTOMER = "REGULAR_CUSTOMER"
    HIGH_SUCCESS_CUSTOMER = "HIGH_SUCCESS_CUSTOMER"
    FAILURE_PRONE_CUSTOMER = "FAILURE_PRONE_CUSTOMER"
    PREVIOUSLY_RECOVERED_CUSTOMER = "PREVIOUSLY_RECOVERED_CUSTOMER"


# =============================================================================
# Recovery Actions
# =============================================================================

class RecoveryAction(Enum):
    """
    Actions available to a recovery strategy.

    Mirrors packages/shared-types/src/index.ts RecoveryAction enum.

    WAIT:
        Take no immediate action. Used when delay may improve outcome.
    RETRY:
        Automatically retry the payment with the same instrument.
        Appropriate only for TEMPORARY failures.
    PAYMENT_LINK:
        Send the customer a new payment link to complete payment.
        Requires customer interaction.
    NOTIFICATION:
        Send a notification to the customer (e.g., reminder).
        Lower friction than PAYMENT_LINK.
    MERCHANT_REVIEW:
        Escalate to merchant for human review.
        Required for RISK_RELATED failures.
    STOP:
        Cease all recovery attempts for this transaction.
        Final action — cannot transition from STOP to any other action.
    """
    WAIT = "WAIT"
    RETRY = "RETRY"
    PAYMENT_LINK = "PAYMENT_LINK"
    NOTIFICATION = "NOTIFICATION"
    MERCHANT_REVIEW = "MERCHANT_REVIEW"
    STOP = "STOP"


# =============================================================================
# Recovery State Machine States
# =============================================================================

class RecoveryState(Enum):
    """
    States in the bounded recovery state machine.

    State transitions are defined in runner/experiment_runner.py.
    No transition may create an infinite loop — the state machine
    is bounded by stopping rules defined in SimulationConfig.

    Valid transitions:
        FAILED          → ANALYZING
        ANALYZING       → ELIGIBLE | STOPPED
        ELIGIBLE        → ACTION_SELECTED | STOPPED
        ACTION_SELECTED → EXECUTING
        EXECUTING       → VERIFYING
        VERIFYING       → RECOVERED | RETRY_PENDING | STOPPED | MERCHANT_REVIEW
        RETRY_PENDING   → ACTION_SELECTED (if not exceeded limits) | STOPPED
        RECOVERED       → (terminal)
        STOPPED         → (terminal)
        MERCHANT_REVIEW → (terminal)
    """
    FAILED = "FAILED"
    ANALYZING = "ANALYZING"
    ELIGIBLE = "ELIGIBLE"
    ACTION_SELECTED = "ACTION_SELECTED"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    RECOVERED = "RECOVERED"
    RETRY_PENDING = "RETRY_PENDING"
    STOPPED = "STOPPED"
    MERCHANT_REVIEW = "MERCHANT_REVIEW"


# Terminal states — no further transitions allowed
TERMINAL_STATES: frozenset[RecoveryState] = frozenset({
    RecoveryState.RECOVERED,
    RecoveryState.STOPPED,
    RecoveryState.MERCHANT_REVIEW,
})


# =============================================================================
# Outcome Types
# =============================================================================

class OutcomeType(Enum):
    """
    Final outcome of a recovery attempt for a transaction.

    SUCCESS:
        Payment was successfully recovered.
    FAILED:
        All recovery attempts exhausted; payment could not be recovered.
    BLOCKED:
        Recovery was blocked by stopping rules before any action.
    STOPPED:
        Recovery was stopped mid-process (opted out, safety rule, etc.).
    MERCHANT_REVIEW:
        Transaction escalated to merchant for human review.
    """
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    STOPPED = "STOPPED"
    MERCHANT_REVIEW = "MERCHANT_REVIEW"


# =============================================================================
# Payment Methods
# =============================================================================

class PaymentMethod(Enum):
    """
    Simulated payment method types.

    Purely for simulation diversity. No real payment credentials are generated.
    """
    CARD = "card"
    UPI = "upi"
    NETBANKING = "netbanking"
    WALLET = "wallet"
    EMI = "emi"


# =============================================================================
# Core Data Models
# =============================================================================

@dataclass
class SyntheticTransaction:
    """
    A single synthetic failed transaction record.

    IMPORTANT:
    - Contains NO real PII (no names, no phone numbers, no email, no address)
    - All identifiers are pseudonymous UUIDs
    - No real payment credentials
    - All amounts are synthetic INR values

    Fields
    ------
    transaction_id : str
        Pseudonymous UUID. Not traceable to any real transaction.
    customer_id : str
        Pseudonymous UUID. Not traceable to any real customer.
    amount : float
        Transaction amount in INR. Sampled from profile-based distribution.
    currency : str
        Always "INR" in this simulation.
    payment_method : PaymentMethod
        Sampled from profile-based payment method distribution.
    failure_category : FailureCategory
        Derived from failure_code via FAILURE_CODE_TO_CATEGORY mapping.
    failure_code : FailureCode
        Specific failure code sampled from profile-weighted distribution.
    transaction_hour : int
        Hour of day (0–23) at which failure occurred.
    customer_account_age_days : int
        Synthetic age of customer account in days.
    previous_transaction_count : int
        Total number of previous transactions for this customer profile.
    previous_successful_transactions : int
        Count of previously successful transactions.
    previous_failed_transactions : int
        Count of previously failed transactions.
    historical_success_rate : float
        previous_successful / previous_transaction_count (or 0 if no history).
    previous_recovery_success_rate : float
        Rate of successful recoveries from prior failures. 0.0 if no prior failures.
    attempt_count : int
        Number of recovery attempts already made for this transaction (0 on first entry).
    time_since_last_attempt_hours : float
        Hours since the last recovery attempt. 0.0 on first attempt.
    transaction_velocity : float
        Number of transactions in the last 24 hours for this customer.
    device_changed : bool
        Whether the device fingerprint changed since the last transaction.
    location_changed : bool
        Whether the location/IP region changed since the last transaction.
    amount_deviation : float
        Ratio: |amount - customer_avg_amount| / customer_avg_amount.
        High deviation indicates unusual spend.
    customer_opted_out : bool
        Whether this customer has opted out of recovery communications.
    profile_type : CustomerProfileType
        The behavioural profile used to generate this transaction.
    """
    transaction_id: str
    customer_id: str
    amount: float
    currency: str
    payment_method: PaymentMethod
    failure_category: FailureCategory
    failure_code: FailureCode
    transaction_hour: int
    customer_account_age_days: int
    previous_transaction_count: int
    previous_successful_transactions: int
    previous_failed_transactions: int
    historical_success_rate: float
    previous_recovery_success_rate: float
    attempt_count: int
    time_since_last_attempt_hours: float
    transaction_velocity: float
    device_changed: bool
    location_changed: bool
    amount_deviation: float
    customer_opted_out: bool
    profile_type: CustomerProfileType

    def __post_init__(self) -> None:
        """Validate key invariants after construction."""
        assert 0 <= self.transaction_hour <= 23, "transaction_hour must be 0-23"
        assert self.amount > 0, "amount must be positive"
        assert 0.0 <= self.historical_success_rate <= 1.0, (
            "historical_success_rate must be in [0, 1]"
        )
        assert 0.0 <= self.previous_recovery_success_rate <= 1.0, (
            "previous_recovery_success_rate must be in [0, 1]"
        )
        assert self.attempt_count >= 0, "attempt_count must be non-negative"
        assert self.amount_deviation >= 0.0, "amount_deviation must be non-negative"
        assert self.previous_transaction_count >= 0
        assert self.previous_successful_transactions >= 0
        assert self.previous_failed_transactions >= 0
        assert (
            self.previous_successful_transactions + self.previous_failed_transactions
            <= self.previous_transaction_count
        ), "successful + failed cannot exceed total"


@dataclass
class RecoveryContext:
    """
    Context passed to a recovery strategy alongside the transaction.

    Contains the current state of the recovery process for this transaction,
    allowing strategies to make informed decisions.

    Fields
    ------
    current_state : RecoveryState
        The current state machine state.
    attempt_count : int
        Number of recovery actions already taken.
    retry_count : int
        Number of RETRY actions already taken.
    risk_score : float
        Computed risk score for this transaction (0.0–1.0).
    time_since_first_failure_hours : float
        Total elapsed time since the initial failure.
    """
    current_state: RecoveryState
    attempt_count: int
    retry_count: int
    risk_score: float
    time_since_first_failure_hours: float


@dataclass
class SimulationOutcome:
    """
    Complete record of a single transaction's simulation run.

    One outcome is produced per (transaction, strategy) pair.

    Fields
    ------
    transaction_id : str
        Identifier of the simulated transaction.
    strategy_name : str
        Name of the recovery strategy used.
    selected_actions : list[RecoveryAction]
        Ordered list of all actions selected during recovery.
    true_recovery_probability : float
        The final ground-truth probability used to determine the outcome.
    outcome : OutcomeType
        Final outcome for this transaction.
    recovered_amount : float
        Amount recovered in INR. Equal to transaction.amount on SUCCESS, else 0.0.
    attempts : int
        Total number of recovery actions taken.
    retry_count : int
        Number of RETRY actions specifically.
    time_to_recovery_hours : float
        Simulated elapsed time to reach terminal state.
    friction_cost : float
        Total friction score accumulated across all actions.
    action_cost : float
        Total operational cost (ACU) accumulated across all actions.
    risk_cost : float
        Risk cost computed for this transaction (see SimulationConfig.risk_cost).
    policy_violation : bool
        Whether any stopping rule was violated (should be False in correct sim).
    state_history : list[RecoveryState]
        Ordered list of all states visited.
    timestamp : str
        ISO 8601 timestamp of when this outcome was recorded.
    """
    transaction_id: str
    strategy_name: str
    selected_actions: list
    true_recovery_probability: float
    outcome: OutcomeType
    recovered_amount: float
    attempts: int
    retry_count: int
    time_to_recovery_hours: float
    friction_cost: float
    action_cost: float
    risk_cost: float
    policy_violation: bool
    state_history: list
    timestamp: str

    def to_dict(self) -> dict:
        """Convert to JSON-serialisable dict."""
        return {
            "transaction_id": self.transaction_id,
            "strategy_name": self.strategy_name,
            "selected_actions": [a.value if hasattr(a, "value") else str(a)
                                  for a in self.selected_actions],
            "true_recovery_probability": round(self.true_recovery_probability, 6),
            "outcome": self.outcome.value,
            "recovered_amount": round(self.recovered_amount, 2),
            "attempts": self.attempts,
            "retry_count": self.retry_count,
            "time_to_recovery_hours": round(self.time_to_recovery_hours, 2),
            "friction_cost": round(self.friction_cost, 4),
            "action_cost": round(self.action_cost, 4),
            "risk_cost": round(self.risk_cost, 4),
            "policy_violation": self.policy_violation,
            "state_history": [s.value if hasattr(s, "value") else str(s)
                               for s in self.state_history],
            "timestamp": self.timestamp,
        }


@dataclass
class StrategyResult:
    """
    Aggregated results for one strategy across the full transaction dataset.

    Fields
    ------
    strategy_name : str
        Name of the strategy.
    outcomes : list[SimulationOutcome]
        All individual transaction outcomes.
    metrics : dict
        Calculated aggregate metrics (see scoring/metrics.py for formulas).
    dataset_hash : str
        SHA256-based hash of the transaction dataset used. Used to verify
        that all strategies ran on the same dataset.
    """
    strategy_name: str
    outcomes: list
    metrics: dict
    dataset_hash: str

    def to_dict(self) -> dict:
        """Convert to JSON-serialisable dict."""
        return {
            "strategy_name": self.strategy_name,
            "dataset_hash": self.dataset_hash,
            "metrics": self.metrics,
            "outcome_count": len(self.outcomes),
            # Individual outcomes are stored separately to avoid huge payloads
        }


@dataclass
class ExperimentResult:
    """
    Complete experiment result for one (seed, dataset_size) run.

    Contains results for all strategies, enabling direct comparison.

    Fields
    ------
    experiment_id : str
        Unique identifier for this experiment run.
    seed : int
        Random seed used.
    dataset_size : int
        Number of transactions in the dataset.
    config_snapshot : dict
        Snapshot of SimulationConfig used.
    strategy_results : list[StrategyResult]
        One result per strategy.
    dataset_hash : str
        Hash of the shared transaction dataset.
    generated_at : str
        ISO 8601 timestamp.
    """
    experiment_id: str
    seed: int
    dataset_size: int
    config_snapshot: dict
    strategy_results: list
    dataset_hash: str
    generated_at: str

    def to_dict(self) -> dict:
        """Convert to JSON-serialisable dict."""
        return {
            "experiment_id": self.experiment_id,
            "seed": self.seed,
            "dataset_size": self.dataset_size,
            "dataset_hash": self.dataset_hash,
            "config_snapshot": self.config_snapshot,
            "strategy_results": [r.to_dict() for r in self.strategy_results],
            "generated_at": self.generated_at,
        }


@dataclass
class MultiSeedResult:
    """
    Aggregated results across multiple seeds for the same strategies.

    Provides mean, std_dev, min, max for major metrics across seeds.

    Fields
    ------
    strategy_name : str
        Name of the strategy.
    seeds : list[int]
        Seeds used.
    dataset_size : int
        Dataset size used per seed.
    per_seed_metrics : list[dict]
        Metrics dict for each seed (aligned with seeds list).
    aggregate_stats : dict
        {metric_name: {mean, std_dev, min, max}} computed across seeds.
    """
    strategy_name: str
    seeds: list
    dataset_size: int
    per_seed_metrics: list
    aggregate_stats: dict

    def to_dict(self) -> dict:
        return {
            "strategy_name": self.strategy_name,
            "seeds": self.seeds,
            "dataset_size": self.dataset_size,
            "aggregate_stats": self.aggregate_stats,
        }
