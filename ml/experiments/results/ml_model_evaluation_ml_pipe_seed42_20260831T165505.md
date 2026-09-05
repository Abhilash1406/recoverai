# RecoverAI ML Model Evaluation Report

**Pipeline ID**: `ml_pipe_seed42_20260831T165505`  
**Seed**: `42` | **Dataset Size**: `2000`  
**Generated**: `2026-08-31T16:55:05.202562+00:00`  

## 1. Risk Prediction Model Selection

**Selected Model Architecture**: `logistic_regression`

### Validation Set Model Comparison

| Model Architecture | ROC-AUC | PR-AUC | F1 | Brier Score | Log Loss |
|---|---|---|---|---|---|
| `logistic_regression` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0002 |
| `random_forest` | 1.0000 | 1.0000 | 1.0000 | 0.0004 | 0.0028 |
| `gradient_boosting` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |

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
| `logistic_regression` | 0.8397 | 0.6432 | 0.6214 | 0.1486 | 0.0391 |
| `random_forest` | 0.8573 | 0.7043 | 0.6486 | 0.1398 | 0.0469 |
| `gradient_boosting` | 0.8568 | 0.7022 | 0.6239 | 0.1411 | 0.0495 |

### Test Set Metrics (Selected Calibrated Model)
- **ROC-AUC**: 0.8717
- **PR-AUC**: 0.7641
- **F1-Score**: 0.6694
- **Brier Score**: 0.1316
- **Expected Calibration Error (ECE)**: 0.0342
