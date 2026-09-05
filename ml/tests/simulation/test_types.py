"""
Tests — Simulation Types and Failure Taxonomy

Covers:
- FailureCategory and FailureCode enum completeness
- FAILURE_CODE_TO_CATEGORY mapping correctness
- RecoveryAction enum completeness
- RecoveryState enum completeness
- SyntheticTransaction validation invariants
- OutcomeType enum completeness
"""

import pytest

from ml.src.simulation.types import (
    FailureCategory,
    FailureCode,
    FAILURE_CODE_TO_CATEGORY,
    CustomerProfileType,
    RecoveryAction,
    RecoveryState,
    RecoveryContext,
    OutcomeType,
    PaymentMethod,
    SyntheticTransaction,
    TERMINAL_STATES,
)


# =============================================================================
# Failure Taxonomy Tests
# =============================================================================

class TestFailureTaxonomy:

    def test_all_required_failure_categories_exist(self):
        """Phase 2 spec requires exactly these 4 categories."""
        required = {"TEMPORARY", "CUSTOMER_ACTION", "HARD_FAILURE", "RISK_RELATED"}
        actual = {c.value for c in FailureCategory}
        assert required == actual

    def test_temporary_failure_codes_exist(self):
        required = {
            FailureCode.NETWORK_TIMEOUT,
            FailureCode.GATEWAY_TIMEOUT,
            FailureCode.BANK_UNAVAILABLE,
        }
        assert required.issubset(set(FailureCode))

    def test_customer_action_failure_codes_exist(self):
        required = {
            FailureCode.AUTHENTICATION_FAILURE,
            FailureCode.PAYMENT_ABANDONED,
            FailureCode.INVALID_DETAILS,
        }
        assert required.issubset(set(FailureCode))

    def test_hard_failure_codes_exist(self):
        required = {
            FailureCode.EXPIRED_INSTRUMENT,
            FailureCode.INSUFFICIENT_FUNDS,
            FailureCode.INVALID_PAYMENT_INSTRUMENT,
        }
        assert required.issubset(set(FailureCode))

    def test_risk_related_failure_code_exists(self):
        assert FailureCode.SUSPICIOUS_PATTERN in set(FailureCode)

    def test_failure_code_to_category_mapping_complete(self):
        """Every FailureCode must map to exactly one FailureCategory."""
        for code in FailureCode:
            assert code in FAILURE_CODE_TO_CATEGORY, (
                f"FailureCode.{code.name} has no category mapping"
            )

    def test_temporary_codes_map_to_temporary_category(self):
        temp_codes = [
            FailureCode.NETWORK_TIMEOUT,
            FailureCode.GATEWAY_TIMEOUT,
            FailureCode.BANK_UNAVAILABLE,
        ]
        for code in temp_codes:
            assert FAILURE_CODE_TO_CATEGORY[code] == FailureCategory.TEMPORARY, (
                f"{code.name} should map to TEMPORARY"
            )

    def test_customer_action_codes_map_correctly(self):
        ca_codes = [
            FailureCode.AUTHENTICATION_FAILURE,
            FailureCode.PAYMENT_ABANDONED,
            FailureCode.INVALID_DETAILS,
        ]
        for code in ca_codes:
            assert FAILURE_CODE_TO_CATEGORY[code] == FailureCategory.CUSTOMER_ACTION

    def test_hard_failure_codes_map_correctly(self):
        hf_codes = [
            FailureCode.EXPIRED_INSTRUMENT,
            FailureCode.INSUFFICIENT_FUNDS,
            FailureCode.INVALID_PAYMENT_INSTRUMENT,
        ]
        for code in hf_codes:
            assert FAILURE_CODE_TO_CATEGORY[code] == FailureCategory.HARD_FAILURE

    def test_suspicious_pattern_maps_to_risk_related(self):
        assert FAILURE_CODE_TO_CATEGORY[FailureCode.SUSPICIOUS_PATTERN] == FailureCategory.RISK_RELATED


# =============================================================================
# Recovery Action Tests
# =============================================================================

class TestRecoveryActions:

    def test_all_required_actions_exist(self):
        required = {"WAIT", "RETRY", "PAYMENT_LINK", "NOTIFICATION",
                    "MERCHANT_REVIEW", "STOP"}
        actual = {a.value for a in RecoveryAction}
        assert required == actual


# =============================================================================
# State Machine Types Tests
# =============================================================================

class TestRecoveryStates:

    def test_all_required_states_exist(self):
        required = {
            "FAILED", "ANALYZING", "ELIGIBLE", "ACTION_SELECTED",
            "EXECUTING", "VERIFYING", "RECOVERED", "RETRY_PENDING",
            "STOPPED", "MERCHANT_REVIEW"
        }
        actual = {s.value for s in RecoveryState}
        assert required == actual

    def test_terminal_states_are_subset_of_all_states(self):
        for s in TERMINAL_STATES:
            assert s in RecoveryState

    def test_terminal_states_contain_expected_entries(self):
        assert RecoveryState.RECOVERED in TERMINAL_STATES
        assert RecoveryState.STOPPED in TERMINAL_STATES
        assert RecoveryState.MERCHANT_REVIEW in TERMINAL_STATES

    def test_non_terminal_states_not_in_terminal(self):
        assert RecoveryState.FAILED not in TERMINAL_STATES
        assert RecoveryState.ANALYZING not in TERMINAL_STATES
        assert RecoveryState.EXECUTING not in TERMINAL_STATES


# =============================================================================
# Outcome Types Tests
# =============================================================================

class TestOutcomeTypes:

    def test_all_outcome_types_exist(self):
        required = {"SUCCESS", "FAILED", "BLOCKED", "STOPPED", "MERCHANT_REVIEW"}
        actual = {o.value for o in OutcomeType}
        assert required == actual


# =============================================================================
# Customer Profile Types Tests
# =============================================================================

class TestCustomerProfileTypes:

    def test_all_required_profiles_exist(self):
        required = {
            "NEW_CUSTOMER",
            "REGULAR_CUSTOMER",
            "HIGH_SUCCESS_CUSTOMER",
            "FAILURE_PRONE_CUSTOMER",
            "PREVIOUSLY_RECOVERED_CUSTOMER",
        }
        actual = {p.value for p in CustomerProfileType}
        assert required == actual


# =============================================================================
# SyntheticTransaction Validation Tests
# =============================================================================

def _make_valid_transaction(**overrides) -> SyntheticTransaction:
    """Create a valid SyntheticTransaction with sensible defaults."""
    defaults = dict(
        transaction_id="txn_abc123",
        customer_id="cust_def456",
        amount=1000.0,
        currency="INR",
        payment_method=PaymentMethod.CARD,
        failure_category=FailureCategory.TEMPORARY,
        failure_code=FailureCode.NETWORK_TIMEOUT,
        transaction_hour=14,
        customer_account_age_days=180,
        previous_transaction_count=20,
        previous_successful_transactions=15,
        previous_failed_transactions=5,
        historical_success_rate=0.75,
        previous_recovery_success_rate=0.50,
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


class TestSyntheticTransactionValidation:

    def test_valid_transaction_creates_successfully(self):
        txn = _make_valid_transaction()
        assert txn.transaction_id == "txn_abc123"
        assert txn.amount == 1000.0

    def test_invalid_hour_raises(self):
        with pytest.raises(AssertionError):
            _make_valid_transaction(transaction_hour=24)

    def test_negative_hour_raises(self):
        with pytest.raises(AssertionError):
            _make_valid_transaction(transaction_hour=-1)

    def test_zero_amount_raises(self):
        with pytest.raises(AssertionError):
            _make_valid_transaction(amount=0.0)

    def test_negative_amount_raises(self):
        with pytest.raises(AssertionError):
            _make_valid_transaction(amount=-100.0)

    def test_invalid_success_rate_above_one_raises(self):
        with pytest.raises(AssertionError):
            _make_valid_transaction(historical_success_rate=1.1)

    def test_invalid_success_rate_below_zero_raises(self):
        with pytest.raises(AssertionError):
            _make_valid_transaction(historical_success_rate=-0.1)

    def test_successful_plus_failed_exceeds_total_raises(self):
        with pytest.raises(AssertionError):
            _make_valid_transaction(
                previous_transaction_count=10,
                previous_successful_transactions=8,
                previous_failed_transactions=5,  # 8+5=13 > 10
            )

    def test_no_pii_fields_present(self):
        """SyntheticTransaction must not contain PII field names."""
        txn = _make_valid_transaction()
        txn_dict = txn.__dict__
        pii_fields = ["name", "email", "phone", "address", "card_number",
                      "cvv", "account_number"]
        for field in pii_fields:
            assert field not in txn_dict, f"PII field '{field}' found in transaction"

    def test_currency_is_inr(self):
        """All synthetic transactions use INR."""
        txn = _make_valid_transaction()
        assert txn.currency == "INR"
