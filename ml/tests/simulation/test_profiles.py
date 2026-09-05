"""
Tests — Customer Profiles

Covers:
- All 5 profiles exist in registry
- Population weights sum to 1.0
- Profiles have non-overlapping characteristics (not all identical)
- Each profile has at least one failure code weight
- All probability ranges are valid [0, 1]
- Amount ranges are positive and ordered (min < max)
- Opt-out probabilities are valid
"""

import pytest

from ml.src.simulation.types import CustomerProfileType, FailureCode
from ml.src.simulation.generator.profiles import (
    PROFILE_REGISTRY,
    PROFILE_POPULATION_WEIGHTS,
    PROFILE_WEIGHTS_ORDERED,
    PROFILE_TYPES_ORDERED,
    get_profile,
    NEW_CUSTOMER,
    REGULAR_CUSTOMER,
    HIGH_SUCCESS_CUSTOMER,
    FAILURE_PRONE_CUSTOMER,
    PREVIOUSLY_RECOVERED_CUSTOMER,
)


class TestProfileRegistry:

    def test_all_five_profiles_exist(self):
        required = set(CustomerProfileType)
        actual   = set(PROFILE_REGISTRY.keys())
        assert required == actual

    def test_get_profile_returns_correct_type(self):
        for ptype in CustomerProfileType:
            p = get_profile(ptype)
            assert p.profile_type == ptype

    def test_population_weights_sum_to_one(self):
        total = sum(PROFILE_POPULATION_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9, f"Weights sum to {total}, expected 1.0"

    def test_all_profile_types_have_weight(self):
        for ptype in CustomerProfileType:
            assert ptype in PROFILE_POPULATION_WEIGHTS

    def test_profile_types_ordered_and_weights_aligned(self):
        assert len(PROFILE_TYPES_ORDERED) == len(PROFILE_WEIGHTS_ORDERED)
        for ptype, weight in zip(PROFILE_TYPES_ORDERED, PROFILE_WEIGHTS_ORDERED):
            assert PROFILE_POPULATION_WEIGHTS[ptype] == weight

    def test_no_zero_weight_profiles(self):
        """Every profile must be sampled with non-zero probability."""
        for ptype, weight in PROFILE_POPULATION_WEIGHTS.items():
            assert weight > 0.0, f"Profile {ptype.name} has zero weight"


class TestProfileCharacteristics:

    def test_amount_ranges_are_valid(self):
        for ptype, profile in PROFILE_REGISTRY.items():
            lo, hi = profile.amount_range_inr
            assert lo > 0, f"{ptype.name}: min amount must be positive"
            assert hi > lo, f"{ptype.name}: max amount must exceed min"

    def test_success_rate_ranges_are_valid(self):
        for ptype, profile in PROFILE_REGISTRY.items():
            lo, hi = profile.base_success_rate_range
            assert 0.0 <= lo <= 1.0, f"{ptype.name}: invalid min success rate"
            assert 0.0 <= hi <= 1.0, f"{ptype.name}: invalid max success rate"
            assert hi >= lo, f"{ptype.name}: max must be >= min"

    def test_recovery_rate_ranges_are_valid(self):
        for ptype, profile in PROFILE_REGISTRY.items():
            lo, hi = profile.recovery_success_rate_range
            assert 0.0 <= lo <= 1.0
            assert 0.0 <= hi <= 1.0
            assert hi >= lo

    def test_opt_out_probs_are_valid(self):
        for ptype, profile in PROFILE_REGISTRY.items():
            assert 0.0 <= profile.opted_out_prob <= 1.0

    def test_device_change_probs_are_valid(self):
        for ptype, profile in PROFILE_REGISTRY.items():
            assert 0.0 <= profile.device_change_prob <= 1.0

    def test_location_change_probs_are_valid(self):
        for ptype, profile in PROFILE_REGISTRY.items():
            assert 0.0 <= profile.location_change_prob <= 1.0

    def test_each_profile_has_failure_code_weights(self):
        for ptype, profile in PROFILE_REGISTRY.items():
            assert len(profile.failure_code_weights) > 0

    def test_failure_code_weights_are_positive(self):
        for ptype, profile in PROFILE_REGISTRY.items():
            for code, w in profile.failure_code_weights.items():
                assert w > 0, f"{ptype.name}: weight for {code.name} must be positive"


class TestProfileDifferentiation:
    """Profiles must not be identical — they represent distinct behavioural segments."""

    def test_high_success_has_higher_base_rate_than_failure_prone(self):
        hs_min, _ = HIGH_SUCCESS_CUSTOMER.base_success_rate_range
        _, fp_max = FAILURE_PRONE_CUSTOMER.base_success_rate_range
        assert hs_min > fp_max, (
            "HIGH_SUCCESS_CUSTOMER should have higher success rates than FAILURE_PRONE"
        )

    def test_new_customer_has_no_prior_recovery_history(self):
        lo, hi = NEW_CUSTOMER.recovery_success_rate_range
        assert lo == 0.0 and hi == 0.0, (
            "NEW_CUSTOMER should have zero prior recovery history"
        )

    def test_failure_prone_has_highest_opt_out(self):
        failure_prone_rate = FAILURE_PRONE_CUSTOMER.opted_out_prob
        high_success_rate  = HIGH_SUCCESS_CUSTOMER.opted_out_prob
        assert failure_prone_rate > high_success_rate

    def test_previously_recovered_has_high_recovery_rate(self):
        lo, hi = PREVIOUSLY_RECOVERED_CUSTOMER.recovery_success_rate_range
        assert lo >= 0.50, "Previously recovered customers should have recovery rate >= 0.50"

    def test_failure_prone_has_higher_amount_deviation(self):
        _, fp_hi = FAILURE_PRONE_CUSTOMER.amount_deviation_range
        _, hs_hi = HIGH_SUCCESS_CUSTOMER.amount_deviation_range
        assert fp_hi > hs_hi, (
            "FAILURE_PRONE should have higher amount deviation than HIGH_SUCCESS"
        )

    def test_profiles_have_different_failure_patterns(self):
        """Different profiles should emphasize different failure codes."""
        new_top   = max(NEW_CUSTOMER.failure_code_weights,
                        key=NEW_CUSTOMER.failure_code_weights.get)
        fp_top    = max(FAILURE_PRONE_CUSTOMER.failure_code_weights,
                        key=FAILURE_PRONE_CUSTOMER.failure_code_weights.get)
        hs_top    = max(HIGH_SUCCESS_CUSTOMER.failure_code_weights,
                        key=HIGH_SUCCESS_CUSTOMER.failure_code_weights.get)

        # High-success customers should have network/gateway as top failure
        assert hs_top in (FailureCode.NETWORK_TIMEOUT, FailureCode.GATEWAY_TIMEOUT)
        # Failure-prone customers should have funds/instrument as top failure
        assert fp_top in (FailureCode.INSUFFICIENT_FUNDS, FailureCode.EXPIRED_INSTRUMENT,
                          FailureCode.INVALID_PAYMENT_INSTRUMENT)
