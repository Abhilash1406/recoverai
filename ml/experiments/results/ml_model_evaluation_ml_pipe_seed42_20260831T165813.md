# RecoverAI ML Model Evaluation Report

**Pipeline ID**: `ml_pipe_seed42_20260831T165813`  
**Seed**: `42` | **Dataset Size**: `500`  
**Generated**: `2026-08-31T16:58:13.111137+00:00`  

## 1. Risk Prediction Model Selection

**Selected Model Architecture**: `logistic_regression`

### Validation Set Model Comparison

| Model Architecture | ROC-AUC | PR-AUC | F1 | Brier Score | Log Loss |
|---|---|---|---|---|---|
| `logistic_regression` | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0002 |
| `random_forest` | 0.5000 | 0.0000 | 0.0000 | 0.0002 | 0.0051 |
| `gradient_boosting` | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

### Test Set Metrics (Selected Model)
- **ROC-AUC**: 1.0000
- **PR-AUC**: 1.0000
- **F1-Score**: 1.0000
- **Precision**: 1.0000
- **Recall**: 1.0000
- **Brier Score**: 0.0000

## 2. Recovery Probability Model Selection & Calibration

**Selected Architecture**: `random_forest` (Calibrated: `isotonic`)

### Validation Set Model Comparison

| Model Architecture | ROC-AUC | PR-AUC | F1 | Brier Score | ECE |
|---|---|---|---|---|---|
| `logistic_regression` | 0.8417 | 0.6954 | 0.6092 | 0.1470 | 0.0617 |
| `random_forest` | 0.8599 | 0.7409 | 0.6333 | 0.1356 | 0.0676 |
| `gradient_boosting` | 0.8540 | 0.7220 | 0.6310 | 0.1409 | 0.0326 |

### Test Set Metrics (Selected Calibrated Model)
- **ROC-AUC**: 0.8540
- **PR-AUC**: 0.6923
- **F1-Score**: 0.6519
- **Brier Score**: 0.1412
- **Expected Calibration Error (ECE)**: 0.0521
