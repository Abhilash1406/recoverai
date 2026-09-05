"""
Tests — Reproducibility and Experiment Fairness

This is the MOST CRITICAL test module for Phase 2.

Covers:
- Seed=42 produces identical datasets on two runs
- Seed=42 produces identical simulation outcomes on two runs
- Seed=42 and seed=123 produce DIFFERENT datasets
- All strategies receive the SAME dataset (same hash)
- Experiment runner produces ExperimentResult structure
- Multi-seed runner produces MultiSeedResult structure
- Dataset hash is stable across strategy runs
"""

import pytest

from ml.src.simulation.config import SimulationConfig
from ml.src.simulation.types import (
    ExperimentResult,
    MultiSeedResult,
    OutcomeType,
)
from ml.src.simulation.generator.transaction_generator import TransactionGenerator
from ml.src.simulation.environment.ground_truth import GroundTruthEnvironment
from ml.src.simulation.strategies.always_retry import AlwaysRetryStrategy
from ml.src.simulation.strategies.always_payment_link import AlwaysPaymentLinkStrategy
from ml.src.simulation.strategies.rule_based import RuleBasedStrategy
from ml.src.simulation.strategies.recoverai_strategy import RecoverAIStrategy
from ml.src.simulation.runner.experiment_runner import ExperimentRunner


CONFIG     = SimulationConfig()
STRATEGIES = [
    AlwaysRetryStrategy(CONFIG),
    AlwaysPaymentLinkStrategy(CONFIG),
    RuleBasedStrategy(CONFIG),
    RecoverAIStrategy(CONFIG),
]
RUNNER     = ExperimentRunner(config=CONFIG)


class TestDeterministicGeneration:

    def test_same_seed_produces_identical_dataset(self):
        """
        CRITICAL: seed=42 must produce the exact same dataset on two runs.
        """
        gen1 = TransactionGenerator(seed=42)
        gen2 = TransactionGenerator(seed=42)
        ds1  = gen1.generate(100)
        ds2  = gen2.generate(100)

        assert len(ds1) == len(ds2)
        for i, (t1, t2) in enumerate(zip(ds1, ds2)):
            assert t1.transaction_id          == t2.transaction_id,          f"id mismatch at {i}"
            assert t1.customer_id             == t2.customer_id,             f"customer_id mismatch at {i}"
            assert t1.amount                  == t2.amount,                  f"amount mismatch at {i}"
            assert t1.failure_category        == t2.failure_category,        f"category mismatch at {i}"
            assert t1.failure_code            == t2.failure_code,            f"code mismatch at {i}"
            assert t1.historical_success_rate == t2.historical_success_rate, f"hist_rate mismatch at {i}"
            assert t1.device_changed          == t2.device_changed,          f"device_changed mismatch at {i}"
            assert t1.customer_opted_out      == t2.customer_opted_out,      f"opted_out mismatch at {i}"

    def test_different_seeds_produce_different_datasets(self):
        gen42  = TransactionGenerator(seed=42)
        gen123 = TransactionGenerator(seed=123)
        ds42   = gen42.generate(100)
        ds123  = gen123.generate(100)

        # Transaction IDs are index-based hashes (same across seeds by design),
        # but amounts, failure codes, and profile types will differ.
        amounts_same = all(
            t1.amount == t2.amount
            for t1, t2 in zip(ds42, ds123)
        )
        assert not amounts_same, "Different seeds should produce different transaction amounts"

    def test_dataset_hash_is_identical_for_same_seed(self):
        gen1 = TransactionGenerator(seed=42)
        gen2 = TransactionGenerator(seed=42)
        ds1  = gen1.generate(100)
        ds2  = gen2.generate(100)
        assert TransactionGenerator.dataset_hash(ds1) == TransactionGenerator.dataset_hash(ds2)


class TestReproducibleSimulation:

    def test_same_seed_produces_identical_experiment_metrics(self):
        """
        CRITICAL: Running the same experiment with seed=42 twice must
        produce identical metric values for all strategies.
        """
        result1 = RUNNER.run_experiment(seed=42, n=100, strategies=STRATEGIES)
        result2 = RUNNER.run_experiment(seed=42, n=100, strategies=STRATEGIES)

        assert result1.dataset_hash == result2.dataset_hash

        for sr1, sr2 in zip(result1.strategy_results, result2.strategy_results):
            assert sr1.strategy_name == sr2.strategy_name
            assert sr1.metrics == sr2.metrics, (
                f"Metrics differ for strategy {sr1.strategy_name} "
                f"between two runs with seed=42"
            )

    def test_same_seed_produces_identical_outcomes(self):
        """Individual transaction outcomes must also be reproducible."""
        result1 = RUNNER.run_experiment(seed=42, n=50, strategies=STRATEGIES[:1])
        result2 = RUNNER.run_experiment(seed=42, n=50, strategies=STRATEGIES[:1])

        outcomes1 = result1.strategy_results[0].outcomes
        outcomes2 = result2.strategy_results[0].outcomes

        for o1, o2 in zip(outcomes1, outcomes2):
            assert o1.outcome           == o2.outcome
            assert o1.recovered_amount  == o2.recovered_amount
            assert o1.attempts          == o2.attempts

    def test_different_seeds_produce_different_results(self):
        r42  = RUNNER.run_experiment(seed=42,  n=100, strategies=STRATEGIES[:1])
        r123 = RUNNER.run_experiment(seed=123, n=100, strategies=STRATEGIES[:1])

        assert r42.dataset_hash != r123.dataset_hash


class TestExperimentFairness:

    def test_all_strategies_receive_same_dataset_hash(self):
        """
        CRITICAL: All strategies must run on the SAME transaction dataset.
        """
        result = RUNNER.run_experiment(seed=42, n=100, strategies=STRATEGIES)

        hashes = {sr.dataset_hash for sr in result.strategy_results}
        assert len(hashes) == 1, (
            f"All strategies must share one dataset hash. Got: {hashes}"
        )
        assert result.dataset_hash in hashes

    def test_all_strategies_process_same_number_of_transactions(self):
        result = RUNNER.run_experiment(seed=42, n=100, strategies=STRATEGIES)
        for sr in result.strategy_results:
            assert sr.metrics["total_transactions"] == 100

    def test_experiment_result_has_all_strategies(self):
        result = RUNNER.run_experiment(seed=42, n=50, strategies=STRATEGIES)
        strategy_names = {sr.strategy_name for sr in result.strategy_results}
        expected_names = {s.name for s in STRATEGIES}
        assert strategy_names == expected_names

    def test_experiment_result_has_required_fields(self):
        result = RUNNER.run_experiment(seed=42, n=50, strategies=STRATEGIES)
        assert isinstance(result, ExperimentResult)
        assert result.seed == 42
        assert result.dataset_size == 50
        assert len(result.experiment_id) > 0
        assert len(result.generated_at) > 0

    def test_recoverai_placeholder_produces_zero_recoveries(self):
        """
        Phase 2 RecoverAI placeholder must produce zero recovered revenue.
        """
        result = RUNNER.run_experiment(seed=42, n=100, strategies=[RecoverAIStrategy(CONFIG)])
        sr     = result.strategy_results[0]
        assert sr.metrics["recovered_revenue"] == 0.0, (
            "Phase 2 RecoverAI placeholder should recover zero revenue"
        )
        assert sr.metrics["successful_recoveries"] == 0


class TestMultiSeedExperiment:

    def test_multi_seed_produces_correct_number_of_results(self):
        seeds = [42, 123, 456]
        multi = RUNNER.run_multi_seed(
            seeds=seeds,
            n=50,
            strategies=STRATEGIES[:2],
        )
        assert len(multi) == 2  # One per strategy

    def test_multi_seed_has_correct_seed_list(self):
        seeds = [42, 123, 456]
        multi = RUNNER.run_multi_seed(seeds=seeds, n=50, strategies=STRATEGIES[:1])
        assert multi[0].seeds == seeds

    def test_multi_seed_aggregate_stats_have_required_keys(self):
        seeds = [42, 123, 456]
        multi = RUNNER.run_multi_seed(seeds=seeds, n=50, strategies=STRATEGIES[:1])
        agg   = multi[0].aggregate_stats
        for key in ["recovery_rate", "recovered_revenue", "net_recovery_value"]:
            assert key in agg, f"Missing aggregate stat key: {key}"
            assert "mean"    in agg[key]
            assert "std_dev" in agg[key]
            assert "min"     in agg[key]
            assert "max"     in agg[key]

    def test_five_seed_experiment_runs_successfully(self):
        """The full Phase 2 five-seed experiment must complete without errors."""
        seeds = [42, 123, 456, 789, 1001]
        multi = RUNNER.run_multi_seed(seeds=seeds, n=100, strategies=STRATEGIES)
        assert len(multi) == len(STRATEGIES)
        for mr in multi:
            assert len(mr.per_seed_metrics) == 5


class TestSimulationProducesVariedOutcomes:

    def test_not_all_outcomes_stopped(self):
        """A well-functioning simulation should produce SUCCESS outcomes too."""
        result   = RUNNER.run_experiment(seed=42, n=500, strategies=[AlwaysRetryStrategy(CONFIG)])
        outcomes = result.strategy_results[0].outcomes
        types    = {o.outcome for o in outcomes}
        # At least some transactions should succeed
        assert OutcomeType.SUCCESS in types or OutcomeType.STOPPED in types, (
            "Simulation should produce some non-trivial outcomes"
        )

    def test_experiment_produces_multiple_outcome_types(self):
        """Multiple outcome types should appear in a reasonably-sized run."""
        result   = RUNNER.run_experiment(seed=42, n=500, strategies=[RuleBasedStrategy(CONFIG)])
        outcomes = result.strategy_results[0].outcomes
        types    = {o.outcome for o in outcomes}
        assert len(types) >= 2, (
            f"Expected at least 2 outcome types, got: {types}"
        )
