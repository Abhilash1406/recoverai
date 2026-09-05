"""
RecoverAI Simulation — Recovery Strategy Base Class

Defines the contract that all recovery strategies must implement.

All strategies — baseline and future ML-powered — must subclass
RecoveryStrategy and implement select_action().

DESIGN PRINCIPLES:
1. Strategies are stateless — they do not retain state between calls.
2. Strategies select ONE action per call — the state machine loops.
3. Strategies CANNOT access the ground-truth environment.
4. Strategies CANNOT inspect each other's decisions.
5. All strategies receive the same transaction data and context.
"""

from abc import ABC, abstractmethod

from ml.src.simulation.types import (
    SyntheticTransaction,
    RecoveryAction,
    RecoveryContext,
)
from ml.src.simulation.config import SimulationConfig


class RecoveryStrategy(ABC):
    """
    Abstract base class for all recovery strategies.

    A recovery strategy selects the best RecoveryAction for a given
    failed transaction and recovery context. It does NOT execute the
    action — execution is handled by the ExperimentRunner.

    All strategies must be deterministic given the same inputs.
    If a strategy requires randomness (e.g., future ML-based sampling),
    the random state must be fully controlled via the seed mechanism.

    Subclasses
    ----------
    AlwaysRetryStrategy       — Always selects RETRY
    AlwaysPaymentLinkStrategy — Always selects PAYMENT_LINK
    RuleBasedStrategy         — Rule-based decision tree
    RecoverAIStrategy         — ML-powered (contract defined; Phase 3+)
    """

    def __init__(self, config: SimulationConfig) -> None:
        self.config = config

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this strategy. Used in reports."""
        ...

    @abstractmethod
    def select_action(
        self,
        transaction: SyntheticTransaction,
        context: RecoveryContext,
    ) -> RecoveryAction:
        """
        Select the next recovery action for a failed transaction.

        Called once per state machine cycle (ELIGIBLE → ACTION_SELECTED).
        The strategy has already been told the transaction has passed
        eligibility checks.

        Stopping rules are enforced by the ExperimentRunner AFTER this
        method returns — the strategy does not need to check them itself,
        but may use context to guide its decision.

        Parameters
        ----------
        transaction : SyntheticTransaction
            The failed transaction data.
        context : RecoveryContext
            Current recovery process context (attempt count, risk score, etc.).

        Returns
        -------
        RecoveryAction
            The selected recovery action.
        """
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
