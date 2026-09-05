"""
RecoverAI ML — Tests for Feature Transformer, Risk & Recovery Models, and ML Pipeline

Covers:
- FeatureTransformer correctness and Data Leakage Prevention
- RiskPredictionModel fitting, predicting, and evaluation
- RecoveryPredictionModel fitting, predicting, calibration, and STOP rule
- MLPipeline training and evaluation report generation
"""

import pytest
import numpy as np
import pandas as pd

from ml.src.simulation.config import SimulationConfig
from ml.src.simulation.types import (
    SyntheticTransaction,
    RecoveryAction,
    FailureCategory,
    FailureCode,
    PaymentMethod,
    CustomerProfileType,
    RiskLevel,
)
from ml.src.features.transformer import FeatureTransformer, LEAKAGE_FIELD_BLOCKLIST
from ml.src.features.dataset import generate_ml_datasets, split_train_val_test
from ml.src.risk.model import RiskPredictionModel, evaluate_risk_candidate_models
from ml.src.recovery.model import RecoveryPredictionModel, evaluate_recovery_candidate_models
from ml.src.evaluation.pipeline import MLPipeline


def _make_txn(**overrides) -> SyntheticTransaction:
    defaults = dict(
        transaction_id="txn_ml_test",
        customer_id="cust_ml_test",
        amount=4000.0,
        currency="INR",
        payment_method=PaymentMethod.CARD,
        failure_category=FailureCategory.TEMPORARY,
        failure_code=FailureCode.NETWORK_TIMEOUT,
        transaction_hour=14,
        customer_account_age_days=180,
        previous_transaction_count=25,
        previous_successful_transactions=20,
        previous_failed_transactions=5,
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


# =============================================================================
# Feature Transformer & Leakage Prevention Tests
# =============================================================================

class TestFeatureTransformer:

    def test_transform_returns_dataframe_with_expected_columns(self):
        ft = FeatureTransformer(include_action=False)
        txn = _make_txn()
        df = ft.transform([txn])
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert list(df.columns) == ft.feature_names

    def test_include_action_feature(self):
        ft = FeatureTransformer(include_action=True)
        txn = _make_txn()
        df = ft.transform([txn], [RecoveryAction.RETRY])
        assert "action_RETRY" in df.columns
        assert df["action_RETRY"].iloc[0] == 1.0
        assert df["action_PAYMENT_LINK"].iloc[0] == 0.0

    def test_data_leakage_prevention_assertion(self):
        """CRITICAL: Ensure no leakage attributes exist in features DataFrame."""
        ft = FeatureTransformer(include_action=True)
        txn = _make_txn()
        df = ft.transform([txn], [RecoveryAction.RETRY])
        for leakage_col in LEAKAGE_FIELD_BLOCKLIST:
            assert leakage_col not in df.columns, f"Leakage column {leakage_col} found in features!"


# =============================================================================
# Dataset Splitter Tests
# =============================================================================

class TestDatasetSplitter:

    def test_dataset_generation_and_70_15_15_split(self):
        data = generate_ml_datasets(seed=42, n_transactions=200)
        assert "X_risk" in data
        assert "y_risk" in data
        assert len(data["X_risk"]) == 200

        Xr_tr, Xr_val, Xr_te, yr_tr, yr_val, yr_te = split_train_val_test(
            data["X_risk"], data["y_risk"], seed=42
        )
        total = len(data["X_risk"])
        assert len(Xr_tr) == int(total * 0.70)
        assert len(Xr_val) == int(total * 0.15)
        assert len(Xr_te) == total - len(Xr_tr) - len(Xr_val)


# =============================================================================
# Risk Prediction Model Tests
# =============================================================================

class TestRiskPredictionModel:

    def test_fit_and_predict_risk(self):
        data = generate_ml_datasets(seed=42, n_transactions=200)
        Xr_tr, Xr_val, Xr_te, yr_tr, yr_val, yr_te = split_train_val_test(
            data["X_risk"], data["y_risk"], seed=42
        )
        model = RiskPredictionModel(model_type="random_forest")
        model.fit(Xr_tr, yr_tr)

        txn = _make_txn()
        risk_score = model.predict_risk_score(txn)
        assert 0.0 <= risk_score <= 1.0

        risk_level = model.categorize_risk_level(risk_score)
        assert isinstance(risk_level, RiskLevel)

    def test_risk_candidate_evaluation(self):
        data = generate_ml_datasets(seed=42, n_transactions=200)
        Xr_tr, Xr_val, Xr_te, yr_tr, yr_val, yr_te = split_train_val_test(
            data["X_risk"], data["y_risk"], seed=42
        )
        results = evaluate_risk_candidate_models(Xr_tr, yr_tr, Xr_val, yr_val)
        assert "logistic_regression" in results
        assert "random_forest" in results
        assert "gradient_boosting" in results
        assert "roc_auc" in results["gradient_boosting"]


# =============================================================================
# Recovery Prediction Model Tests
# =============================================================================

class TestRecoveryPredictionModel:

    def test_fit_predict_and_stop_action_rule(self):
        data = generate_ml_datasets(seed=42, n_transactions=100)
        Xrec_tr, Xrec_val, Xrec_te, yrec_tr, yrec_val, yrec_te = split_train_val_test(
            data["X_recovery"], data["y_recovery"], seed=42
        )
        model = RecoveryPredictionModel(model_type="gradient_boosting", calibrate=True)
        model.fit(Xrec_tr, yrec_tr, Xrec_val, yrec_val)

        txn = _make_txn()
        p_retry = model.predict_action_recovery_probability(txn, RecoveryAction.RETRY)
        assert 0.0 <= p_retry <= 1.0

        p_stop = model.predict_action_recovery_probability(txn, RecoveryAction.STOP)
        assert p_stop == 0.0, "STOP action must always yield 0.0 recovery probability"

    def test_recovery_candidate_evaluation(self):
        data = generate_ml_datasets(seed=42, n_transactions=100)
        Xrec_tr, Xrec_val, Xrec_te, yrec_tr, yrec_val, yrec_te = split_train_val_test(
            data["X_recovery"], data["y_recovery"], seed=42
        )
        results = evaluate_recovery_candidate_models(Xrec_tr, yrec_tr, Xrec_val, yrec_val)
        assert "gradient_boosting" in results
        assert "ece" in results["gradient_boosting"]


# =============================================================================
# ML Pipeline End-to-End Test
# =============================================================================

class TestMLPipeline:

    def test_pipeline_runs_and_saves_reports(self, tmp_path):
        pipe = MLPipeline(seed=42, n_transactions=200)
        res = pipe.run_training_pipeline()
        assert "risk_model" in res
        assert "recovery_model" in res

        json_p, md_p = pipe.save_model_evaluation_report(output_dir=str(tmp_path))
        assert json_p.exists()
        assert md_p.exists()
