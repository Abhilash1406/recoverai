"""
RecoverAI Simulation — Always Retry Strategy

STRATEGY: AlwaysRetryStrategy
-------------------------------
Selects RETRY for every eligible failed transaction.

BEHAVIOUR:
    Every eligible failed transaction attempts a RETRY action.
    Subject to stopping rules enforced by ExperimentRunner:
        - MAX_RETRIES limit applies
        - MAX_AUTOMATIC_ACTIONS limit applies
        - Customer opt-out → STOP (enforced externally)
        - High risk → MERCHANT_REVIEW (enforced externally)
        - Low recovery probability → STOP (enforced externally)

USE CASE:
    This is the simplest possible strategy and serves as a baseline.
    It performs well on TEMPORARY failures (network/gateway) and
    poorly on HARD_FAILURE and RISK_RELATED failures.

    Expected weakness: Will accumulate friction costs and fail frequently
    on CUSTOMER_ACTION and HARD_FAILURE categories.

DOCUMENTED LIMITATION:
    This strategy ignores all contextual information about the failure
    category, customer profile, and risk signals. It is intentionally
    naive for baseline comparison purposes.
"""

from ml.src.simulation.types import (
    SyntheticTransaction,
    RecoveryAction,
    RecoveryContext,
)
from ml.src.simulation.config import SimulationConfig
from ml.src.simulation.strategies.base import RecoveryStrategy


class AlwaysRetryStrategy(RecoveryStrategy):
    """
    Baseline strategy: always select RETRY.

    This is the most naive recovery strategy. It serves as a lower-bound
    reference for more sophisticated approaches.
    """

    def __init__(self, config: SimulationConfig) -> None:
        super().__init__(config)

    @property
    def name(self) -> str:
        return "AlwaysRetry"

    def select_action(
        self,
        transaction: SyntheticTransaction,
        context: RecoveryContext,
    ) -> RecoveryAction:
        """
        Always select RETRY regardless of transaction context.

        The ExperimentRunner will enforce stopping rules after this
        returns. If retry limits are exceeded, the runner will substitute
        STOP.
        """
        return RecoveryAction.RETRY
