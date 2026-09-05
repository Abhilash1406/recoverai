"""
RecoverAI ML — Recovery Probability Model & Probability Calibration

Predicts P(recovery | transaction, action) for candidate actions, with probability
calibration (isotonic or Platt scaling) to ensure output probabilities accurately
reflect actual recovery rates.

DATA / LOGIC INVARIANTS:
- RecoveryAction.STOP always returns 0.0 probability.
- Probability predictions are strictly clamped to [0.0, 1.0].
"""

from typing import Dict, Any, Optional, List, Tuple
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    precision_score,
    recall_score,
    f1_score,
    brier_score_loss,
    log_loss,
)

from ml.src.simulation.types import SyntheticTransaction, RecoveryAction
from ml.src.features.transformer import FeatureTransformer


from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

class RecoveryPredictionModel:
    """
    Model for estimating P(recovery | transaction, action).
    Includes optional probability calibration (Platt scaling / sigmoid or isotonic).
    """

    def __init__(
        self,
        model_type: str = "gradient_boosting",
        calibrate: bool = True,
        calibration_method: str = "isotonic",
    ) -> None:
        self.model_type = model_type
        self.calibrate = calibrate
        self.calibration_method = calibration_method
        self.transformer = FeatureTransformer(include_action=True)

        self.base_model = self._create_base_model(model_type)
        self._fitted_model: Any = None
        self.is_fitted = False

    def _create_base_model(self, model_type: str) -> Any:
        if model_type == "logistic_regression":
            return make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, random_state=42))
        elif model_type == "random_forest":
            return RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)
        elif model_type == "gradient_boosting":
            return GradientBoostingClassifier(n_estimators=100, max_depth=4, random_state=42)
        else:
            raise ValueError(f"Unknown model_type: {model_type}")

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: np.ndarray,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[np.ndarray] = None,
    ) -> "RecoveryPredictionModel":
        """
        Fit the base model, and optionally calibrate using validation data or CV.
        """
        if self.calibrate:
            calibrated = CalibratedClassifierCV(
                estimator=self.base_model,
                method=self.calibration_method,
                cv=5,
            )
            calibrated.fit(X_train, y_train)
            self._fitted_model = calibrated
        else:
            self.base_model.fit(X_train, y_train)
            self._fitted_model = self.base_model

        self.is_fitted = True
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Return probability of positive recovery (class 1)."""
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted yet.")
        probas = self._fitted_model.predict_proba(X)
        if probas.shape[1] == 1:
            return np.zeros(len(X))
        return np.clip(probas[:, 1], 0.0, 1.0)

    def predict_action_recovery_probability(
        self,
        transaction: SyntheticTransaction,
        action: RecoveryAction,
    ) -> float:
        """
        Predict P(recovery | transaction, action) for a single action.

        SPECIAL RULE: STOP action always yields 0.0 probability.
        """
        if action == RecoveryAction.STOP:
            return 0.0

        X_single = self.transformer.transform_single(transaction, action)
        prob = float(self.predict_proba(X_single)[0])
        return max(0.0, min(1.0, prob))

    def predict_all_action_probabilities(
        self,
        transaction: SyntheticTransaction,
        actions: Optional[List[RecoveryAction]] = None,
    ) -> Dict[RecoveryAction, float]:
        """
        Predict recovery probabilities for all specified actions in a single batch.
        """
        if actions is None:
            actions = list(RecoveryAction)

        # Batch transform all actions for this transaction at once
        non_stop_actions = [a for a in actions if a != RecoveryAction.STOP]
        
        results: Dict[RecoveryAction, float] = {RecoveryAction.STOP: 0.0}

        if non_stop_actions:
            txns = [transaction] * len(non_stop_actions)
            X_batch = self.transformer.transform(txns, non_stop_actions)
            probs = self.predict_proba(X_batch)
            for idx, act in enumerate(non_stop_actions):
                results[act] = max(0.0, min(1.0, float(probs[idx])))

        return results

    def evaluate(self, X_val: pd.DataFrame, y_val: np.ndarray) -> Dict[str, float]:
        """Compute evaluation metrics and calibration error on validation/test data."""
        y_prob = self.predict_proba(X_val)
        y_pred = (y_prob >= 0.50).astype(int)

        roc_auc = float(roc_auc_score(y_val, y_prob)) if len(np.unique(y_val)) > 1 else 0.5
        pr_auc = float(average_precision_score(y_val, y_prob)) if len(np.unique(y_val)) > 1 else 0.0
        prec = float(precision_score(y_val, y_pred, zero_division=0))
        rec = float(recall_score(y_val, y_pred, zero_division=0))
        f1 = float(f1_score(y_val, y_pred, zero_division=0))
        brier = float(brier_score_loss(y_val, y_prob))
        ll = float(log_loss(y_val, y_prob, labels=[0, 1]))

        # Expected Calibration Error (ECE) estimation with 10 bins
        prob_true, prob_pred = calibration_curve(y_val, y_prob, n_bins=10, strategy="uniform")
        ece = float(np.mean(np.abs(prob_true - prob_pred))) if len(prob_true) > 0 else 0.0

        return {
            "roc_auc": round(roc_auc, 6),
            "pr_auc": round(pr_auc, 6),
            "precision": round(prec, 6),
            "recall": round(rec, 6),
            "f1": round(f1, 6),
            "brier_score": round(brier, 6),
            "log_loss": round(ll, 6),
            "ece": round(ece, 6),
        }


def evaluate_recovery_candidate_models(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_val: pd.DataFrame,
    y_val: np.ndarray,
) -> Dict[str, Dict[str, float]]:
    """
    Train and evaluate all candidate recovery models on validation set
    with calibration metrics.
    """
    candidate_types = ["logistic_regression", "random_forest", "gradient_boosting"]
    results: Dict[str, Dict[str, float]] = {}

    for model_type in candidate_types:
        model = RecoveryPredictionModel(
            model_type=model_type, calibrate=True, calibration_method="isotonic"
        )
        model.fit(X_train, y_train, X_val, y_val)
        metrics = model.evaluate(X_val, y_val)
        results[model_type] = metrics

    return results
