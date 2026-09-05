"""
RecoverAI Simulation — Always Payment Link Strategy

STRATEGY: AlwaysPaymentLinkStrategy
--------------------------------------
Selects PAYMENT_LINK for every eligible failed transaction.

BEHAVIOUR:
    Every eligible failed transaction is sent a payment link for customer
    re-engagement. Subject to stopping rules enforced by ExperimentRunner:
        - MAX_AUTOMATIC_ACTIONS limit applies
        - Customer opt-out → STOP (enforced externally)
        - High risk → MERCHANT_REVIEW (enforced externally)
        - Low recovery probability → STOP (enforced externally)

    Note: PAYMENT_LINK is not subject to MAX_RETRIES (which tracks RETRY only).

USE CASE:
    This strategy performs well on CUSTOMER_ACTION failures (abandoned,
    authentication failure) where customer re-engagement is needed.
    It accumulates higher friction scores than RETRY (friction=3 vs 1).

DOCUMENTED LIMITATION:
    This strategy ignores failure category — it will send a payment link
    even for TEMPORARY (network) failures where a RETRY would be more
    appropriate. It is intentionally naive for baseline comparison purposes.
"""

from ml.src.simulation.types import (
    SyntheticTransaction,
    RecoveryAction,
    RecoveryContext,
)
from ml.src.simulation.config import SimulationConfig
from ml.src.simulation.strategies.base import RecoveryStrategy


class AlwaysPaymentLinkStrategy(RecoveryStrategy):
    """
    Baseline strategy: always select PAYMENT_LINK.

    This strategy serves as a reference for customer-re-engagement
    approaches. It pairs naturally with the ground-truth model where
    CUSTOMER_ACTION failures have high PAYMENT_LINK base probability.
    """

    def __init__(self, config: SimulationConfig) -> None:
        super().__init__(config)

    @property
    def name(self) -> str:
        return "AlwaysPaymentLink"

    def select_action(
        self,
        transaction: SyntheticTransaction,
        context: RecoveryContext,
    ) -> RecoveryAction:
        """
        Always select PAYMENT_LINK regardless of transaction context.

        The ExperimentRunner will enforce stopping rules after this returns.
        """
        return RecoveryAction.PAYMENT_LINK
