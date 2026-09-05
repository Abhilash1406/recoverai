"""
RecoverAI ML — Tests for Expected Utility Engine, Action Ranker, Safety Gate, and RecoverAI Strategy

Covers:
- Expected Utility (EU) calculation formula
- Safety gate constraints (opt-out, high risk, min probability, max attempts, max retries)
- Action ranking and transparent explanation output
- ML-powered RecoverAIStrategy execution
"""

import pytest

from ml.src.simulation.config import SimulationConfig
from ml.src.simulation.types import (
    SyntheticTransaction,
    RecoveryAction,
    RecoveryState,
    RecoveryContext,
    FailureCategory,
    FailureCode,
    PaymentMethod,
    CustomerProfileType,
    RiskLevel,
)
from ml.src.decision.engine import ExpectedUtilityEngine, ActionRanker
from ml.src.risk.model import RiskPredictionModel
from ml.src.recovery.model import RecoveryPredictionModel
from ml.src.simulation.strategies.recoverai_strategy import RecoverAIStrategy
from ml.src.features.dataset import generate_ml_datasets, split_train_val_test


CONFIG = SimulationConfig()


def _make_context(**overrides) -> RecoveryContext:
    defaults = dict(
        current_state=RecoveryState.ELIGIBLE,
        attempt_count=0,
        retry_count=0,
        risk_score=0.20,
        time_since_first_failure_hours=0.0,
    )
    defaults.update(overrides)
    return RecoveryContext(**defaults)


def _make_txn(**overrides) -> SyntheticTransaction:
    defaults = dict(
        transaction_id="txn_dec_test",
        customer_id="cust_dec_test",
        amount=5000.0,
        currency="INR",
        payment_method=PaymentMethod.CARD,
        failure_category=FailureCategory.TEMPORARY,
        failure_code=FailureCode.NETWORK_TIMEOUT,
        transaction_hour=12,
        customer_account_age_days=365,
        previous_transaction_count=50,
        previous_successful_transactions=40,
        previous_failed_transactions=10,
        historical_success_rate=0.80,
        previous_recovery_success_rate=0.60,
        attempt_count=0,
        time_since_last_attempt_hours=0.0,
        transaction_velocity=3.0,
        device_changed=False,
        location_changed=False,
        amount_deviation=0.10,
        customer_opted_out=False,
        profile_type=CustomerProfileType.REGULAR_CUSTOMER,
    )
    defaults.update(overrides)
    return SyntheticTransaction(**defaults)


# =============================================================================
# Expected Utility Engine Tests
# =============================================================================

class TestExpectedUtilityEngine:

    def test_eu_formula_calculation(self):
        engine = ExpectedUtilityEngine(CONFIG)
        txn = _make_txn(amount=1000.0)
        # RETRY: p=0.80, amount=1000 => exp_val=800
        # risk_prob=0.10 => risk_cost = 0.10 * 1000 * 0.05 = 5.0
        # friction = 1.0, action_cost = 0.5
        # EU = 800 - 5.0 - 1.0 - 0.5 = 793.5
        scored = engine.compute_action_utility(
            txn, RecoveryAction.RETRY, recovery_prob=0.80, risk_prob=0.10
        )
        assert scored.expected_recovery_value == pytest.approx(800.0)
        assert scored.risk_cost == pytest.approx(5.0)
        assert scored.friction_cost == pytest.approx(1.0)
        assert scored.action_cost == pytest.approx(0.5)
        assert scored.expected_utility == pytest.approx(793.5)

    def test_stop_action_has_zero_utility_and_zero_costs(self):
        engine = ExpectedUtilityEngine(CONFIG)
        txn = _make_txn(amount=5000.0)
        scored = engine.compute_action_utility(
            txn, RecoveryAction.STOP, recovery_prob=0.80, risk_prob=0.50
        )
        assert scored.expected_utility == 0.0
        assert scored.risk_cost == 0.0
        assert scored.action_cost == 0.0


# =============================================================================
# Action Ranker & Policy Gate Tests
# =============================================================================

class TestActionRanker:

    def test_customer_opted_out_returns_stop(self):
        ranker = ActionRanker(CONFIG)
        txn = _make_txn(customer_opted_out=True)
        context = _make_context()
        probs = {RecoveryAction.RETRY: 0.90, RecoveryAction.PAYMENT_LINK: 0.90}
        decision = ranker.rank_and_select_action(txn, context, 0.10, RiskLevel.LOW, probs)

        assert decision.selected_action == RecoveryAction.STOP
        assert "opted out" in decision.explanation.lower()

    def test_critical_risk_returns_merchant_review(self):
        ranker = ActionRanker(CONFIG)
        txn = _make_txn()
        context = _make_context()
        probs = {RecoveryAction.RETRY: 0.90, RecoveryAction.MERCHANT_REVIEW: 0.50}
        decision = ranker.rank_and_select_action(
            txn, context, CONFIG.HIGH_RISK_THRESHOLD + 0.05, RiskLevel.CRITICAL, probs
        )

        assert decision.selected_action == RecoveryAction.MERCHANT_REVIEW
        assert "MERCHANT_REVIEW" in decision.explanation

    def test_low_probability_candidate_action_rejected(self):
        ranker = ActionRanker(CONFIG)
        txn = _make_txn()
        context = _make_context()
        # p_retry = 0.20 < MIN_RECOVERY_PROBABILITY (0.60)
        probs = {RecoveryAction.RETRY: 0.20, RecoveryAction.PAYMENT_LINK: 0.70}
        decision = ranker.rank_and_select_action(txn, context, 0.10, RiskLevel.LOW, probs)

        assert decision.selected_action == RecoveryAction.PAYMENT_LINK
        # Verify RETRY was rejected
        retry_scored = next(sa for sa in decision.scored_actions if sa.action == RecoveryAction.RETRY)
        assert not retry_scored.allowed
        assert "threshold" in retry_scored.rejection_reason.lower()


# =============================================================================
# ML-Powered RecoverAI Strategy Tests
# =============================================================================

class TestRecoverAIStrategyPhase3:

    def test_ml_powered_strategy_execution(self):
        # 1. Train quick models
        data = generate_ml_datasets(seed=42, n_transactions=150)
        Xr_tr, Xr_val, Xr_te, yr_tr, yr_val, yr_te = split_train_val_test(
            data["X_risk"], data["y_risk"], seed=42
        )
        risk_m = RiskPredictionModel(model_type="random_forest")
        risk_m.fit(Xr_tr, yr_tr)

        Xrec_tr, Xrec_val, Xrec_te, yrec_tr, yrec_val, yrec_te = split_train_val_test(
            data["X_recovery"], data["y_recovery"], seed=42
        )
        rec_m = RecoveryPredictionModel(model_type="gradient_boosting", calibrate=True)
        rec_m.fit(Xrec_tr, yrec_tr, Xrec_val, yrec_val)

        # 2. Instantiate Phase 3 strategy
        strategy = RecoverAIStrategy(CONFIG, risk_model=risk_m, recovery_model=rec_m)
        assert strategy.is_placeholder() is False
        assert strategy.phase_label == "PHASE_3_ML_DECISION_ENGINE"

        # 3. Select action
        txn = _make_txn()
        context = _make_context()
        action = strategy.select_action(txn, context)

        assert isinstance(action, RecoveryAction)
        assert strategy.last_decision is not None
        assert len(strategy.last_decision.explanation) > 0
