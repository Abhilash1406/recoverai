"""
RecoverAI ML — Expected Utility Engine & Action Ranker

Combines ML predictions (Risk + Recovery Probability) with Expected Utility
optimization and deterministic policy safety gates.

Expected Utility Formula:
    EU(action) = P(recovery | txn, action) * amount - riskCost - frictionCost - actionCost

Policy Safety Constraints:
- Customer opted out -> STOP
- Risk probability >= HIGH_RISK_THRESHOLD or RiskLevel == CRITICAL -> MERCHANT_REVIEW
- P(recovery | action) < MIN_RECOVERY_PROBABILITY -> reject action
- attempt_count >= MAX_AUTOMATIC_ACTIONS -> STOP / MERCHANT_REVIEW
- retry_count >= MAX_RETRIES for RETRY -> reject RETRY
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any

from ml.src.simulation.types import (
    SyntheticTransaction,
    RecoveryAction,
    RecoveryContext,
    RiskLevel,
)
from ml.src.simulation.config import SimulationConfig


@dataclass
class ScoredAction:
    """Detailed score breakdown for a single candidate recovery action."""
    action: RecoveryAction
    recovery_probability: float
    expected_recovery_value: float
    risk_cost: float
    friction_cost: float
    action_cost: float
    expected_utility: float
    allowed: bool
    rejection_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action.value,
            "recovery_probability": round(self.recovery_probability, 4),
            "expected_recovery_value": round(self.expected_recovery_value, 2),
            "risk_cost": round(self.risk_cost, 2),
            "friction_cost": round(self.friction_cost, 2),
            "action_cost": round(self.action_cost, 2),
            "expected_utility": round(self.expected_utility, 2),
            "allowed": self.allowed,
            "rejection_reason": self.rejection_reason,
        }


@dataclass
class ScoredActionDecision:
    """Final decision output with ranked candidate actions and explanation."""
    selected_action: RecoveryAction
    scored_actions: List[ScoredAction]
    risk_probability: float
    risk_level: RiskLevel
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selected_action": self.selected_action.value,
            "risk_probability": round(self.risk_probability, 4),
            "risk_level": self.risk_level.value,
            "explanation": self.explanation,
            "scored_actions": [sa.to_dict() for sa in self.scored_actions],
        }


class ExpectedUtilityEngine:
    """
    Computes Expected Utility (EU) for candidate actions.
    """

    def __init__(self, config: Optional[SimulationConfig] = None) -> None:
        self.config = config or SimulationConfig()

    def compute_action_utility(
        self,
        transaction: SyntheticTransaction,
        action: RecoveryAction,
        recovery_prob: float,
        risk_prob: float,
    ) -> ScoredAction:
        """
        Compute expected utility breakdown for a single action.
        """
        if action == RecoveryAction.STOP:
            return ScoredAction(
                action=RecoveryAction.STOP,
                recovery_probability=0.0,
                expected_recovery_value=0.0,
                risk_cost=0.0,
                friction_cost=0.0,
                action_cost=0.0,
                expected_utility=0.0,
                allowed=True,
            )

        amount = transaction.amount
        exp_value = recovery_prob * amount
        risk_cost = self.config.risk_cost(risk_prob, amount)
        friction_cost = self.config.friction_score(action.value)
        action_cost = self.config.action_cost(action.value)

        eu = exp_value - risk_cost - friction_cost - action_cost

        return ScoredAction(
            action=action,
            recovery_probability=recovery_prob,
            expected_recovery_value=exp_value,
            risk_cost=risk_cost,
            friction_cost=friction_cost,
            action_cost=action_cost,
            expected_utility=eu,
            allowed=True,
        )


class ActionRanker:
    """
    Ranks candidate actions based on Expected Utility and applies
    deterministic policy safety constraints.
    """

    def __init__(self, config: Optional[SimulationConfig] = None) -> None:
        self.config = config or SimulationConfig()
        self.eu_engine = ExpectedUtilityEngine(self.config)

    def rank_and_select_action(
        self,
        transaction: SyntheticTransaction,
        context: RecoveryContext,
        risk_prob: float,
        risk_level: RiskLevel,
        recovery_probs: Dict[RecoveryAction, float],
    ) -> ScoredActionDecision:
        """
        Rank candidate actions and apply deterministic policy safety rules.
        """
        scored_actions: List[ScoredAction] = []

        # Candidate actions to evaluate
        candidates = [
            RecoveryAction.RETRY,
            RecoveryAction.PAYMENT_LINK,
            RecoveryAction.NOTIFICATION,
            RecoveryAction.MERCHANT_REVIEW,
            RecoveryAction.WAIT,
            RecoveryAction.STOP,
        ]

        # 1. Customer Opted Out (Safety Override)
        if transaction.customer_opted_out:
            stop_scored = self.eu_engine.compute_action_utility(
                transaction, RecoveryAction.STOP, 0.0, risk_prob
            )
            return ScoredActionDecision(
                selected_action=RecoveryAction.STOP,
                scored_actions=[stop_scored],
                risk_probability=risk_prob,
                risk_level=risk_level,
                explanation="Policy Gate: Customer opted out of recovery communications -> STOP",
            )

        # 2. Critical Risk / High Risk threshold (Safety Override)
        if risk_prob >= self.config.HIGH_RISK_THRESHOLD or risk_level == RiskLevel.CRITICAL:
            mr_prob = recovery_probs.get(RecoveryAction.MERCHANT_REVIEW, 0.5)
            mr_scored = self.eu_engine.compute_action_utility(
                transaction, RecoveryAction.MERCHANT_REVIEW, mr_prob, risk_prob
            )
            return ScoredActionDecision(
                selected_action=RecoveryAction.MERCHANT_REVIEW,
                scored_actions=[mr_scored],
                risk_probability=risk_prob,
                risk_level=risk_level,
                explanation=(
                    f"Policy Gate: Risk probability ({risk_prob:.2f}) >= threshold "
                    f"({self.config.HIGH_RISK_THRESHOLD}) -> Escalated to MERCHANT_REVIEW"
                ),
            )

        # 3. Evaluate each candidate action and check policy permissions
        for action in candidates:
            prob = recovery_probs.get(action, 0.0)
            scored = self.eu_engine.compute_action_utility(
                transaction, action, prob, risk_prob
            )

            # Policy permission checks
            if action == RecoveryAction.STOP:
                scored.allowed = True
            elif context.attempt_count >= self.config.MAX_AUTOMATIC_ACTIONS:
                scored.allowed = False
                scored.rejection_reason = (
                    f"Attempt limit reached ({context.attempt_count}/{self.config.MAX_AUTOMATIC_ACTIONS})"
                )
            elif action == RecoveryAction.RETRY and context.retry_count >= self.config.MAX_RETRIES:
                scored.allowed = False
                scored.rejection_reason = (
                    f"Retry limit reached ({context.retry_count}/{self.config.MAX_RETRIES})"
                )
            elif prob < self.config.MIN_RECOVERY_PROBABILITY and action not in (
                RecoveryAction.STOP, RecoveryAction.MERCHANT_REVIEW, RecoveryAction.WAIT
            ):
                scored.allowed = False
                scored.rejection_reason = (
                    f"Recovery probability ({prob:.2f}) < threshold ({self.config.MIN_RECOVERY_PROBABILITY})"
                )

            scored_actions.append(scored)

        # Sort candidate actions by Expected Utility descending
        scored_actions.sort(key=lambda sa: sa.expected_utility, reverse=True)

        # Find top allowed action
        selected_action = RecoveryAction.STOP
        top_scored: Optional[ScoredAction] = None

        for sa in scored_actions:
            if sa.allowed:
                selected_action = sa.action
                top_scored = sa
                break

        explanation = self._build_explanation(
            transaction, selected_action, top_scored, risk_prob, risk_level, scored_actions
        )

        return ScoredActionDecision(
            selected_action=selected_action,
            scored_actions=scored_actions,
            risk_probability=risk_prob,
            risk_level=risk_level,
            explanation=explanation,
        )

    def _build_explanation(
        self,
        transaction: SyntheticTransaction,
        selected_action: RecoveryAction,
        top_scored: Optional[ScoredAction],
        risk_prob: float,
        risk_level: RiskLevel,
        scored_actions: List[ScoredAction],
    ) -> str:
        if top_scored is None or selected_action == RecoveryAction.STOP:
            return f"Decision: STOP | Rationale: No candidate action met expected utility or policy constraints."

        exp = (
            f"Decision: {selected_action.value} | "
            f"Recovery Prob: {top_scored.recovery_probability:.2f} | "
            f"Risk Prob: {risk_prob:.2f} ({risk_level.value}) | "
            f"Exp Value: INR {top_scored.expected_recovery_value:.2f} | "
            f"Risk Cost: INR {top_scored.risk_cost:.2f} | "
            f"Friction: {top_scored.friction_cost:.1f} | "
            f"Action Cost: {top_scored.action_cost:.1f} | "
            f"Expected Utility: INR {top_scored.expected_utility:.2f} | "
            f"Policy: ALLOWED"
        )
        return exp
