"""
RecoverAI ML — Training Dataset Generator and Splitter

Generates ML training datasets from synthetic simulation batches and performs
deterministic Train (70%) / Validation (15%) / Test (15%) splits.

DATA SEPARATION PRINCIPLE:
--------------------------
Ground truth probability / environment functions are used ONLY to sample
training target labels (y_risk, y_recovery). The true probability value is
NEVER saved into the feature matrix X.
"""

from typing import List, Tuple, Dict, Any
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from ml.src.simulation.types import (
    SyntheticTransaction,
    RecoveryAction,
    OutcomeType,
    FailureCategory,
)
from ml.src.simulation.generator.transaction_generator import TransactionGenerator
from ml.src.simulation.environment.ground_truth import GroundTruthEnvironment
from ml.src.features.transformer import FeatureTransformer


def generate_ml_datasets(
    seed: int = 42,
    n_transactions: int = 2000,
) -> Dict[str, Any]:
    """
    Generate dataset for both Risk Model and Recovery Model training.

    Parameters
    ----------
    seed : int
        Master random seed.
    n_transactions : int
        Number of synthetic transactions to generate.

    Returns
    -------
    dict
        Contains:
        - 'transactions': List[SyntheticTransaction]
        - 'X_risk': pd.DataFrame
        - 'y_risk': np.ndarray
        - 'X_recovery': pd.DataFrame
        - 'y_recovery': np.ndarray
    """
    gen = TransactionGenerator(seed=seed)
    transactions = gen.generate(n_transactions)

    env = GroundTruthEnvironment(seed=seed + 999)

    # 1. Prepare Risk Dataset
    risk_transformer = FeatureTransformer(include_action=False)
    X_risk = risk_transformer.transform(transactions)

    y_risk_list = []
    for txn in transactions:
        risk_score = env.compute_risk_score(txn)
        # Label 1 if high risk score (>= 0.70) or RISK_RELATED failure
        is_risky = 1 if (risk_score >= 0.70 or txn.failure_category == FailureCategory.RISK_RELATED) else 0
        y_risk_list.append(is_risky)

    y_risk = np.array(y_risk_list, dtype=int)

    # 2. Prepare Recovery Dataset (Transaction-Action pairs)
    rec_transformer = FeatureTransformer(include_action=True)

    candidate_actions = [
        RecoveryAction.RETRY,
        RecoveryAction.PAYMENT_LINK,
        RecoveryAction.NOTIFICATION,
        RecoveryAction.MERCHANT_REVIEW,
    ]

    paired_txns: List[SyntheticTransaction] = []
    paired_actions: List[RecoveryAction] = []
    y_recovery_list: List[int] = []

    for txn in transactions:
        for action in candidate_actions:
            prob, outcome = env.sample_outcome(txn, action, attempt_count=0)
            paired_txns.append(txn)
            paired_actions.append(action)
            is_success = 1 if outcome == OutcomeType.SUCCESS else 0
            y_recovery_list.append(is_success)

    X_recovery = rec_transformer.transform(paired_txns, paired_actions)
    y_recovery = np.array(y_recovery_list, dtype=int)

    return {
        "transactions": transactions,
        "X_risk": X_risk,
        "y_risk": y_risk,
        "X_recovery": X_recovery,
        "y_recovery": y_recovery,
    }


def split_train_val_test(
    X: pd.DataFrame,
    y: np.ndarray,
    seed: int = 42,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray, np.ndarray]:
    """
    Deterministically split X, y into Train (70%), Validation (15%), and Test (15%).

    Returns
    -------
    X_train, X_val, X_test, y_train, y_val, y_test
    """
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-5

    val_test_ratio = val_ratio + test_ratio
    test_size_relative = test_ratio / val_test_ratio

    def _can_stratify(y_arr: np.ndarray) -> bool:
        if len(y_arr) == 0:
            return False
        counts = np.bincount(y_arr)
        return len(counts) > 1 and np.min(counts) >= 2

    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=val_test_ratio, random_state=seed, stratify=y if _can_stratify(y) else None
    )

    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=test_size_relative, random_state=seed, stratify=y_temp if _can_stratify(y_temp) else None
    )

    return X_train, X_val, X_test, y_train, y_val, y_test
