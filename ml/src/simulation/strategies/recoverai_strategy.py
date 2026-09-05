"""
RecoverAI Simulation — RecoverAI Strategy (Phase 3 ML-Powered)

STRATEGY: RecoverAIStrategy
-----------------------------
ML-powered, risk-aware recovery decision strategy.

Decision Pipeline:
1. Feature Transformation (FeatureTransformer)
2. Risk Score & RiskLevel Estimation (RiskPredictionModel)
3. Action-Specific Calibrated Recovery Probability Estimation (RecoveryPredictionModel)
4. Expected Utility (EU) Calculation (ExpectedUtilityEngine)
5. Safety / Policy Gate Constraints & Action Ranking (ActionRanker)
6. Action Selection & Transparent Decision Explanation Output

IMPORTANT:
- NO Gemini, NO Razorpay APIs, NO external calls.
- Purely deterministic decision intelligence powered by trained ML models.
- Does NOT access GroundTruthEnvironment directly.
"""

from typing import Optional, Dict, Any, List

from ml.src.simulation.types import (
    SyntheticTransaction,
    RecoveryAction,
    RecoveryContext,
    RiskLevel,
)
from ml.src.simulation.config import SimulationConfig
from ml.src.simulation.strategies.base import RecoveryStrategy

from ml.src.risk.model import RiskPredictionModel
from ml.src.recovery.model import RecoveryPredictionModel
from ml.src.decision.engine import ActionRanker, ScoredActionDecision


PHASE_LABEL = "PHASE_3_ML_DECISION_ENGINE"
IMPLEMENTATION_NOTE = (
    "RecoverAI ML Strategy is fully active in Phase 3. "
    "Uses risk estimation, calibrated recovery probability prediction, "
    "Expected Utility optimization, and deterministic policy safety gates."
)


class RecoverAIStrategy(RecoveryStrategy):
    """
    RecoverAI Intelligent Recovery Strategy (Phase 3 Complete).

    Integrates RiskPredictionModel, RecoveryPredictionModel,
    ExpectedUtilityEngine, and ActionRanker.
    """

    def __init__(
        self,
        config: SimulationConfig,
        risk_model: Optional[RiskPredictionModel] = None,
        recovery_model: Optional[RecoveryPredictionModel] = None,
    ) -> None:
        super().__init__(config)
        self.risk_model = risk_model
        self.recovery_model = recovery_model
        self.action_ranker = ActionRanker(config)

        self.last_decision: Optional[ScoredActionDecision] = None
        self.decision_history: List[ScoredActionDecision] = []

    @property
    def name(self) -> str:
        return "RecoverAI"

    @property
    def phase_label(self) -> str:
        return PHASE_LABEL

    @property
    def implementation_note(self) -> str:
        return IMPLEMENTATION_NOTE

    def is_placeholder(self) -> bool:
        """Returns False as Phase 3 ML strategy is active."""
        return self.risk_model is None or self.recovery_model is None

    def select_action(
        self,
        transaction: SyntheticTransaction,
        context: RecoveryContext,
    ) -> RecoveryAction:
        """
        Select optimal recovery action for a transaction using ML + EU Optimization.

        Fallback: If models are not passed, safe fallback to STOP.
        """
        if self.is_placeholder():
            # Fallback if uninitialized
            return RecoveryAction.STOP

        # Initialize cache if needed
        if not hasattr(self, "_cache"):
            self._cache = {}

        tx_id = transaction.transaction_id
        if tx_id in self._cache:
            risk_prob, risk_level, recovery_probs = self._cache[tx_id]
        else:
            # 1. Predict Risk Probability & Categorise Risk Level
            risk_prob = float(self.risk_model.predict_risk_score(transaction))
            risk_level = self.risk_model.categorize_risk_level(risk_prob)

            # 2. Predict Action-Specific Recovery Probabilities
            candidate_actions = [
                RecoveryAction.RETRY,
                RecoveryAction.PAYMENT_LINK,
                RecoveryAction.NOTIFICATION,
                RecoveryAction.MERCHANT_REVIEW,
                RecoveryAction.WAIT,
                RecoveryAction.STOP,
            ]
            recovery_probs = self.recovery_model.predict_all_action_probabilities(
                transaction, candidate_actions
            )
            self._cache[tx_id] = (risk_prob, risk_level, recovery_probs)

        # 3. Rank Actions via Expected Utility Engine & Policy Gate
        decision = self.action_ranker.rank_and_select_action(
            transaction=transaction,
            context=context,
            risk_prob=risk_prob,
            risk_level=risk_level,
            recovery_probs=recovery_probs,
        )

        self.last_decision = decision
        self.decision_history.append(decision)

        return decision.selected_action
