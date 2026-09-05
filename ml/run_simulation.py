"""
RecoverAI Phase 3 — Simulation & ML Decision Engine Execution Script

Trains the Risk & Recovery ML models, runs the strategy comparison benchmark
(AlwaysRetry, AlwaysPaymentLink, RuleBased, RecoverAI), verifies reproducibility,
and exports single-seed & multi-seed experiment reports.

Usage:
    python run_simulation.py
"""

import json
import sys
import os

# Add repo root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ml.src.simulation.config import SimulationConfig
from ml.src.simulation.strategies.always_retry import AlwaysRetryStrategy
from ml.src.simulation.strategies.always_payment_link import AlwaysPaymentLinkStrategy
from ml.src.simulation.strategies.rule_based import RuleBasedStrategy
from ml.src.simulation.strategies.recoverai_strategy import RecoverAIStrategy
from ml.src.simulation.runner.experiment_runner import ExperimentRunner
from ml.src.simulation.reports.report_generator import ReportGenerator
from ml.src.evaluation.pipeline import MLPipeline


def fmt(n, decimals=2):
    if isinstance(n, float):
        return f"{n:,.{decimals}f}"
    return str(n)


def print_strategy_summary(sr):
    m = sr.metrics
    print(f"  Strategy: {sr.strategy_name}")
    print(f"    Recovery Rate:         {m['recovery_rate']:.2%}")
    print(f"    Recovered Revenue:     INR {m['recovered_revenue']:>12,.2f}")
    print(f"    Rev Recovery Effic.:   {m['revenue_recovery_efficiency']:.2%}")
    print(f"    Net Recovery Value:    INR {m['net_recovery_value']:>12,.2f}")
    print(f"    Successful Recoveries: {m['successful_recoveries']}")
    print(f"    Stopped Transactions:  {m['stopped_transactions']}")
    print(f"    Merchant Review:       {m['merchant_review_transactions']}")
    print(f"    Avg Attempts:          {m['average_recovery_attempts']:.3f}")
    print(f"    Safety Violations:     {m['safety_violation_count']}")
    print()


def main():
    print("=" * 60)
    print("PHASE 3 — TRAINING ML DECISION MODELS")
    print("=" * 60)
    
    # Train ML models
    ml_pipe = MLPipeline(seed=42, n_transactions=500)
    pipe_results = ml_pipe.run_training_pipeline()
    json_ml, md_ml = ml_pipe.save_model_evaluation_report()

    print(f"Selected Risk Model:     {pipe_results['risk_model']['selected_type']} (Test ROC-AUC: {pipe_results['risk_model']['test_metrics']['roc_auc']:.4f})")
    print(f"Selected Recovery Model: {pipe_results['recovery_model']['selected_type']} (Test ECE: {pipe_results['recovery_model']['test_metrics']['ece']:.4f})")
    print(f"ML Model Report JSON:    {json_ml}")
    print(f"ML Model Report MD:      {md_ml}")
    print()

    config = SimulationConfig()
    strategies = [
        AlwaysRetryStrategy(config),
        AlwaysPaymentLinkStrategy(config),
        RuleBasedStrategy(config),
        RecoverAIStrategy(config, risk_model=ml_pipe.risk_model, recovery_model=ml_pipe.recovery_model),
    ]
    runner   = ExperimentRunner(config=config)
    reporter = ReportGenerator(output_dir="experiments/results")

    # ─── Seed 42 — Run 1 ──────────────────────────────────────────────────
    print("=" * 60)
    print("RUN 1 — seed=42, n=1000")
    print("=" * 60)
    r1 = runner.run_experiment(seed=42, n=1000, strategies=strategies)
    print(f"Experiment ID:   {r1.experiment_id}")
    print(f"Dataset Hash:    {r1.dataset_hash[:24]}...")
    print()
    for sr in r1.strategy_results:
        print_strategy_summary(sr)

    # ─── Seed 42 — Run 2 ──────────────────────────────────────────────────
    print("=" * 60)
    print("RUN 2 — seed=42, n=1000 (reproducibility check)")
    print("=" * 60)
    r2 = runner.run_experiment(seed=42, n=1000, strategies=strategies)
    print(f"Experiment ID:   {r2.experiment_id}")
    print(f"Dataset Hash:    {r2.dataset_hash[:24]}...")
    print()

    # ─── Reproducibility Verification ─────────────────────────────────────
    print("=" * 60)
    print("REPRODUCIBILITY VERIFICATION")
    print("=" * 60)
    dataset_match = r1.dataset_hash == r2.dataset_hash
    print(f"Dataset hash match: {'[PASS] IDENTICAL' if dataset_match else '[FAIL] DIFFERENT'}")

    all_metrics_match = True
    for sr1, sr2 in zip(r1.strategy_results, r2.strategy_results):
        match = sr1.metrics == sr2.metrics
        if not match:
            all_metrics_match = False
        print(f"  {sr1.strategy_name}: {'[PASS] IDENTICAL' if match else '[FAIL] DIFFERENT'}")

    print(f"\nOverall reproducibility: {'[PASS]' if (dataset_match and all_metrics_match) else '[FAIL]'}")
    print()

    # ─── Save Reports for Run 1 ───────────────────────────────────────────
    json_p, md_p = reporter.save_experiment(r1)
    print(f"JSON report: {json_p}")
    print(f"MD report:   {md_p}")
    print()

    # ─── Multi-Seed Experiment ─────────────────────────────────────────────
    print("=" * 60)
    print("MULTI-SEED EXPERIMENT — seeds=[42,123,456,789,1001], n=1000")
    print("=" * 60)
    seeds = [42, 123, 456, 789, 1001]
    multi = runner.run_multi_seed(seeds=seeds, n=1000, strategies=strategies)

    for mr in multi:
        print(f"Strategy: {mr.strategy_name}")
        agg = mr.aggregate_stats
        for key in ["recovery_rate", "recovered_revenue", "net_recovery_value"]:
            a = agg.get(key, {})
            print(f"  {key:<30} mean={a.get('mean',0):.4f}  "
                  f"std={a.get('std_dev',0):.4f}  "
                  f"min={a.get('min',0):.4f}  "
                  f"max={a.get('max',0):.4f}")
        print()

    # Save multi-seed report
    mj, mm = reporter.save_multi_seed(multi, seeds=seeds, n=1000)
    print(f"Multi-seed JSON: {mj}")
    print(f"Multi-seed MD:   {mm}")
    print()

    print("=" * 60)
    print("PHASE 3 DECISION ENGINE SIMULATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
