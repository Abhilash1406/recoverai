"""
RecoverAI Simulation — Synthetic Transaction Generator

Generates a deterministic, reproducible batch of synthetic failed transactions.

DESIGN PRINCIPLES:
1. All randomness flows through a single seeded random.Random instance.
2. Running with the same seed ALWAYS produces the same dataset.
3. No PII is generated (no names, phone numbers, email, real payment data).
4. Failure codes are sampled from profile-weighted distributions.
5. All statistical distributions are documented below.

IMPORTANT: This is a synthetic research environment. Generated transactions
do not represent real Razorpay transactions or real customer data.

Amount Distribution Assumptions
---------------------------------
Amounts are sampled uniformly within each profile's amount_range_inr.
In practice, real transaction amounts follow a log-normal or power-law
distribution. A uniform sampler is used here for simplicity and transparency.
Future phases may use more realistic distributions.

Opt-Out Sampling
-----------------
Each customer is independently assigned opted_out status based on
profile.opted_out_prob. This is a Bernoulli trial per transaction.
"""

import random
import hashlib
import json
from typing import List, Optional

from ml.src.simulation.types import (
    SyntheticTransaction,
    FailureCategory,
    FailureCode,
    CustomerProfileType,
    PaymentMethod,
    FAILURE_CODE_TO_CATEGORY,
)
from ml.src.simulation.generator.profiles import (
    CustomerProfile,
    PROFILE_TYPES_ORDERED,
    PROFILE_WEIGHTS_ORDERED,
    PROFILE_REGISTRY,
)


# Payment methods available in simulation (no real credentials)
_PAYMENT_METHODS = list(PaymentMethod)
_PAYMENT_METHOD_WEIGHTS = [0.40, 0.35, 0.12, 0.08, 0.05]  # card, upi, netbanking, wallet, emi


class TransactionGenerator:
    """
    Deterministic synthetic transaction generator.

    Creates a batch of synthetic failed transaction records that can be
    used as shared input to multiple recovery strategy experiments.

    Parameters
    ----------
    seed : int
        Master random seed. All downstream random values are derived from
        this seed deterministically. Running with the same seed always
        produces identical output.

    Usage
    -----
    >>> gen = TransactionGenerator(seed=42)
    >>> dataset = gen.generate(n=1000)
    >>> len(dataset)
    1000

    Reproducibility
    ---------------
    >>> gen1 = TransactionGenerator(seed=42)
    >>> gen2 = TransactionGenerator(seed=42)
    >>> gen1.generate(100) == gen2.generate(100)
    True
    """

    def __init__(self, seed: int) -> None:
        self.seed = seed
        self._rng = random.Random(seed)

    def generate(self, n: int) -> List[SyntheticTransaction]:
        """
        Generate n synthetic failed transactions.

        Parameters
        ----------
        n : int
            Number of transactions to generate. Must be positive.

        Returns
        -------
        list[SyntheticTransaction]
            Deterministic list of synthetic transactions.
        """
        if n <= 0:
            raise ValueError(f"n must be positive, got {n}")

        transactions: List[SyntheticTransaction] = []
        for i in range(n):
            txn = self._generate_one(i)
            transactions.append(txn)
        return transactions

    def _generate_one(self, index: int) -> SyntheticTransaction:
        """Generate a single synthetic transaction."""
        # --- Select customer profile ---
        profile_type = self._rng.choices(
            PROFILE_TYPES_ORDERED,
            weights=PROFILE_WEIGHTS_ORDERED,
            k=1,
        )[0]
        profile = PROFILE_REGISTRY[profile_type]

        # --- Generate pseudonymous IDs (no real PII) ---
        transaction_id = self._make_id("txn", index)
        customer_id = self._make_id("cust", self._rng.randint(0, int(index * 2.5) + 1))

        # --- Transaction amount ---
        amount = round(
            self._rng.uniform(profile.amount_range_inr[0], profile.amount_range_inr[1]),
            2,
        )

        # --- Payment method ---
        payment_method = self._rng.choices(
            _PAYMENT_METHODS,
            weights=_PAYMENT_METHOD_WEIGHTS,
            k=1,
        )[0]

        # --- Failure code (profile-weighted) ---
        failure_code = self._sample_failure_code(profile)
        failure_category = FAILURE_CODE_TO_CATEGORY[failure_code]

        # --- Temporal features ---
        transaction_hour = self._rng.randint(0, 23)

        # --- Account history ---
        account_age_days = self._rng.randint(
            profile.account_age_range_days[0],
            profile.account_age_range_days[1],
        )
        prev_tx_count = self._rng.randint(
            profile.prev_transaction_range[0],
            profile.prev_transaction_range[1],
        )

        # Sample success rate within profile range
        base_success_rate = self._rng.uniform(
            profile.base_success_rate_range[0],
            profile.base_success_rate_range[1],
        )
        prev_successful = round(prev_tx_count * base_success_rate)
        prev_failed = prev_tx_count - prev_successful

        # Historical success rate (computed, not magic)
        historical_success_rate = (
            prev_successful / prev_tx_count if prev_tx_count > 0 else 0.0
        )

        # Recovery success rate
        prev_recovery_rate = self._rng.uniform(
            profile.recovery_success_rate_range[0],
            profile.recovery_success_rate_range[1],
        )

        # --- Velocity & behavioural signals ---
        velocity = round(
            self._rng.uniform(profile.velocity_range[0], profile.velocity_range[1]),
            2,
        )
        device_changed = self._rng.random() < profile.device_change_prob
        location_changed = self._rng.random() < profile.location_change_prob

        # --- Amount deviation ---
        amount_deviation = round(
            self._rng.uniform(
                profile.amount_deviation_range[0],
                profile.amount_deviation_range[1],
            ),
            4,
        )

        # --- Customer opt-out ---
        customer_opted_out = self._rng.random() < profile.opted_out_prob

        return SyntheticTransaction(
            transaction_id=transaction_id,
            customer_id=customer_id,
            amount=amount,
            currency="INR",
            payment_method=payment_method,
            failure_category=failure_category,
            failure_code=failure_code,
            transaction_hour=transaction_hour,
            customer_account_age_days=account_age_days,
            previous_transaction_count=prev_tx_count,
            previous_successful_transactions=prev_successful,
            previous_failed_transactions=prev_failed,
            historical_success_rate=round(historical_success_rate, 4),
            previous_recovery_success_rate=round(prev_recovery_rate, 4),
            attempt_count=0,
            time_since_last_attempt_hours=0.0,
            transaction_velocity=velocity,
            device_changed=device_changed,
            location_changed=location_changed,
            amount_deviation=amount_deviation,
            customer_opted_out=customer_opted_out,
            profile_type=profile_type,
        )

    def _sample_failure_code(self, profile: CustomerProfile) -> FailureCode:
        """
        Sample a failure code from profile-weighted distribution.

        The failure_code_weights in each profile are unnormalized.
        random.choices handles normalization internally.
        """
        codes = list(profile.failure_code_weights.keys())
        weights = [profile.failure_code_weights[c] for c in codes]
        return self._rng.choices(codes, weights=weights, k=1)[0]

    @staticmethod
    def _make_id(prefix: str, index: int) -> str:
        """
        Create a pseudonymous identifier.

        The ID is not reversible to any real customer or transaction.
        Format: <prefix>_<hex-digest-truncated>

        Not a real UUID — shortened for readability in logs.
        """
        raw = f"{prefix}:{index}:recoverai-sim"
        digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
        return f"{prefix}_{digest}"

    @staticmethod
    def dataset_hash(transactions: List[SyntheticTransaction]) -> str:
        """
        Compute a deterministic hash of a transaction dataset.

        Used to verify that all strategies in an experiment ran on the
        exact same dataset. Two datasets with identical content produce
        the same hash.

        Parameters
        ----------
        transactions : list[SyntheticTransaction]
            The transaction dataset.

        Returns
        -------
        str
            SHA256 hex digest of the serialized dataset.
        """
        records = []
        for t in transactions:
            records.append({
                "id": t.transaction_id,
                "cid": t.customer_id,
                "amount": t.amount,
                "method": t.payment_method.value,
                "failure_code": t.failure_code.value,
                "failure_category": t.failure_category.value,
                "hour": t.transaction_hour,
                "acct_age": t.customer_account_age_days,
                "prev_tx": t.previous_transaction_count,
                "prev_ok": t.previous_successful_transactions,
                "prev_fail": t.previous_failed_transactions,
                "hist_rate": t.historical_success_rate,
                "rec_rate": t.previous_recovery_success_rate,
                "velocity": t.transaction_velocity,
                "device_chg": t.device_changed,
                "loc_chg": t.location_changed,
                "amt_dev": t.amount_deviation,
                "opted_out": t.customer_opted_out,
                "profile": t.profile_type.value,
            })
        payload = json.dumps(records, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()
