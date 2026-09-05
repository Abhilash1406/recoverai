"""
RecoverAI ML — Feature Engineering

Provides FeatureTransformer for converting synthetic transactions
and candidate recovery actions into numeric feature vectors for ML models.

DATA LEAKAGE PREVENTION:
-------------------------
This transformer strictly excludes all future outcome fields:
- true_recovery_probability / trueRecoveryProbability
- outcome / outcome_type
- recovered_amount / recoveredAmount
- state_history / future attempts

Only transaction state known BEFORE action execution is used.
"""

from typing import List, Dict, Any, Optional, Union
import numpy as np
import pandas as pd

from ml.src.simulation.types import (
    SyntheticTransaction,
    RecoveryAction,
    FailureCategory,
    FailureCode,
    CustomerProfileType,
    PaymentMethod,
)

# Explicit target leakage blocklist for verification
LEAKAGE_FIELD_BLOCKLIST = {
    "true_recovery_probability",
    "trueRecoveryProbability",
    "outcome",
    "recovered_amount",
    "recoveredAmount",
    "state_history",
    "policy_violation",
}


class FeatureTransformer:
    """
    Transforms SyntheticTransaction objects into ML-ready pandas DataFrames
    or NumPy arrays.

    Supports transforming:
    1. Transaction features only (used for Risk Model)
    2. Transaction + Action pair features (used for Recovery Model)

    Feature names are deterministic and fixed.
    """

    CATEGORICAL_COLUMNS = {
        "failure_category": [c.value for c in FailureCategory],
        "failure_code": [c.value for c in FailureCode],
        "payment_method": [m.value for m in PaymentMethod],
        "profile_type": [p.value for p in CustomerProfileType],
    }

    ACTION_VALUES = [a.value for a in RecoveryAction]

    def __init__(self, include_action: bool = False) -> None:
        self.include_action = include_action
        self._feature_names: List[str] = self._build_feature_names()

    def _build_feature_names(self) -> List[str]:
        names = [
            "amount",
            "transaction_hour",
            "customer_account_age_days",
            "previous_transaction_count",
            "previous_successful_transactions",
            "previous_failed_transactions",
            "historical_success_rate",
            "previous_recovery_success_rate",
            "attempt_count",
            "time_since_last_attempt_hours",
            "transaction_velocity",
            "device_changed",
            "location_changed",
            "amount_deviation",
            "customer_opted_out",
        ]

        # One-hot categorical columns
        for col, categories in self.CATEGORICAL_COLUMNS.items():
            for cat in categories:
                names.append(f"{col}_{cat}")

        if self.include_action:
            for act in self.ACTION_VALUES:
                names.append(f"action_{act}")

        return names

    @property
    def feature_names(self) -> List[str]:
        return list(self._feature_names)

    def fit(self, X: Any = None, y: Any = None) -> "FeatureTransformer":
        """Stateless transformer for standard encodings, fit returns self."""
        return self

    def fit_transform(
        self,
        transactions: List[SyntheticTransaction],
        actions: Optional[List[RecoveryAction]] = None,
    ) -> pd.DataFrame:
        self.fit()
        return self.transform(transactions, actions)

    def transform(
        self,
        transactions: List[SyntheticTransaction],
        actions: Optional[List[RecoveryAction]] = None,
    ) -> pd.DataFrame:
        """
        Transform a list of SyntheticTransactions (and optional actions)
        into a DataFrame of numerical features.
        """
        if self.include_action:
            if actions is None or len(actions) != len(transactions):
                raise ValueError(
                    "actions list of matching length required when include_action=True"
                )

        rows = []
        for idx, txn in enumerate(transactions):
            action = actions[idx] if self.include_action and actions else None
            row_dict = self._transform_one(txn, action)
            rows.append(row_dict)

        df = pd.DataFrame(rows, columns=self._feature_names)
        df = df.fillna(0.0)

        # Assert no leakage fields in generated columns
        for leakage_col in LEAKAGE_FIELD_BLOCKLIST:
            assert leakage_col not in df.columns, (
                f"Data leakage detected! Leakage column '{leakage_col}' found in features."
            )

        return df

    def transform_single(
        self,
        transaction: SyntheticTransaction,
        action: Optional[RecoveryAction] = None,
    ) -> pd.DataFrame:
        """Convenience method for transforming a single transaction."""
        actions = [action] if self.include_action and action is not None else None
        return self.transform([transaction], actions)

    def _transform_one(
        self,
        txn: SyntheticTransaction,
        action: Optional[RecoveryAction] = None,
    ) -> Dict[str, Union[float, int]]:
        row: Dict[str, Union[float, int]] = {
            "amount": float(txn.amount),
            "transaction_hour": float(txn.transaction_hour),
            "customer_account_age_days": float(txn.customer_account_age_days),
            "previous_transaction_count": float(txn.previous_transaction_count),
            "previous_successful_transactions": float(txn.previous_successful_transactions),
            "previous_failed_transactions": float(txn.previous_failed_transactions),
            "historical_success_rate": float(txn.historical_success_rate),
            "previous_recovery_success_rate": float(txn.previous_recovery_success_rate),
            "attempt_count": float(txn.attempt_count),
            "time_since_last_attempt_hours": float(txn.time_since_last_attempt_hours),
            "transaction_velocity": float(txn.transaction_velocity),
            "device_changed": 1.0 if txn.device_changed else 0.0,
            "location_changed": 1.0 if txn.location_changed else 0.0,
            "amount_deviation": float(txn.amount_deviation),
            "customer_opted_out": 1.0 if txn.customer_opted_out else 0.0,
        }

        # One-hot categoricals
        cat_values = {
            "failure_category": txn.failure_category.value,
            "failure_code": txn.failure_code.value,
            "payment_method": txn.payment_method.value,
            "profile_type": txn.profile_type.value,
        }

        for col, categories in self.CATEGORICAL_COLUMNS.items():
            val = cat_values[col]
            for cat in categories:
                row[f"{col}_{cat}"] = 1.0 if val == cat else 0.0

        if self.include_action:
            act_val = action.value if action else ""
            for act in self.ACTION_VALUES:
                row[f"action_{act}"] = 1.0 if act_val == act else 0.0

        return row
