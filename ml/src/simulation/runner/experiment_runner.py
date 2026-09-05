"""
RecoverAI Simulation — Experiment Runner

Orchestrates the full simulation experiment:
    1. Generate a shared synthetic transaction dataset
    2. Run each strategy against the SAME dataset
    3. Collect per-transaction outcomes via the state machine
    4. Calculate aggregate metrics
    5. Return experiment results for report generation

==============================================================================
STATE MACHINE
==============================================================================

Each transaction passes through a bounded state machine:

    FAILED
      ↓
    ANALYZING   ← eligibility + risk score computed
      ↓
    ELIGIBLE    ← or STOPPED (opted-out, BLOCKED)
      ↓
    ACTION_SELECTED  ← strategy.select_action() called
      ↓
    EXECUTING   ← environment.sample_outcome() called
      ↓
    VERIFYING   ← outcome evaluated
      ↓
    RECOVERED   (terminal — payment succeeded)
    RETRY_PENDING  ← outcome was FAILED; check stopping rules
    STOPPED     (terminal — stopping rule triggered)
    MERCHANT_REVIEW (terminal — escalated)

From RETRY_PENDING:
    → ACTION_SELECTED  if retry is allowed (attempt < MAX_AUTOMATIC_ACTIONS)
    → STOPPED          if stopping rule applies

==============================================================================
STOPPING RULES
==============================================================================

A transaction's recovery MUST stop when ANY of the following are true:

Rule SR-1: Payment succeeded → RECOVERED (terminal)
Rule SR-2: attempt_count >= MAX_AUTOMATIC_ACTIONS → STOPPED
Rule SR-3: retry_count >= MAX_RETRIES (if action is RETRY) → STOP substituted
Rule SR-4: customer_opted_out → STOPPED (checked at ANALYZING)
Rule SR-5: risk_score > HIGH_RISK_THRESHOLD → MERCHANT_REVIEW
Rule SR-6: recovery_probability < MIN_RECOVERY_PROBABILITY → STOPPED
Rule SR-7: action == STOP (strategy returned STOP) → STOPPED
Rule SR-8: action == MERCHANT_REVIEW → MERCHANT_REVIEW (terminal)

Rules are checked in this priority order.

==============================================================================
FAIRNESS GUARANTEE
==============================================================================

All strategies receive:
    - The EXACT SAME list of SyntheticTransaction objects (same Python list)
    - The EXACT SAME dataset_hash
    - A SEPARATE GroundTruthEnvironment instance seeded from the same master seed

The environment is seeded deterministically per strategy:
    env_seed = master_seed + strategy_index

This ensures:
    - Each strategy's environment is independent (no cross-contamination)
    - Each strategy's environment is reproducible (same seed → same outcomes)
    - Comparison between strategies is fair (same transactions)

==============================================================================
TIMING SIMULATION
==============================================================================

Time is simulated, not real. Each action advances a simulated clock by
a random duration drawn from the environment. The same seed produces
the same simulated timing. Times are in hours.
"""

import datetime
import uuid
from typing import List, Dict, Optional

from ml.src.simulation.config import SimulationConfig
from ml.src.simulation.types import (
    SyntheticTransaction,
    SimulationOutcome,
    StrategyResult,
    ExperimentResult,
    MultiSeedResult,
    RecoveryState,
    RecoveryAction,
    RecoveryContext,
    OutcomeType,
    TERMINAL_STATES,
)
from ml.src.simulation.generator.transaction_generator import TransactionGenerator
from ml.src.simulation.environment.ground_truth import GroundTruthEnvironment
from ml.src.simulation.strategies.base import RecoveryStrategy
from ml.src.simulation.scoring.metrics import compute_metrics, compute_aggregate_stats


class ExperimentRunner:
    """
    Orchestrates recovery strategy experiments.

    Usage (single seed)
    -------------------
    >>> config = SimulationConfig()
    >>> strategies = [AlwaysRetryStrategy(config), RuleBasedStrategy(config)]
    >>> runner = ExperimentRunner(config)
    >>> result = runner.run_experiment(seed=42, n=1000, strategies=strategies)

    Usage (multi-seed)
    ------------------
    >>> multi = runner.run_multi_seed(
    ...     seeds=[42, 123, 456],
    ...     n=1000,
    ...     strategies=strategies,
    ... )
    """

    def __init__(self, config: Optional[SimulationConfig] = None) -> None:
        self.config = config or SimulationConfig()

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    def generate_dataset(self, seed: int, n: int) -> List[SyntheticTransaction]:
        """
        Generate a deterministic synthetic transaction dataset.

        Parameters
        ----------
        seed : int
            Master seed. Same seed always produces the same dataset.
        n : int
            Number of transactions.

        Returns
        -------
        list[SyntheticTransaction]
        """
        gen = TransactionGenerator(seed=seed)
        return gen.generate(n)

    def run_experiment(
        self,
        seed: int,
        n: int,
        strategies: List[RecoveryStrategy],
    ) -> ExperimentResult:
        """
        Run all strategies on the same dataset.

        Parameters
        ----------
        seed : int
            Master seed.
        n : int
            Dataset size.
        strategies : list[RecoveryStrategy]
            Strategies to evaluate. All run on the same dataset.

        Returns
        -------
        ExperimentResult
        """
        # Generate the shared dataset ONCE
        dataset = self.generate_dataset(seed=seed, n=n)
        dataset_hash = TransactionGenerator.dataset_hash(dataset)

        # Build transaction amount lookup
        tx_amounts = {t.transaction_id: t.amount for t in dataset}

        # Run each strategy
        strategy_results: List[StrategyResult] = []
        for idx, strategy in enumerate(strategies):
            # Each strategy gets its own environment seeded deterministically
            env_seed = seed + idx + 1
            env = GroundTruthEnvironment(seed=env_seed)

            outcomes = self._run_strategy(dataset, strategy, env)
            metrics = compute_metrics(outcomes, tx_amounts)

            strategy_results.append(StrategyResult(
                strategy_name=strategy.name,
                outcomes=outcomes,
                metrics=metrics,
                dataset_hash=dataset_hash,
            ))

        experiment_id = self._make_experiment_id(seed, n)
        config_snapshot = self._config_snapshot()

        return ExperimentResult(
            experiment_id=experiment_id,
            seed=seed,
            dataset_size=n,
            config_snapshot=config_snapshot,
            strategy_results=strategy_results,
            dataset_hash=dataset_hash,
            generated_at=self._now_iso(),
        )

    def run_multi_seed(
        self,
        seeds: List[int],
        n: int,
        strategies: List[RecoveryStrategy],
    ) -> List[MultiSeedResult]:
        """
        Run experiments across multiple seeds and aggregate statistics.

        Parameters
        ----------
        seeds : list[int]
            List of random seeds to use.
        n : int
            Dataset size per seed.
        strategies : list[RecoveryStrategy]
            Strategies to evaluate.

        Returns
        -------
        list[MultiSeedResult]
            One MultiSeedResult per strategy.
        """
        # Collect per-seed metrics for each strategy
        per_strategy_per_seed: Dict[str, List[Dict]] = {
            s.name: [] for s in strategies
        }

        for seed in seeds:
            result = self.run_experiment(seed=seed, n=n, strategies=strategies)
            for sr in result.strategy_results:
                per_strategy_per_seed[sr.strategy_name].append(sr.metrics)

        multi_results: List[MultiSeedResult] = []
        for strategy in strategies:
            per_seed_metrics = per_strategy_per_seed[strategy.name]
            agg = compute_aggregate_stats(per_seed_metrics)
            multi_results.append(MultiSeedResult(
                strategy_name=strategy.name,
                seeds=seeds,
                dataset_size=n,
                per_seed_metrics=per_seed_metrics,
                aggregate_stats=agg,
            ))

        return multi_results

    # ──────────────────────────────────────────────────────────────────────
    # State Machine
    # ──────────────────────────────────────────────────────────────────────

    def _run_strategy(
        self,
        dataset: List[SyntheticTransaction],
        strategy: RecoveryStrategy,
        env: GroundTruthEnvironment,
    ) -> List[SimulationOutcome]:
        """
        Run a strategy against every transaction in the dataset.

        Returns one SimulationOutcome per transaction.
        """
        outcomes: List[SimulationOutcome] = []
        for txn in dataset:
            outcome = self._simulate_transaction(txn, strategy, env)
            outcomes.append(outcome)
        return outcomes

    def _simulate_transaction(
        self,
        txn: SyntheticTransaction,
        strategy: RecoveryStrategy,
        env: GroundTruthEnvironment,
    ) -> SimulationOutcome:
        """
        Run the recovery state machine for one transaction.

        See module docstring for state transition documentation.
        """
        timestamp = self._now_iso()

        # Accumulators
        actions_taken:    List[RecoveryAction] = []
        state_history:    List[RecoveryState]  = [RecoveryState.FAILED]
        attempt_count:    int   = 0
        retry_count:      int   = 0
        total_friction:   float = 0.0
        total_action_c:   float = 0.0
        total_time:       float = 0.0
        policy_violation: bool  = False
        final_prob:       float = 0.0

        # ── ANALYZING ──────────────────────────────────────────────────────
        state_history.append(RecoveryState.ANALYZING)
        risk_score = env.compute_risk_score(txn)

        # SR-4: Customer opted out → BLOCKED immediately
        if txn.customer_opted_out:
            return self._make_outcome(
                txn, strategy.name, actions_taken, final_prob,
                OutcomeType.BLOCKED, 0.0, attempt_count, retry_count,
                total_time, total_friction, total_action_c, 0.0,
                policy_violation,
                state_history + [RecoveryState.STOPPED],
                timestamp,
            )

        # SR-5: High risk → MERCHANT_REVIEW at eligibility check
        if risk_score > self.config.HIGH_RISK_THRESHOLD:
            state_history.append(RecoveryState.MERCHANT_REVIEW)
            return self._make_outcome(
                txn, strategy.name, actions_taken, final_prob,
                OutcomeType.MERCHANT_REVIEW, 0.0, attempt_count, retry_count,
                total_time, total_friction, total_action_c,
                self.config.risk_cost(risk_score, txn.amount),
                policy_violation,
                state_history,
                timestamp,
            )

        # ── ELIGIBLE ───────────────────────────────────────────────────────
        state_history.append(RecoveryState.ELIGIBLE)
        risk_cost_total = self.config.risk_cost(risk_score, txn.amount)

        # Recovery loop — bounded by stopping rules
        while True:
            context = RecoveryContext(
                current_state=RecoveryState.ELIGIBLE,
                attempt_count=attempt_count,
                retry_count=retry_count,
                risk_score=risk_score,
                time_since_first_failure_hours=total_time,
            )

            # ── ACTION_SELECTED ────────────────────────────────────────────
            state_history.append(RecoveryState.ACTION_SELECTED)
            action = strategy.select_action(txn, context)

            # SR-7: Strategy returned STOP
            if action == RecoveryAction.STOP:
                actions_taken.append(action)
                state_history.append(RecoveryState.STOPPED)
                return self._make_outcome(
                    txn, strategy.name, actions_taken, final_prob,
                    OutcomeType.STOPPED, 0.0, attempt_count, retry_count,
                    total_time, total_friction, total_action_c, risk_cost_total,
                    policy_violation, state_history, timestamp,
                )

            # SR-2: Max automatic actions exceeded — substitute STOP
            if attempt_count >= self.config.MAX_AUTOMATIC_ACTIONS:
                state_history.append(RecoveryState.STOPPED)
                return self._make_outcome(
                    txn, strategy.name, actions_taken, final_prob,
                    OutcomeType.STOPPED, 0.0, attempt_count, retry_count,
                    total_time, total_friction, total_action_c, risk_cost_total,
                    policy_violation, state_history, timestamp,
                )

            # SR-3: Max retries exceeded — substitute STOP for RETRY
            if action == RecoveryAction.RETRY and retry_count >= self.config.MAX_RETRIES:
                action = RecoveryAction.STOP
                actions_taken.append(action)
                state_history.append(RecoveryState.STOPPED)
                return self._make_outcome(
                    txn, strategy.name, actions_taken, final_prob,
                    OutcomeType.STOPPED, 0.0, attempt_count, retry_count,
                    total_time, total_friction, total_action_c, risk_cost_total,
                    policy_violation, state_history, timestamp,
                )

            # SR-8: Strategy returned MERCHANT_REVIEW
            if action == RecoveryAction.MERCHANT_REVIEW:
                actions_taken.append(action)
                total_friction += self.config.friction_score(action.value)
                total_action_c += self.config.action_cost(action.value)
                state_history.append(RecoveryState.MERCHANT_REVIEW)
                return self._make_outcome(
                    txn, strategy.name, actions_taken, final_prob,
                    OutcomeType.MERCHANT_REVIEW, 0.0,
                    attempt_count + 1, retry_count,
                    total_time, total_friction, total_action_c, risk_cost_total,
                    policy_violation, state_history, timestamp,
                )

            # ── Check recovery probability BEFORE executing ────────────────
            current_prob = env.compute_recovery_probability(
                txn, action, attempt_count, txn.time_since_last_attempt_hours
            )
            final_prob = current_prob

            # SR-6: Probability below threshold → STOPPED
            if current_prob < self.config.MIN_RECOVERY_PROBABILITY:
                state_history.append(RecoveryState.STOPPED)
                return self._make_outcome(
                    txn, strategy.name, actions_taken, final_prob,
                    OutcomeType.STOPPED, 0.0, attempt_count, retry_count,
                    total_time, total_friction, total_action_c, risk_cost_total,
                    policy_violation, state_history, timestamp,
                )

            # ── EXECUTING ──────────────────────────────────────────────────
            state_history.append(RecoveryState.EXECUTING)
            actions_taken.append(action)

            # Accumulate costs
            total_friction += self.config.friction_score(action.value)
            total_action_c += self.config.action_cost(action.value)
            action_time     = env.simulate_time_to_action_hours(action)
            total_time     += action_time

            if action == RecoveryAction.RETRY:
                retry_count += 1
            attempt_count += 1

            # ── VERIFYING ──────────────────────────────────────────────────
            state_history.append(RecoveryState.VERIFYING)
            prob, outcome_type = env.sample_outcome(
                txn, action, attempt_count - 1,
                txn.time_since_last_attempt_hours
            )
            final_prob = prob

            # SR-1: Payment succeeded → RECOVERED
            if outcome_type == OutcomeType.SUCCESS:
                state_history.append(RecoveryState.RECOVERED)
                return self._make_outcome(
                    txn, strategy.name, actions_taken, final_prob,
                    OutcomeType.SUCCESS, txn.amount, attempt_count, retry_count,
                    total_time, total_friction, total_action_c, risk_cost_total,
                    policy_violation, state_history, timestamp,
                )

            # ── RETRY_PENDING ──────────────────────────────────────────────
            state_history.append(RecoveryState.RETRY_PENDING)

            # Loop again (stopping rules re-checked at top of while)
            # ELIGIBLE state re-appended for next cycle
            state_history.append(RecoveryState.ELIGIBLE)

    # ──────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────

    def _make_outcome(
        self,
        txn: SyntheticTransaction,
        strategy_name: str,
        actions: List[RecoveryAction],
        prob: float,
        outcome: OutcomeType,
        recovered: float,
        attempts: int,
        retries: int,
        time_hrs: float,
        friction: float,
        action_cost: float,
        risk_cost: float,
        policy_violation: bool,
        state_history: List[RecoveryState],
        timestamp: str,
    ) -> SimulationOutcome:
        return SimulationOutcome(
            transaction_id=txn.transaction_id,
            strategy_name=strategy_name,
            selected_actions=list(actions),
            true_recovery_probability=round(prob, 6),
            outcome=outcome,
            recovered_amount=round(recovered, 2),
            attempts=attempts,
            retry_count=retries,
            time_to_recovery_hours=round(time_hrs, 4),
            friction_cost=round(friction, 4),
            action_cost=round(action_cost, 4),
            risk_cost=round(risk_cost, 4),
            policy_violation=policy_violation,
            state_history=list(state_history),
            timestamp=timestamp,
        )

    @staticmethod
    def _make_experiment_id(seed: int, n: int) -> str:
        """Generate a unique but readable experiment ID."""
        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S")
        return f"exp_seed{seed}_n{n}_{ts}"

    @staticmethod
    def _now_iso() -> str:
        return datetime.datetime.now(datetime.timezone.utc).isoformat()

    def _config_snapshot(self) -> dict:
        """Serialize SimulationConfig for report inclusion."""
        return {
            "MAX_AUTOMATIC_ACTIONS":   self.config.MAX_AUTOMATIC_ACTIONS,
            "MAX_RETRIES":             self.config.MAX_RETRIES,
            "HIGH_RISK_THRESHOLD":     self.config.HIGH_RISK_THRESHOLD,
            "MIN_RECOVERY_PROBABILITY": self.config.MIN_RECOVERY_PROBABILITY,
            "RISK_COST_MULTIPLIER":    self.config.RISK_COST_MULTIPLIER,
            "ACTION_COSTS":            self.config.ACTION_COSTS,
            "FRICTION_SCORES":         self.config.FRICTION_SCORES,
        }
