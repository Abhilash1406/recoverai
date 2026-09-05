"""
RecoverAI Simulation — Customer Profiles

Defines the 5 customer behavioural profiles used by the transaction generator.

IMPORTANT: These profiles are SYNTHETIC ASSUMPTIONS for simulation purposes.
They do not represent real Razorpay customer segments or real behavioural data.
All values are documented assumptions for fair comparative evaluation.

Population Distribution Assumptions
------------------------------------
The profiles are sampled with the following weights. This reflects a realistic
(but entirely synthetic) distribution of a payment platform's user base:

    NEW_CUSTOMER:               20% — First-time or early users
    REGULAR_CUSTOMER:           40% — Core user base with moderate history
    HIGH_SUCCESS_CUSTOMER:      15% — Reliable, established users
    FAILURE_PRONE_CUSTOMER:     15% — Users with poor instruments or habits
    PREVIOUSLY_RECOVERED_CUSTOMER: 10% — Users who have been recovered before

These weights are intentionally unequal to create a realistic mixture.
Using equal weights would not represent the natural distribution of
payment platform users.

Profile Parameter Assumptions
-------------------------------
Each profile specifies ranges for:

1. amount_range_inr : (min, max) — INR transaction amount range
   Reflects different spending patterns per profile type.

2. account_age_range_days : (min, max) — Account age at time of transaction.
   New customers have younger accounts.

3. prev_transaction_range : (min, max) — Prior transaction count.
   Higher for established customers.

4. base_success_rate_range : (min, max) — Historical success rate range.
   High-success customers cluster near 0.9+.

5. recovery_success_rate_range : (min, max) — Previous recovery rate.
   0.0 for new customers (no prior failures), higher for recovered customers.

6. velocity_range : (min, max) — Transactions per 24 hours.

7. device_change_prob : float — P(device changed since last transaction).

8. location_change_prob : float — P(location changed since last transaction).

9. opted_out_prob : float — P(customer opted out of recovery communications).

10. failure_code_weights : dict[FailureCode, float] — Relative probability
    of each failure code for this profile. Does not need to sum to 1.0;
    will be normalised by the generator.
"""

from dataclasses import dataclass, field
from typing import Dict, Tuple

from ml.src.simulation.types import CustomerProfileType, FailureCode


@dataclass
class CustomerProfile:
    """
    Quantitative specification of a customer behavioural profile.

    All ranges are (min, max) tuples sampled uniformly by the generator.
    """
    profile_type: CustomerProfileType

    # Transaction amount in INR
    amount_range_inr: Tuple[float, float]

    # Account age
    account_age_range_days: Tuple[int, int]

    # Transaction history counts
    prev_transaction_range: Tuple[int, int]

    # Historical payment success rate [0, 1]
    base_success_rate_range: Tuple[float, float]

    # Historical recovery success rate [0, 1]
    recovery_success_rate_range: Tuple[float, float]

    # Transaction velocity (tx per 24h)
    velocity_range: Tuple[float, float]

    # Behavioural change probabilities
    device_change_prob: float
    location_change_prob: float

    # Opt-out probability
    opted_out_prob: float

    # Failure code sampling weights (unnormalized)
    failure_code_weights: Dict[FailureCode, float]

    # Amount deviation range |amount - avg| / avg
    amount_deviation_range: Tuple[float, float]

    def __post_init__(self) -> None:
        assert 0.0 <= self.device_change_prob <= 1.0
        assert 0.0 <= self.location_change_prob <= 1.0
        assert 0.0 <= self.opted_out_prob <= 1.0
        assert len(self.failure_code_weights) > 0


# =============================================================================
# Profile Definitions
# =============================================================================

#
# ASSUMPTION DOCUMENTATION
#
# NEW_CUSTOMER
# ------------
# Younger accounts, smaller amounts, fewer transactions.
# Higher authentication failures (unfamiliarity with 3DS flow).
# Lower historical success rate due to limited data.
# No prior recovery history.
# Moderate velocity (testing the platform).
#
NEW_CUSTOMER = CustomerProfile(
    profile_type=CustomerProfileType.NEW_CUSTOMER,
    amount_range_inr=(200.0, 5_000.0),
    account_age_range_days=(0, 90),
    prev_transaction_range=(1, 15),
    base_success_rate_range=(0.50, 0.75),
    recovery_success_rate_range=(0.0, 0.0),   # no prior recovery history
    velocity_range=(1.0, 5.0),
    device_change_prob=0.20,
    location_change_prob=0.15,
    opted_out_prob=0.05,
    amount_deviation_range=(0.0, 0.30),
    failure_code_weights={
        # New customers struggle with authentication
        FailureCode.AUTHENTICATION_FAILURE:  0.35,
        FailureCode.PAYMENT_ABANDONED:       0.20,
        FailureCode.INVALID_DETAILS:         0.15,
        FailureCode.NETWORK_TIMEOUT:         0.15,
        FailureCode.GATEWAY_TIMEOUT:         0.10,
        FailureCode.BANK_UNAVAILABLE:        0.05,
    },
)

#
# REGULAR_CUSTOMER
# ----------------
# Core user base. Moderate amounts and history.
# Mix of failure types reflecting typical usage.
# Moderate recovery history.
#
REGULAR_CUSTOMER = CustomerProfile(
    profile_type=CustomerProfileType.REGULAR_CUSTOMER,
    amount_range_inr=(500.0, 25_000.0),
    account_age_range_days=(90, 730),
    prev_transaction_range=(15, 100),
    base_success_rate_range=(0.70, 0.88),
    recovery_success_rate_range=(0.30, 0.60),
    velocity_range=(1.0, 10.0),
    device_change_prob=0.10,
    location_change_prob=0.10,
    opted_out_prob=0.08,
    amount_deviation_range=(0.0, 0.40),
    failure_code_weights={
        FailureCode.NETWORK_TIMEOUT:         0.20,
        FailureCode.GATEWAY_TIMEOUT:         0.15,
        FailureCode.AUTHENTICATION_FAILURE:  0.20,
        FailureCode.PAYMENT_ABANDONED:       0.10,
        FailureCode.INSUFFICIENT_FUNDS:      0.15,
        FailureCode.BANK_UNAVAILABLE:        0.10,
        FailureCode.EXPIRED_INSTRUMENT:      0.05,
        FailureCode.INVALID_DETAILS:         0.05,
    },
)

#
# HIGH_SUCCESS_CUSTOMER
# ---------------------
# Reliable customers with established good payment history.
# Mostly experience transient failures (network, gateway).
# Very few authentication issues.
# Low opt-out rate.
#
HIGH_SUCCESS_CUSTOMER = CustomerProfile(
    profile_type=CustomerProfileType.HIGH_SUCCESS_CUSTOMER,
    amount_range_inr=(1_000.0, 100_000.0),
    account_age_range_days=(365, 2000),
    prev_transaction_range=(50, 500),
    base_success_rate_range=(0.88, 0.98),
    recovery_success_rate_range=(0.60, 0.90),
    velocity_range=(2.0, 15.0),
    device_change_prob=0.05,
    location_change_prob=0.05,
    opted_out_prob=0.02,
    amount_deviation_range=(0.0, 0.20),
    failure_code_weights={
        # Mostly transient failures — their instruments are good
        FailureCode.NETWORK_TIMEOUT:         0.35,
        FailureCode.GATEWAY_TIMEOUT:         0.30,
        FailureCode.BANK_UNAVAILABLE:        0.20,
        FailureCode.AUTHENTICATION_FAILURE:  0.10,
        FailureCode.PAYMENT_ABANDONED:       0.05,
    },
)

#
# FAILURE_PRONE_CUSTOMER
# ----------------------
# Users with poor instruments, habit of abandoning, or insufficient funds.
# High failure rate, low historical success rate.
# Higher opt-out rate (frustrated with recovery attempts).
# High amount deviation (erratic spending).
#
FAILURE_PRONE_CUSTOMER = CustomerProfile(
    profile_type=CustomerProfileType.FAILURE_PRONE_CUSTOMER,
    amount_range_inr=(200.0, 10_000.0),
    account_age_range_days=(30, 500),
    prev_transaction_range=(5, 50),
    base_success_rate_range=(0.25, 0.55),
    recovery_success_rate_range=(0.10, 0.35),
    velocity_range=(0.5, 8.0),
    device_change_prob=0.25,
    location_change_prob=0.20,
    opted_out_prob=0.20,
    amount_deviation_range=(0.10, 0.80),
    failure_code_weights={
        FailureCode.INSUFFICIENT_FUNDS:          0.30,
        FailureCode.EXPIRED_INSTRUMENT:          0.20,
        FailureCode.INVALID_PAYMENT_INSTRUMENT:  0.15,
        FailureCode.PAYMENT_ABANDONED:           0.15,
        FailureCode.AUTHENTICATION_FAILURE:      0.10,
        FailureCode.INVALID_DETAILS:             0.05,
        FailureCode.SUSPICIOUS_PATTERN:          0.05,
    },
)

#
# PREVIOUSLY_RECOVERED_CUSTOMER
# ------------------------------
# Customers who have been through successful recovery before.
# Higher trust in recovery process → lower opt-out.
# Higher recovery success rate (familiar with re-engagement flow).
# Moderate amounts.
#
PREVIOUSLY_RECOVERED_CUSTOMER = CustomerProfile(
    profile_type=CustomerProfileType.PREVIOUSLY_RECOVERED_CUSTOMER,
    amount_range_inr=(500.0, 30_000.0),
    account_age_range_days=(60, 1000),
    prev_transaction_range=(10, 200),
    base_success_rate_range=(0.60, 0.82),
    recovery_success_rate_range=(0.60, 0.90),
    velocity_range=(1.0, 12.0),
    device_change_prob=0.12,
    location_change_prob=0.12,
    opted_out_prob=0.03,
    amount_deviation_range=(0.0, 0.35),
    failure_code_weights={
        FailureCode.NETWORK_TIMEOUT:         0.20,
        FailureCode.GATEWAY_TIMEOUT:         0.15,
        FailureCode.AUTHENTICATION_FAILURE:  0.20,
        FailureCode.PAYMENT_ABANDONED:       0.15,
        FailureCode.INSUFFICIENT_FUNDS:      0.15,
        FailureCode.BANK_UNAVAILABLE:        0.10,
        FailureCode.EXPIRED_INSTRUMENT:      0.05,
    },
)


# =============================================================================
# Registry and Population Weights
# =============================================================================

# Population sampling weights (not uniform — see module docstring)
# Must sum to 1.0
PROFILE_POPULATION_WEIGHTS: Dict[CustomerProfileType, float] = {
    CustomerProfileType.NEW_CUSTOMER:                0.20,
    CustomerProfileType.REGULAR_CUSTOMER:            0.40,
    CustomerProfileType.HIGH_SUCCESS_CUSTOMER:       0.15,
    CustomerProfileType.FAILURE_PRONE_CUSTOMER:      0.15,
    CustomerProfileType.PREVIOUSLY_RECOVERED_CUSTOMER: 0.10,
}

assert abs(sum(PROFILE_POPULATION_WEIGHTS.values()) - 1.0) < 1e-9, (
    "Profile population weights must sum to 1.0"
)

# Registry: CustomerProfileType → CustomerProfile instance
PROFILE_REGISTRY: Dict[CustomerProfileType, CustomerProfile] = {
    CustomerProfileType.NEW_CUSTOMER:                NEW_CUSTOMER,
    CustomerProfileType.REGULAR_CUSTOMER:            REGULAR_CUSTOMER,
    CustomerProfileType.HIGH_SUCCESS_CUSTOMER:       HIGH_SUCCESS_CUSTOMER,
    CustomerProfileType.FAILURE_PRONE_CUSTOMER:      FAILURE_PRONE_CUSTOMER,
    CustomerProfileType.PREVIOUSLY_RECOVERED_CUSTOMER: PREVIOUSLY_RECOVERED_CUSTOMER,
}

# Ordered lists for weighted sampling
PROFILE_TYPES_ORDERED = list(PROFILE_POPULATION_WEIGHTS.keys())
PROFILE_WEIGHTS_ORDERED = [PROFILE_POPULATION_WEIGHTS[p] for p in PROFILE_TYPES_ORDERED]


def get_profile(profile_type: CustomerProfileType) -> CustomerProfile:
    """Return the CustomerProfile for a given profile type."""
    return PROFILE_REGISTRY[profile_type]
