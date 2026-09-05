"""
Tests — Ground-Truth Recovery Environment

Covers:
- Probability is always in [0.0, 1.0]
- STOP always returns 0.0 probability
- RETRY is best for TEMPORARY failures
- PAYMENT_LINK is best for CUSTOMER_ACTION failures
- MERCHANT_REVIEW produces MERCHANT_REVIEW outcome
- Attempt count penalty reduces probability
- High-risk factors reduce probability
- Probability model is deterministic given same inputs
- sample_outcome returns (float, OutcomeType)
"""

import pytest

from ml.src.simulation.types import (
    SyntheticTransaction,
    FailureCategory,
    FailureCode,
    CustomerProfileType,
    PaymentMethod,
    RecoveryAction,
    OutcomeType,
)
from ml.src.simulation.environment.ground_truth import (
    GroundTruthEnvironment,
    BASE_PROBABILITY,
)


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


class TestBaseProbabilityMatrix:

    def test_all_categories_in_base_matrix(self):
        for cat in FailureCategory:
            assert cat in BASE_PROBABILITY, f"{cat.name} missing from BASE_PROBABILITY"

    def test_all_actions_in_each_category(self):
        for cat in FailureCategory:
            for action in RecoveryAction:
                assert action in BASE_PROBABILITY[cat], (
                    f"Action {action.name} missing for category {cat.name}"
                )

    def test_base_probabilities_in_valid_range(self):
        for cat in FailureCategory:
            for action, prob in BASE_PROBABILITY[cat].items():
                assert 0.0 <= prob <= 1.0, (
                    f"Base probability out of range: {cat.name}/{action.name} = {prob}"
                )

    def test_stop_always_zero_base(self):
        for cat in FailureCategory:
            assert BASE_PROBABILITY[cat][RecoveryAction.STOP] == 0.0

    def test_retry_best_for_temporary(self):
        """RETRY should have highest base probability for TEMPORARY failures."""
        temp_probs = BASE_PROBABILITY[FailureCategory.TEMPORARY]
        retry_p = temp_probs[RecoveryAction.RETRY]
        for action, p in temp_probs.items():
            if action not in (RecoveryAction.STOP, RecoveryAction.RETRY):
                assert retry_p >= p, (
                    f"RETRY ({retry_p}) should be >= {action.name} ({p}) for TEMPORARY"
                )

    def test_payment_link_best_for_customer_action(self):
        """PAYMENT_LINK should have highest base probability for CUSTOMER_ACTION."""
        ca_probs = BASE_PROBABILITY[FailureCategory.CUSTOMER_ACTION]
        pl_p = ca_probs[RecoveryAction.PAYMENT_LINK]
        for action, p in ca_probs.items():
            if action not in (RecoveryAction.STOP, RecoveryAction.PAYMENT_LINK):
                assert pl_p >= p

    def test_merchant_review_best_for_risk_related(self):
        rr_probs = BASE_PROBABILITY[FailureCategory.RISK_RELATED]
        mr_p = rr_probs[RecoveryAction.MERCHANT_REVIEW]
        for action, p in rr_probs.items():
            if action not in (RecoveryAction.STOP, RecoveryAction.MERCHANT_REVIEW):
                assert mr_p >= p

    def test_retry_low_for_hard_failure(self):
        """RETRY should have very low probability for HARD_FAILURE."""
        hf_retry = BASE_PROBABILITY[FailureCategory.HARD_FAILURE][RecoveryAction.RETRY]
        assert hf_retry < 0.15, f"RETRY probability too high for HARD_FAILURE: {hf_retry}"


class TestComputeRecoveryProbability:

    def test_probability_always_in_01_range(self):
        env = GroundTruthEnvironment(seed=42)
        txn = _make_txn()
        for action in RecoveryAction:
            p = env.compute_recovery_probability(txn, action)
            assert 0.0 <= p <= 1.0, f"Probability out of range for {action.name}: {p}"

    def test_stop_always_zero_probability(self):
        env = GroundTruthEnvironment(seed=42)
        txn = _make_txn()
        p   = env.compute_recovery_probability(txn, RecoveryAction.STOP)
        assert p == 0.0

    def test_attempt_penalty_reduces_probability(self):
        """More attempts should yield lower probability (all else equal)."""
        env  = GroundTruthEnvironment(seed=42)
        txn0 = _make_txn()
        p0   = env.compute_recovery_probability(txn0, RecoveryAction.RETRY, attempt_count=0)
        p1   = env.compute_recovery_probability(txn0, RecoveryAction.RETRY, attempt_count=1)
        p2   = env.compute_recovery_probability(txn0, RecoveryAction.RETRY, attempt_count=2)
        assert p0 >= p1 >= p2, "Attempt penalty should reduce probability monotonically"

    def test_device_change_reduces_probability(self):
        env      = GroundTruthEnvironment(seed=42)
        txn_ok   = _make_txn(device_changed=False)
        txn_chg  = _make_txn(device_changed=True)
        p_ok     = env.compute_recovery_probability(txn_ok, RecoveryAction.RETRY)
        p_chg    = env.compute_recovery_probability(txn_chg, RecoveryAction.RETRY)
        assert p_ok > p_chg, "Device change should reduce recovery probability"

    def test_location_change_reduces_probability(self):
        env      = GroundTruthEnvironment(seed=42)
        txn_ok   = _make_txn(location_changed=False)
        txn_chg  = _make_txn(location_changed=True)
        p_ok     = env.compute_recovery_probability(txn_ok, RecoveryAction.RETRY)
        p_chg    = env.compute_recovery_probability(txn_chg, RecoveryAction.RETRY)
        assert p_ok > p_chg

    def test_high_amount_deviation_reduces_probability(self):
        env      = GroundTruthEnvironment(seed=42)
        txn_low  = _make_txn(amount_deviation=0.05)
        txn_high = _make_txn(amount_deviation=0.90)
        p_low    = env.compute_recovery_probability(txn_low, RecoveryAction.RETRY)
        p_high   = env.compute_recovery_probability(txn_high, RecoveryAction.RETRY)
        assert p_low > p_high

    def test_high_velocity_reduces_probability(self):
        env      = GroundTruthEnvironment(seed=42)
        txn_low  = _make_txn(transaction_velocity=2.0)
        txn_high = _make_txn(transaction_velocity=20.0)
        p_low    = env.compute_recovery_probability(txn_low, RecoveryAction.RETRY)
        p_high   = env.compute_recovery_probability(txn_high, RecoveryAction.RETRY)
        assert p_low > p_high

    def test_high_success_history_increases_probability(self):
        env      = GroundTruthEnvironment(seed=42)
        txn_low  = _make_txn(historical_success_rate=0.20)
        txn_high = _make_txn(historical_success_rate=0.95)
        p_low    = env.compute_recovery_probability(txn_low, RecoveryAction.RETRY)
        p_high   = env.compute_recovery_probability(txn_high, RecoveryAction.RETRY)
        assert p_high > p_low

    def test_delay_bonus_for_payment_link(self):
        """Payment link with delay should have slightly higher probability."""
        env       = GroundTruthEnvironment(seed=42)
        txn       = _make_txn(failure_category=FailureCategory.CUSTOMER_ACTION,
                               failure_code=FailureCode.PAYMENT_ABANDONED)
        p_no_delay  = env.compute_recovery_probability(txn, RecoveryAction.PAYMENT_LINK,
                                                        time_since_last_hours=0.0)
        p_with_delay = env.compute_recovery_probability(txn, RecoveryAction.PAYMENT_LINK,
                                                         time_since_last_hours=2.0)
        assert p_with_delay >= p_no_delay

    def test_probability_is_deterministic(self):
        """Same inputs always produce same probability."""
        env = GroundTruthEnvironment(seed=42)
        txn = _make_txn()
        p1  = env.compute_recovery_probability(txn, RecoveryAction.RETRY, attempt_count=0)
        p2  = env.compute_recovery_probability(txn, RecoveryAction.RETRY, attempt_count=0)
        assert p1 == p2

    def test_failure_prone_profile_has_lower_probability(self):
        env  = GroundTruthEnvironment(seed=42)
        txn_hs = _make_txn(profile_type=CustomerProfileType.HIGH_SUCCESS_CUSTOMER,
                             historical_success_rate=0.92)
        txn_fp = _make_txn(profile_type=CustomerProfileType.FAILURE_PRONE_CUSTOMER,
                             historical_success_rate=0.35)
        p_hs = env.compute_recovery_probability(txn_hs, RecoveryAction.RETRY)
        p_fp = env.compute_recovery_probability(txn_fp, RecoveryAction.RETRY)
        assert p_hs > p_fp


class TestSampleOutcome:

    def test_returns_tuple_of_float_and_outcome_type(self):
        env = GroundTruthEnvironment(seed=42)
        txn = _make_txn()
        result = env.sample_outcome(txn, RecoveryAction.RETRY)
        assert isinstance(result, tuple)
        assert len(result) == 2
        prob, outcome = result
        assert isinstance(prob, float)
        assert isinstance(outcome, OutcomeType)

    def test_stop_returns_stopped_outcome(self):
        env = GroundTruthEnvironment(seed=42)
        txn = _make_txn()
        prob, outcome = env.sample_outcome(txn, RecoveryAction.STOP)
        assert prob == 0.0
        assert outcome == OutcomeType.STOPPED

    def test_merchant_review_returns_merchant_review_outcome(self):
        env = GroundTruthEnvironment(seed=42)
        txn = _make_txn()
        _, outcome = env.sample_outcome(txn, RecoveryAction.MERCHANT_REVIEW)
        assert outcome == OutcomeType.MERCHANT_REVIEW

    def test_outcome_is_success_or_failed_for_retry(self):
        env = GroundTruthEnvironment(seed=42)
        txn = _make_txn()
        for _ in range(20):
            _, outcome = env.sample_outcome(txn, RecoveryAction.RETRY)
            assert outcome in (OutcomeType.SUCCESS, OutcomeType.FAILED)


class TestRiskScore:

    def test_risk_score_in_valid_range(self):
        env = GroundTruthEnvironment(seed=42)
        txn = _make_txn()
        r   = env.compute_risk_score(txn)
        assert 0.0 <= r <= 1.0

    def test_suspicious_pattern_increases_risk(self):
        env     = GroundTruthEnvironment(seed=42)
        txn_ok  = _make_txn(failure_category=FailureCategory.TEMPORARY,
                             failure_code=FailureCode.NETWORK_TIMEOUT)
        txn_sus = _make_txn(failure_category=FailureCategory.RISK_RELATED,
                             failure_code=FailureCode.SUSPICIOUS_PATTERN)
        assert env.compute_risk_score(txn_sus) > env.compute_risk_score(txn_ok)

    def test_device_and_location_change_increase_risk(self):
        env      = GroundTruthEnvironment(seed=42)
        txn_ok   = _make_txn(device_changed=False, location_changed=False)
        txn_risk = _make_txn(device_changed=True, location_changed=True)
        assert env.compute_risk_score(txn_risk) > env.compute_risk_score(txn_ok)
