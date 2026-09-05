"""
Tests — Recovery Strategies

Covers:
- AlwaysRetryStrategy always returns RETRY
- AlwaysPaymentLinkStrategy always returns PAYMENT_LINK
- RuleBasedStrategy: all rule branches
- RecoverAIStrategy: contract compliance + placeholder behaviour
- All strategies implement RecoveryStrategy interface
- All strategies have a name property
"""

import pytest

from ml.src.simulation.config import SimulationConfig
from ml.src.simulation.types import (
    SyntheticTransaction,
    FailureCategory,
    FailureCode,
    CustomerProfileType,
    PaymentMethod,
    RecoveryAction,
    RecoveryState,
    RecoveryContext,
)
from ml.src.simulation.strategies.base import RecoveryStrategy
from ml.src.simulation.strategies.always_retry import AlwaysRetryStrategy
from ml.src.simulation.strategies.always_payment_link import AlwaysPaymentLinkStrategy
from ml.src.simulation.strategies.rule_based import RuleBasedStrategy
from ml.src.simulation.strategies.recoverai_strategy import RecoverAIStrategy


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
        transaction_id="txn_test",
        customer_id="cust_test",
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
# Interface Contract Tests
# =============================================================================

class TestStrategyInterface:

    def test_all_strategies_subclass_base(self):
        strategies = [
            AlwaysRetryStrategy(CONFIG),
            AlwaysPaymentLinkStrategy(CONFIG),
            RuleBasedStrategy(CONFIG),
            RecoverAIStrategy(CONFIG),
        ]
        for s in strategies:
            assert isinstance(s, RecoveryStrategy), (
                f"{type(s).__name__} must subclass RecoveryStrategy"
            )

    def test_all_strategies_have_name_property(self):
        strategies = [
            AlwaysRetryStrategy(CONFIG),
            AlwaysPaymentLinkStrategy(CONFIG),
            RuleBasedStrategy(CONFIG),
            RecoverAIStrategy(CONFIG),
        ]
        for s in strategies:
            assert isinstance(s.name, str)
            assert len(s.name) > 0

    def test_strategy_names_are_unique(self):
        strategies = [
            AlwaysRetryStrategy(CONFIG),
            AlwaysPaymentLinkStrategy(CONFIG),
            RuleBasedStrategy(CONFIG),
            RecoverAIStrategy(CONFIG),
        ]
        names = [s.name for s in strategies]
        assert len(names) == len(set(names)), "Strategy names must be unique"

    def test_select_action_returns_recovery_action(self):
        strategies = [
            AlwaysRetryStrategy(CONFIG),
            AlwaysPaymentLinkStrategy(CONFIG),
            RuleBasedStrategy(CONFIG),
            RecoverAIStrategy(CONFIG),
        ]
        txn     = _make_txn()
        context = _make_context()
        for s in strategies:
            action = s.select_action(txn, context)
            assert isinstance(action, RecoveryAction), (
                f"{s.name}.select_action must return RecoveryAction"
            )


# =============================================================================
# AlwaysRetryStrategy Tests
# =============================================================================

class TestAlwaysRetryStrategy:

    def test_always_returns_retry(self):
        strategy = AlwaysRetryStrategy(CONFIG)
        txn      = _make_txn()
        context  = _make_context()
        for _ in range(20):
            assert strategy.select_action(txn, context) == RecoveryAction.RETRY

    def test_returns_retry_for_all_failure_categories(self):
        strategy = AlwaysRetryStrategy(CONFIG)
        context  = _make_context()
        for cat, code in [
            (FailureCategory.TEMPORARY,       FailureCode.NETWORK_TIMEOUT),
            (FailureCategory.CUSTOMER_ACTION,  FailureCode.PAYMENT_ABANDONED),
            (FailureCategory.HARD_FAILURE,     FailureCode.INSUFFICIENT_FUNDS),
            (FailureCategory.RISK_RELATED,     FailureCode.SUSPICIOUS_PATTERN),
        ]:
            txn    = _make_txn(failure_category=cat, failure_code=code)
            action = strategy.select_action(txn, context)
            assert action == RecoveryAction.RETRY

    def test_name_is_always_retry(self):
        assert AlwaysRetryStrategy(CONFIG).name == "AlwaysRetry"


# =============================================================================
# AlwaysPaymentLinkStrategy Tests
# =============================================================================

class TestAlwaysPaymentLinkStrategy:

    def test_always_returns_payment_link(self):
        strategy = AlwaysPaymentLinkStrategy(CONFIG)
        txn      = _make_txn()
        context  = _make_context()
        for _ in range(20):
            assert strategy.select_action(txn, context) == RecoveryAction.PAYMENT_LINK

    def test_returns_payment_link_for_all_categories(self):
        strategy = AlwaysPaymentLinkStrategy(CONFIG)
        context  = _make_context()
        for cat, code in [
            (FailureCategory.TEMPORARY,       FailureCode.GATEWAY_TIMEOUT),
            (FailureCategory.CUSTOMER_ACTION,  FailureCode.AUTHENTICATION_FAILURE),
            (FailureCategory.HARD_FAILURE,     FailureCode.EXPIRED_INSTRUMENT),
            (FailureCategory.RISK_RELATED,     FailureCode.SUSPICIOUS_PATTERN),
        ]:
            txn    = _make_txn(failure_category=cat, failure_code=code)
            action = strategy.select_action(txn, context)
            assert action == RecoveryAction.PAYMENT_LINK

    def test_name_is_always_payment_link(self):
        assert AlwaysPaymentLinkStrategy(CONFIG).name == "AlwaysPaymentLink"


# =============================================================================
# RuleBasedStrategy Tests
# =============================================================================

class TestRuleBasedStrategy:

    def test_temporary_failure_returns_retry(self):
        strategy = RuleBasedStrategy(CONFIG)
        txn      = _make_txn(failure_category=FailureCategory.TEMPORARY,
                              failure_code=FailureCode.NETWORK_TIMEOUT)
        context  = _make_context(risk_score=0.10)
        assert strategy.select_action(txn, context) == RecoveryAction.RETRY

    def test_customer_action_failure_returns_payment_link(self):
        strategy = RuleBasedStrategy(CONFIG)
        txn      = _make_txn(failure_category=FailureCategory.CUSTOMER_ACTION,
                              failure_code=FailureCode.PAYMENT_ABANDONED)
        context  = _make_context(risk_score=0.10)
        assert strategy.select_action(txn, context) == RecoveryAction.PAYMENT_LINK

    def test_hard_failure_first_attempt_returns_notification(self):
        strategy = RuleBasedStrategy(CONFIG)
        txn      = _make_txn(failure_category=FailureCategory.HARD_FAILURE,
                              failure_code=FailureCode.INSUFFICIENT_FUNDS)
        context  = _make_context(attempt_count=0, risk_score=0.10)
        assert strategy.select_action(txn, context) == RecoveryAction.NOTIFICATION

    def test_hard_failure_second_attempt_returns_stop(self):
        strategy = RuleBasedStrategy(CONFIG)
        txn      = _make_txn(failure_category=FailureCategory.HARD_FAILURE,
                              failure_code=FailureCode.EXPIRED_INSTRUMENT)
        context  = _make_context(attempt_count=1, risk_score=0.10)
        assert strategy.select_action(txn, context) == RecoveryAction.STOP

    def test_risk_related_failure_returns_merchant_review(self):
        strategy = RuleBasedStrategy(CONFIG)
        txn      = _make_txn(failure_category=FailureCategory.RISK_RELATED,
                              failure_code=FailureCode.SUSPICIOUS_PATTERN)
        context  = _make_context(risk_score=0.10)
        assert strategy.select_action(txn, context) == RecoveryAction.MERCHANT_REVIEW

    def test_opted_out_customer_returns_stop(self):
        """Rule 1: opted-out customer must always get STOP."""
        strategy = RuleBasedStrategy(CONFIG)
        txn      = _make_txn(customer_opted_out=True,
                              failure_category=FailureCategory.TEMPORARY,
                              failure_code=FailureCode.NETWORK_TIMEOUT)
        context  = _make_context(risk_score=0.10)
        assert strategy.select_action(txn, context) == RecoveryAction.STOP

    def test_high_risk_returns_merchant_review(self):
        """Rule 2: high risk score escalates to MERCHANT_REVIEW."""
        strategy   = RuleBasedStrategy(CONFIG)
        txn        = _make_txn(failure_category=FailureCategory.TEMPORARY,
                                failure_code=FailureCode.NETWORK_TIMEOUT,
                                customer_opted_out=False)
        high_risk  = _make_context(risk_score=CONFIG.HIGH_RISK_THRESHOLD + 0.05)
        assert strategy.select_action(txn, high_risk) == RecoveryAction.MERCHANT_REVIEW

    def test_opted_out_takes_priority_over_high_risk(self):
        """Rule 1 (opt-out) takes priority over Rule 2 (high risk)."""
        strategy = RuleBasedStrategy(CONFIG)
        txn      = _make_txn(customer_opted_out=True)
        context  = _make_context(risk_score=CONFIG.HIGH_RISK_THRESHOLD + 0.10)
        assert strategy.select_action(txn, context) == RecoveryAction.STOP

    def test_name_is_rule_based(self):
        assert RuleBasedStrategy(CONFIG).name == "RuleBased"


# =============================================================================
# RecoverAI Strategy Contract Tests
# =============================================================================

class TestRecoverAIStrategy:

    def test_is_instance_of_recovery_strategy(self):
        s = RecoverAIStrategy(CONFIG)
        assert isinstance(s, RecoveryStrategy)

    def test_name_is_recoverai(self):
        assert RecoverAIStrategy(CONFIG).name == "RecoverAI"

    def test_is_placeholder_returns_true(self):
        """In Phase 2, is_placeholder must return True."""
        s = RecoverAIStrategy(CONFIG)
        assert s.is_placeholder() is True

    def test_returns_stop_as_placeholder(self):
        """Phase 2 placeholder must return STOP for all inputs."""
        s       = RecoverAIStrategy(CONFIG)
        txn     = _make_txn()
        context = _make_context()
        action  = s.select_action(txn, context)
        assert action == RecoveryAction.STOP, (
            "RecoverAI Phase 2 placeholder must return STOP"
        )

    def test_placeholder_consistent_across_all_failure_types(self):
        s = RecoverAIStrategy(CONFIG)
        context = _make_context()
        for cat, code in [
            (FailureCategory.TEMPORARY,       FailureCode.NETWORK_TIMEOUT),
            (FailureCategory.CUSTOMER_ACTION,  FailureCode.PAYMENT_ABANDONED),
            (FailureCategory.HARD_FAILURE,     FailureCode.INSUFFICIENT_FUNDS),
            (FailureCategory.RISK_RELATED,     FailureCode.SUSPICIOUS_PATTERN),
        ]:
            txn    = _make_txn(failure_category=cat, failure_code=code)
            action = s.select_action(txn, context)
            assert action == RecoveryAction.STOP

    def test_has_implementation_note(self):
        s = RecoverAIStrategy(CONFIG)
        assert isinstance(s.implementation_note, str)
        assert len(s.implementation_note) > 0
        assert "Phase" in s.implementation_note

    def test_has_phase_label(self):
        s = RecoverAIStrategy(CONFIG)
        assert "PHASE_" in s.phase_label
