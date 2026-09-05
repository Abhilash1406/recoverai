"""
RecoverAI ML — Training & Evaluation Pipeline

Orchestrates data generation, train/val/test split, risk & recovery model selection,
calibration, and model artifact/metadata serialization.
"""

import os
import json
import datetime
from pathlib import Path
from typing import Dict, Any, Tuple

from ml.src.features.dataset import generate_ml_datasets, split_train_val_test
from ml.src.risk.model import RiskPredictionModel, evaluate_risk_candidate_models
from ml.src.recovery.model import RecoveryPredictionModel, evaluate_recovery_candidate_models


class MLPipeline:
    """
    ML training and evaluation pipeline manager.
    """

    def __init__(self, seed: int = 42, n_transactions: int = 2000) -> None:
        self.seed = seed
        self.n_transactions = n_transactions
        self.risk_model: Optional[RiskPredictionModel] = None
        self.recovery_model: Optional[RecoveryPredictionModel] = None
        self.pipeline_results: Dict[str, Any] = {}

    def run_training_pipeline(self) -> Dict[str, Any]:
        """
        Run dataset generation, model selection, training, calibration,
        and test set evaluation.
        """
        data = generate_ml_datasets(seed=self.seed, n_transactions=self.n_transactions)

        # 1. Risk Model Train/Val/Test
        Xr_train, Xr_val, Xr_test, yr_train, yr_val, yr_test = split_train_val_test(
            data["X_risk"], data["y_risk"], seed=self.seed
        )

        risk_candidates = evaluate_risk_candidate_models(Xr_train, yr_train, Xr_val, yr_val)

        # Select best risk model by ROC-AUC
        best_risk_type = max(risk_candidates, key=lambda k: risk_candidates[k]["roc_auc"])
        self.risk_model = RiskPredictionModel(model_type=best_risk_type)
        self.risk_model.fit(Xr_train, yr_train)
        risk_test_metrics = self.risk_model.evaluate(Xr_test, yr_test)

        # 2. Recovery Model Train/Val/Test
        Xrec_train, Xrec_val, Xrec_test, yrec_train, yrec_val, yrec_test = split_train_val_test(
            data["X_recovery"], data["y_recovery"], seed=self.seed
        )

        recovery_candidates = evaluate_recovery_candidate_models(
            Xrec_train, yrec_train, Xrec_val, yrec_val
        )

        # Select best recovery model by ROC-AUC
        best_rec_type = max(recovery_candidates, key=lambda k: recovery_candidates[k]["roc_auc"])
        self.recovery_model = RecoveryPredictionModel(
            model_type=best_rec_type, calibrate=True, calibration_method="isotonic"
        )
        self.recovery_model.fit(Xrec_train, yrec_train, Xrec_val, yrec_val)
        rec_test_metrics = self.recovery_model.evaluate(Xrec_test, yrec_test)

        pipeline_id = f"ml_pipe_seed{self.seed}_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S')}"

        self.pipeline_results = {
            "pipeline_id": pipeline_id,
            "seed": self.seed,
            "n_transactions": self.n_transactions,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "risk_model": {
                "selected_type": best_risk_type,
                "candidate_val_metrics": risk_candidates,
                "test_metrics": risk_test_metrics,
            },
            "recovery_model": {
                "selected_type": best_rec_type,
                "calibrated": True,
                "calibration_method": "isotonic",
                "candidate_val_metrics": recovery_candidates,
                "test_metrics": rec_test_metrics,
            },
        }

        return self.pipeline_results

    def save_model_evaluation_report(
        self, output_dir: str = "experiments/results"
    ) -> Tuple[Path, Path]:
        """Save machine-readable JSON and Markdown model evaluation reports."""
        if not self.pipeline_results:
            raise RuntimeError("Pipeline must be run before saving reports.")

        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        pid = self.pipeline_results["pipeline_id"]
        json_p = out_path / f"ml_model_evaluation_{pid}.json"
        md_p = out_path / f"ml_model_evaluation_{pid}.md"

        with open(json_p, "w", encoding="utf-8") as f:
            json.dump(self.pipeline_results, f, indent=2)

        md_content = self._generate_md_report()
        with open(md_p, "w", encoding="utf-8") as f:
            f.write(md_content)

        return json_p, md_p

    def _generate_md_report(self) -> str:
        res = self.pipeline_results
        lines = [
            "# RecoverAI ML Model Evaluation Report",
            "",
            f"**Pipeline ID**: `{res['pipeline_id']}`  ",
            f"**Seed**: `{res['seed']}` | **Dataset Size**: `{res['n_transactions']}`  ",
            f"**Generated**: `{res['timestamp']}`  ",
            "",
            "## 1. Risk Prediction Model Selection",
            "",
            f"**Selected Model Architecture**: `{res['risk_model']['selected_type']}`",
            "",
            "### Validation Set Model Comparison",
            "",
            "| Model Architecture | ROC-AUC | PR-AUC | F1 | Brier Score | Log Loss |",
            "|---|---|---|---|---|---|",
        ]

        for mtype, m in res["risk_model"]["candidate_val_metrics"].items():
            lines.append(
                f"| `{mtype}` | {m['roc_auc']:.4f} | {m['pr_auc']:.4f} | {m['f1']:.4f} | {m['brier_score']:.4f} | {m['log_loss']:.4f} |"
            )

        rt = res["risk_model"]["test_metrics"]
        lines.extend([
            "",
            "### Test Set Metrics (Selected Model)",
            f"- **ROC-AUC**: {rt['roc_auc']:.4f}",
            f"- **PR-AUC**: {rt['pr_auc']:.4f}",
            f"- **F1-Score**: {rt['f1']:.4f}",
            f"- **Precision**: {rt['precision']:.4f}",
            f"- **Recall**: {rt['recall']:.4f}",
            f"- **Brier Score**: {rt['brier_score']:.4f}",
            "",
            "## 2. Recovery Probability Model Selection & Calibration",
            "",
            f"**Selected Architecture**: `{res['recovery_model']['selected_type']}` (Calibrated: `isotonic`)",
            "",
            "### Validation Set Model Comparison",
            "",
            "| Model Architecture | ROC-AUC | PR-AUC | F1 | Brier Score | ECE |",
            "|---|---|---|---|---|---|",
        ])

        for mtype, m in res["recovery_model"]["candidate_val_metrics"].items():
            lines.append(
                f"| `{mtype}` | {m['roc_auc']:.4f} | {m['pr_auc']:.4f} | {m['f1']:.4f} | {m['brier_score']:.4f} | {m['ece']:.4f} |"
            )

        rect = res["recovery_model"]["test_metrics"]
        lines.extend([
            "",
            "### Test Set Metrics (Selected Calibrated Model)",
            f"- **ROC-AUC**: {rect['roc_auc']:.4f}",
            f"- **PR-AUC**: {rect['pr_auc']:.4f}",
            f"- **F1-Score**: {rect['f1']:.4f}",
            f"- **Brier Score**: {rect['brier_score']:.4f}",
            f"- **Expected Calibration Error (ECE)**: {rect['ece']:.4f}",
            "",
        ])

        return "\n".join(lines)
