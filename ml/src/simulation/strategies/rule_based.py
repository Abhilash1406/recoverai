"""
RecoverAI Simulation — Rule-Based Recovery Strategy

STRATEGY: RuleBasedStrategy
------------------------------
Selects recovery actions based on a deterministic decision tree
using failure category, risk score, and customer opt-out status.

RULES (documented explicitly):

Rule 1 — Customer opted out:
    IF customer_opted_out → STOP
    Rationale: Must respect customer communication preferences.
    No further automated action may be taken.

Rule 2 — High-risk transaction:
    IF risk_score > HIGH_RISK_THRESHOLD → MERCHANT_REVIEW
    Rationale: Suspicious transactions should not be automatically retried.
    Human review is required before any recovery action.

Rule 3 — TEMPORARY failure:
    IF failure_category == TEMPORARY → RETRY
    Rationale: Transient failures (network, gateway, bank) are best
    addressed by retrying. The issue is likely resolved by the time
    the retry occurs.

Rule 4 — CUSTOMER_ACTION failure:
    IF failure_category == CUSTOMER_ACTION → PAYMENT_LINK
    Rationale: The customer abandoned or entered incorrect details.
    A payment link re-engages the customer without annoying them
    with automatic retries that will fail.

Rule 5 — HARD_FAILURE:
    IF failure_category == HARD_FAILURE:
        IF attempt_count == 0 → NOTIFICATION
        ELSE → STOP
    Rationale: Hard failures (expired card, insufficient funds, blocked
    instrument) cannot be retried. A single notification may prompt the
    customer to update their payment details. If already notified,
    further action is unlikely to help.

Rule 6 — RISK_RELATED failure:
    IF failure_category == RISK_RELATED → MERCHANT_REVIEW
    Rationale: Risk-triggered failures should always escalate to human
    review. Automated retry would be inappropriate and may increase
    risk exposure.

Rule 7 — Fallback:
    STOP
    Rationale: If none of the above rules match, stop safely.

DOCUMENTED LIMITATIONS:
    1. Rules do not adapt based on previous attempt outcomes.
    2. Rules do not consider historical recovery success rates.
    3. Rules do not optimize for expected utility.
    4. TEMPORARY failure always retries, even if retry count is high
       (stopping rules in ExperimentRunner handle the limit).
    5. These rules are intentionally simple — a real rule engine would
       incorporate many more signals.
"""

from ml.src.simulation.types import (
    SyntheticTransaction,
    RecoveryAction,
    RecoveryContext,
    FailureCategory,
)
from ml.src.simulation.config import SimulationConfig
from ml.src.simulation.strategies.base import RecoveryStrategy


class RuleBasedStrategy(RecoveryStrategy):
    """
    Deterministic rule-based recovery strategy.

    More sophisticated than the always-X baselines — uses failure category
    and risk context to select contextually appropriate actions.

    See module docstring for the complete documented rule set.
    """

    def __init__(self, config: SimulationConfig) -> None:
        super().__init__(config)

    @property
    def name(self) -> str:
        return "RuleBased"

    def select_action(
        self,
        transaction: SyntheticTransaction,
        context: RecoveryContext,
    ) -> RecoveryAction:
        """
        Apply rule tree to select the next recovery action.

        Rules are evaluated in priority order. The first matching rule wins.

        See module docstring for full rule documentation.
        """
        # Rule 1 — Customer opted out (highest priority safety rule)
        if transaction.customer_opted_out:
            return RecoveryAction.STOP

        # Rule 2 — High-risk transaction
        if context.risk_score > self.config.HIGH_RISK_THRESHOLD:
            return RecoveryAction.MERCHANT_REVIEW

        # Rule 3 — TEMPORARY failure → RETRY
        if transaction.failure_category == FailureCategory.TEMPORARY:
            return RecoveryAction.RETRY

        # Rule 4 — CUSTOMER_ACTION failure → PAYMENT_LINK
        if transaction.failure_category == FailureCategory.CUSTOMER_ACTION:
            return RecoveryAction.PAYMENT_LINK

        # Rule 5 — HARD_FAILURE → NOTIFICATION (first attempt) or STOP
        if transaction.failure_category == FailureCategory.HARD_FAILURE:
            if context.attempt_count == 0:
                return RecoveryAction.NOTIFICATION
            return RecoveryAction.STOP

        # Rule 6 — RISK_RELATED → MERCHANT_REVIEW
        if transaction.failure_category == FailureCategory.RISK_RELATED:
            return RecoveryAction.MERCHANT_REVIEW

        # Rule 7 — Fallback: stop safely
        return RecoveryAction.STOP
