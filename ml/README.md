# RecoverAI ML

> **Status: Phase 1 — Structure only. No models trained.**

## Overview

The RecoverAI ML layer provides two core capabilities (Phase 3+):

1. **Risk Assessment** — classifies failed transactions by risk level
2. **Recovery Probability Estimation** — estimates P(recovery | transaction, action)

## Directory Structure

```
ml/
├── data/
│   ├── raw/           # Raw data (never committed to Git)
│   ├── processed/     # Cleaned, feature-engineered data
│   └── synthetic/     # Synthetic transactions for training
├── models/            # Trained model artifacts (.pkl, .joblib)
├── notebooks/         # Exploratory analysis and prototyping
├── src/
│   ├── features/      # Feature engineering pipeline
│   ├── risk/          # Risk assessment model
│   ├── recovery/      # Recovery probability model
│   └── evaluation/    # Model evaluation and simulation
└── tests/
    └── test_environment.py
```

## ML Architecture (Phase 3+)

```
Raw Transaction Data
        ↓
Feature Engineering (src/features/)
        ↓
  ┌─────┴─────┐
  │           │
Risk Model  Recovery Probability Model
(src/risk/) (src/recovery/)
  │           │
  └─────┬─────┘
        ↓
Decision Engine (packages/decision-engine/)
```

## Models Under Evaluation

| Model | Purpose | Phase |
|-------|---------|-------|
| Logistic Regression | Risk baseline | 3 |
| Random Forest | Risk + recovery | 3 |
| XGBoost | Primary candidate | 3 |

## Setup

```bash
cd ml
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
pytest
```

## Phase Roadmap

| Phase | Milestone |
|-------|-----------|
| 1 | Structure and environment test only |
| 2 | Feature engineering design |
| 3 | Synthetic data generation + model training |
| 4 | Real Razorpay data integration |
| 5 | Online learning + continuous evaluation |
