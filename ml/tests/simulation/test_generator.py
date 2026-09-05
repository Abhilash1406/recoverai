"""
Tests — Transaction Generator and Dataset Quality

Covers:
- Deterministic generation (same seed → same dataset)
- Dataset contains expected fields (no PII)
- Valid amounts
- Valid failure categories and codes
- Valid transaction hours
- Profile distribution is not all one profile
- Both opted-out and opted-in customers appear
- dataset_hash is stable and correct
"""

import pytest

from ml.src.simulation.types import (
    FailureCategory,
    FailureCode,
    CustomerProfileType,
    PaymentMethod,
    FAILURE_CODE_TO_CATEGORY,
)
from ml.src.simulation.generator.transaction_generator import TransactionGenerator


class TestTransactionGeneratorBasics:

    def test_generates_correct_count(self):
        gen = TransactionGenerator(seed=42)
        ds  = gen.generate(100)
        assert len(ds) == 100

    def test_all_transaction_ids_are_unique(self):
        gen  = TransactionGenerator(seed=42)
        ds   = gen.generate(200)
        ids  = [t.transaction_id for t in ds]
        assert len(set(ids)) == len(ids), "Transaction IDs must be unique"

    def test_raises_on_zero_n(self):
        gen = TransactionGenerator(seed=42)
        with pytest.raises(ValueError):
            gen.generate(0)

    def test_raises_on_negative_n(self):
        gen = TransactionGenerator(seed=42)
        with pytest.raises(ValueError):
            gen.generate(-10)


class TestNoRealPII:

    def test_transaction_id_is_pseudonymous(self):
        """Transaction IDs must not be real payment gateway IDs."""
        gen = TransactionGenerator(seed=42)
        ds  = gen.generate(10)
        for t in ds:
            # Must start with txn_ prefix
            assert t.transaction_id.startswith("txn_"), (
                f"Unexpected transaction_id format: {t.transaction_id}"
            )
            # Must not look like a real Razorpay pay_xxx ID
            assert not t.transaction_id.startswith("pay_")
            assert not t.transaction_id.startswith("order_")

    def test_customer_id_is_pseudonymous(self):
        gen = TransactionGenerator(seed=42)
        ds  = gen.generate(10)
        for t in ds:
            assert t.customer_id.startswith("cust_")

    def test_no_pii_attributes(self):
        """Transaction objects must not carry PII field names."""
        gen = TransactionGenerator(seed=42)
        ds  = gen.generate(10)
        pii_fields = ["name", "email", "phone", "mobile", "address",
                      "card_number", "cvv", "pan", "aadhaar"]
        for t in ds:
            for field in pii_fields:
                assert not hasattr(t, field), f"PII field '{field}' found"


class TestDataQuality:

    def test_amounts_are_positive(self):
        gen = TransactionGenerator(seed=42)
        ds  = gen.generate(200)
        for t in ds:
            assert t.amount > 0, f"Non-positive amount: {t.amount}"

    def test_currency_is_always_inr(self):
        gen = TransactionGenerator(seed=42)
        ds  = gen.generate(100)
        for t in ds:
            assert t.currency == "INR"

    def test_transaction_hours_in_valid_range(self):
        gen = TransactionGenerator(seed=42)
        ds  = gen.generate(200)
        for t in ds:
            assert 0 <= t.transaction_hour <= 23

    def test_failure_categories_are_valid_enum(self):
        gen         = TransactionGenerator(seed=42)
        ds          = gen.generate(200)
        valid_cats  = set(FailureCategory)
        for t in ds:
            assert t.failure_category in valid_cats

    def test_failure_codes_are_valid_enum(self):
        gen         = TransactionGenerator(seed=42)
        ds          = gen.generate(200)
        valid_codes = set(FailureCode)
        for t in ds:
            assert t.failure_code in valid_codes

    def test_failure_code_matches_category(self):
        gen = TransactionGenerator(seed=42)
        ds  = gen.generate(200)
        for t in ds:
            expected_cat = FAILURE_CODE_TO_CATEGORY[t.failure_code]
            assert t.failure_category == expected_cat, (
                f"Mismatch: code={t.failure_code.name} "
                f"category={t.failure_category.name} expected={expected_cat.name}"
            )

    def test_historical_success_rate_in_valid_range(self):
        gen = TransactionGenerator(seed=42)
        ds  = gen.generate(200)
        for t in ds:
            assert 0.0 <= t.historical_success_rate <= 1.0

    def test_recovery_success_rate_in_valid_range(self):
        gen = TransactionGenerator(seed=42)
        ds  = gen.generate(200)
        for t in ds:
            assert 0.0 <= t.previous_recovery_success_rate <= 1.0

    def test_successful_plus_failed_leq_total(self):
        gen = TransactionGenerator(seed=42)
        ds  = gen.generate(200)
        for t in ds:
            assert (t.previous_successful_transactions
                    + t.previous_failed_transactions
                    <= t.previous_transaction_count)

    def test_amount_deviation_non_negative(self):
        gen = TransactionGenerator(seed=42)
        ds  = gen.generate(200)
        for t in ds:
            assert t.amount_deviation >= 0.0

    def test_attempt_count_starts_at_zero(self):
        gen = TransactionGenerator(seed=42)
        ds  = gen.generate(50)
        for t in ds:
            assert t.attempt_count == 0

    def test_payment_methods_are_valid(self):
        gen           = TransactionGenerator(seed=42)
        ds            = gen.generate(200)
        valid_methods = set(PaymentMethod)
        for t in ds:
            assert t.payment_method in valid_methods


class TestDistributionQuality:

    def test_multiple_failure_categories_represented(self):
        """A large dataset should include all 4 failure categories."""
        gen        = TransactionGenerator(seed=42)
        ds         = gen.generate(500)
        categories = {t.failure_category for t in ds}
        assert len(categories) == 4, (
            f"Expected all 4 failure categories, got: {categories}"
        )

    def test_multiple_profiles_represented(self):
        """A large dataset should sample multiple profiles."""
        gen      = TransactionGenerator(seed=42)
        ds       = gen.generate(500)
        profiles = {t.profile_type for t in ds}
        assert len(profiles) >= 4, (
            f"Expected at least 4 profiles, got: {profiles}"
        )

    def test_both_opted_in_and_opted_out_present(self):
        gen     = TransactionGenerator(seed=42)
        ds      = gen.generate(500)
        opted   = [t.customer_opted_out for t in ds]
        assert any(opted),  "No opted-out customers in dataset"
        assert not all(opted), "All customers opted out — unrealistic"

    def test_both_device_changed_and_unchanged(self):
        gen = TransactionGenerator(seed=42)
        ds  = gen.generate(500)
        changed = [t.device_changed for t in ds]
        assert any(changed)
        assert not all(changed)

    def test_regular_customer_is_most_common_profile(self):
        """REGULAR_CUSTOMER has 40% weight — should be most common."""
        gen      = TransactionGenerator(seed=42)
        ds       = gen.generate(1000)
        from collections import Counter
        counts   = Counter(t.profile_type for t in ds)
        most_common = counts.most_common(1)[0][0]
        assert most_common == CustomerProfileType.REGULAR_CUSTOMER


class TestDatasetHash:

    def test_hash_is_deterministic(self):
        gen1 = TransactionGenerator(seed=42)
        gen2 = TransactionGenerator(seed=42)
        ds1  = gen1.generate(100)
        ds2  = gen2.generate(100)
        assert TransactionGenerator.dataset_hash(ds1) == TransactionGenerator.dataset_hash(ds2)

    def test_different_seeds_produce_different_hashes(self):
        gen1 = TransactionGenerator(seed=42)
        gen2 = TransactionGenerator(seed=123)
        ds1  = gen1.generate(100)
        ds2  = gen2.generate(100)
        assert TransactionGenerator.dataset_hash(ds1) != TransactionGenerator.dataset_hash(ds2)

    def test_hash_is_hex_string(self):
        gen  = TransactionGenerator(seed=42)
        ds   = gen.generate(10)
        h    = TransactionGenerator.dataset_hash(ds)
        assert isinstance(h, str)
        assert len(h) == 64  # SHA256 → 64 hex chars
