"""
RecoverAI ML — Risk Prediction Model

Evaluates candidate classifiers (LogisticRegression, RandomForest, GradientBoosting)
and selects/fits the best model for predicting transaction risk probability
and categorising RiskLevel (LOW, MEDIUM, HIGH, CRITICAL).
"""

from typing import Dict, Any, Optional, Tuple, List
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    precision_score,
    recall_score,
    f1_score,
    brier_score_loss,
    log_loss,
)

from ml.src.simulation.types import RiskLevel, SyntheticTransaction
from ml.src.simulation.config import SimulationConfig
from ml.src.features.transformer import FeatureTransformer


from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

class RiskPredictionModel:
    """
    ML model for predicting transaction risk probability in [0.0, 1.0]
    and categorising RiskLevel.

    Thresholds (configurable):
    - LOW      : < 0.30
    - MEDIUM   : < 0.60
    - HIGH     : < 0.80
    - CRITICAL : >= 0.80
    """

    def __init__(
        self,
        low_threshold: float = 0.30,
        medium_threshold: float = 0.60,
        high_threshold: float = 0.80,
        model_type: str = "gradient_boosting",
    ) -> None:
        self.low_threshold = low_threshold
        self.medium_threshold = medium_threshold
        self.high_threshold = high_threshold
        self.model_type = model_type
        self.transformer = FeatureTransformer(include_action=False)

        self._model = self._create_base_model(model_type)
        self.is_fitted = False
        self.metadata: Dict[str, Any] = {}

    def _create_base_model(self, model_type: str) -> Any:
        if model_type == "logistic_regression":
            return make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, random_state=42))
        elif model_type == "random_forest":
            return RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)
        elif model_type == "gradient_boosting":
            return GradientBoostingClassifier(n_estimators=100, max_depth=4, random_state=42)
        else:
            raise ValueError(f"Unknown model_type: {model_type}")

    def fit(self, X_train: pd.DataFrame, y_train: np.ndarray) -> "RiskPredictionModel":
        self._model.fit(X_train, y_train)
        self.is_fitted = True
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Return probability of high risk class (1)."""
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted yet.")
        probas = self._model.predict_proba(X)
        if probas.shape[1] == 1:
            return np.zeros(len(X))
        return probas[:, 1]

    def predict_risk_score(self, transaction: SyntheticTransaction) -> float:
        """Predict risk score for a single SyntheticTransaction."""
        X_single = self.transformer.transform_single(transaction)
        prob = float(self.predict_proba(X_single)[0])
        return max(0.0, min(1.0, prob))

    def predict_risk_scores_batch(self, transactions: List[SyntheticTransaction]) -> np.ndarray:
        """Predict risk scores for a list of SyntheticTransactions in batch."""
        X_batch = self.transformer.transform(transactions)
        probs = self.predict_proba(X_batch)
        return np.clip(probs, 0.0, 1.0)

    def categorize_risk_level(self, risk_score: float) -> RiskLevel:
        """
        Categorise risk score into RiskLevel enum based on configured thresholds.
        """
        if risk_score < self.low_threshold:
            return RiskLevel.LOW
        elif risk_score < self.medium_threshold:
            return RiskLevel.MEDIUM
        elif risk_score < self.high_threshold:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    def evaluate(self, X_val: pd.DataFrame, y_val: np.ndarray) -> Dict[str, float]:
        """Compute evaluation metrics on validation/test set."""
        y_prob = self.predict_proba(X_val)
        y_pred = (y_prob >= 0.50).astype(int)

        roc_auc = float(roc_auc_score(y_val, y_prob)) if len(np.unique(y_val)) > 1 else 0.5
        pr_auc = float(average_precision_score(y_val, y_prob)) if len(np.unique(y_val)) > 1 else 0.0
        prec = float(precision_score(y_val, y_pred, zero_division=0))
        rec = float(recall_score(y_val, y_pred, zero_division=0))
        f1 = float(f1_score(y_val, y_pred, zero_division=0))
        brier = float(brier_score_loss(y_val, y_prob))
        ll = float(log_loss(y_val, y_prob, labels=[0, 1]))

        return {
            "roc_auc": round(roc_auc, 6),
            "pr_auc": round(pr_auc, 6),
            "precision": round(prec, 6),
            "recall": round(rec, 6),
            "f1": round(f1, 6),
            "brier_score": round(brier, 6),
            "log_loss": round(ll, 6),
        }


def evaluate_risk_candidate_models(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_val: pd.DataFrame,
    y_val: np.ndarray,
) -> Dict[str, Dict[str, float]]:
    """
    Train and evaluate all candidate risk models on validation set.
    """
    candidate_types = ["logistic_regression", "random_forest", "gradient_boosting"]
    results: Dict[str, Dict[str, float]] = {}

    for model_type in candidate_types:
        model = RiskPredictionModel(model_type=model_type)
        model.fit(X_train, y_train)
        metrics = model.evaluate(X_val, y_val)
        results[model_type] = metrics

    return results
