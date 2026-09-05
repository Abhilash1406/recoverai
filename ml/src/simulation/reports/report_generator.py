"""
RecoverAI Simulation — Report Generator

Generates machine-readable JSON and human-readable Markdown reports
from ExperimentResult and MultiSeedResult objects.

All reported numbers come directly from simulation outcomes.
No numbers are fabricated or estimated.

Output paths:
    experiments/results/<experiment-id>.json
    experiments/results/<experiment-id>.md
    experiments/results/multiseed_<timestamp>.json
    experiments/results/multiseed_<timestamp>.md
"""

import json
import os
import datetime
from pathlib import Path
from typing import List, Optional

from ml.src.simulation.types import (
    ExperimentResult,
    MultiSeedResult,
    StrategyResult,
)


DISCLAIMER = (
    "The simulation environment is a synthetic research environment and does not "
    "represent real Razorpay production behavior. All transaction amounts, costs, "
    "and metrics are simulation parameters only."
)

COST_DISCLAIMER = (
    "Action costs and friction scores are simulation parameters (not real Razorpay "
    "costs). Risk cost formula: risk_score × amount × 0.05. All values are "
    "assumptions for fair comparative evaluation."
)


class ReportGenerator:
    """
    Generates JSON and Markdown reports from simulation results.

    Parameters
    ----------
    output_dir : str | Path
        Directory where reports are written.
        Created automatically if it does not exist.
    """

    def __init__(self, output_dir: str | Path = "experiments/results") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ──────────────────────────────────────────────────────────────────────
    # Single-experiment reports
    # ──────────────────────────────────────────────────────────────────────

    def save_experiment(self, result: ExperimentResult) -> tuple[Path, Path]:
        """
        Save JSON and Markdown reports for a single experiment.

        Parameters
        ----------
        result : ExperimentResult

        Returns
        -------
        tuple[Path, Path]
            (json_path, markdown_path)
        """
        eid = result.experiment_id
        json_path = self.output_dir / f"{eid}.json"
        md_path   = self.output_dir / f"{eid}.md"

        # JSON — machine-readable
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self._experiment_to_dict(result), f, indent=2)

        # Markdown — human-readable
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(self._experiment_to_markdown(result))

        return json_path, md_path

    def save_multi_seed(
        self,
        multi_results: List[MultiSeedResult],
        seeds: List[int],
        n: int,
        label: str = "",
    ) -> tuple[Path, Path]:
        """
        Save JSON and Markdown reports for a multi-seed experiment.

        Parameters
        ----------
        multi_results : list[MultiSeedResult]
        seeds : list[int]
        n : int
        label : str
            Optional label for the filename.

        Returns
        -------
        tuple[Path, Path]
            (json_path, markdown_path)
        """
        ts   = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        stem = f"multiseed_{ts}" if not label else f"multiseed_{label}_{ts}"

        json_path = self.output_dir / f"{stem}.json"
        md_path   = self.output_dir / f"{stem}.md"

        data = {
            "report_type":  "multi_seed",
            "seeds":        seeds,
            "dataset_size": n,
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "disclaimer":   DISCLAIMER,
            "cost_disclaimer": COST_DISCLAIMER,
            "strategies": [r.to_dict() for r in multi_results],
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(self._multi_seed_to_markdown(multi_results, seeds, n, ts))

        return json_path, md_path

    # ──────────────────────────────────────────────────────────────────────
    # Serialization helpers
    # ──────────────────────────────────────────────────────────────────────

    def _experiment_to_dict(self, result: ExperimentResult) -> dict:
        data = result.to_dict()
        data["disclaimer"]      = DISCLAIMER
        data["cost_disclaimer"] = COST_DISCLAIMER
        return data

    # ──────────────────────────────────────────────────────────────────────
    # Markdown generation
    # ──────────────────────────────────────────────────────────────────────

    def _experiment_to_markdown(self, result: ExperimentResult) -> str:
        lines = [
            f"# RecoverAI Simulation Report",
            f"",
            f"> {DISCLAIMER}",
            f"",
            f"## Experiment Summary",
            f"",
            f"| Field | Value |",
            f"|-------|-------|",
            f"| Experiment ID | `{result.experiment_id}` |",
            f"| Seed | `{result.seed}` |",
            f"| Dataset Size | `{result.dataset_size}` transactions |",
            f"| Dataset Hash | `{result.dataset_hash[:16]}...` |",
            f"| Generated At | `{result.generated_at}` |",
            f"",
            f"## Simulation Configuration",
            f"",
            f"| Parameter | Value |",
            f"|-----------|-------|",
        ]
        for k, v in result.config_snapshot.items():
            if isinstance(v, dict):
                lines.append(f"| {k} | *(see JSON)* |")
            else:
                lines.append(f"| {k} | `{v}` |")

        lines += [
            f"",
            f"> {COST_DISCLAIMER}",
            f"",
            f"## Strategy Results",
            f"",
        ]

        for sr in result.strategy_results:
            lines += self._strategy_section(sr)

        lines += [
            f"",
            f"## Strategy Comparison",
            f"",
        ]
        lines += self._comparison_table(result.strategy_results)

        lines += [
            f"",
            f"## Limitations",
            f"",
            f"- Amounts and outcomes are synthetic — not real Razorpay data.",
            f"- Ground-truth model is a documented parametric simulation.",
            f"- RecoverAI ML strategy is a Phase 2 placeholder (returns STOP).",
            f"- Action costs and friction are simulation assumptions.",
            f"- Stopping rules are configurable; defaults are conservative.",
            f"",
        ]
        return "\n".join(lines)

    def _strategy_section(self, sr: StrategyResult) -> List[str]:
        m = sr.metrics
        lines = [
            f"### {sr.strategy_name}",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Transactions | {m.get('total_transactions', 0)} |",
            f"| Successful Recoveries | {m.get('successful_recoveries', 0)} |",
            f"| Failed Recoveries | {m.get('failed_recoveries', 0)} |",
            f"| Stopped Transactions | {m.get('stopped_transactions', 0)} |",
            f"| Merchant Review | {m.get('merchant_review_transactions', 0)} |",
            f"| Blocked Transactions | {m.get('blocked_transactions', 0)} |",
            f"| Recovery Rate | {m.get('recovery_rate', 0):.2%} |",
            f"| Revenue at Risk | ₹{m.get('revenue_at_risk', 0):,.2f} |",
            f"| Eligible Revenue | ₹{m.get('eligible_revenue', 0):,.2f} |",
            f"| Recovered Revenue | ₹{m.get('recovered_revenue', 0):,.2f} |",
            f"| Revenue Recovery Efficiency | {m.get('revenue_recovery_efficiency', 0):.2%} |",
            f"| Avg Recovery Attempts | {m.get('average_recovery_attempts', 0):.3f} |",
            f"| Total Friction Cost | {m.get('total_friction_cost', 0):.2f} FSU |",
            f"| Total Action Cost | {m.get('total_action_cost', 0):.2f} ACU |",
            f"| Total Risk Cost | ₹{m.get('total_risk_cost', 0):,.2f} (sim) |",
            f"| Net Recovery Value | ₹{m.get('net_recovery_value', 0):,.2f} (sim) |",
            f"| Safety Violations | {m.get('safety_violation_count', 0)} |",
            f"",
        ]
        return lines

    def _comparison_table(self, strategy_results: List[StrategyResult]) -> List[str]:
        if not strategy_results:
            return []
        # Header
        header = "| Metric |" + "".join(f" {sr.strategy_name} |" for sr in strategy_results)
        sep    = "|--------|" + "".join(" --------- |" for _ in strategy_results)
        lines  = [header, sep]

        key_metrics = [
            ("Recovery Rate",           "recovery_rate",                  ".2%"),
            ("Recovered Revenue (INR)", "recovered_revenue",              ",.2f"),
            ("Rev Recovery Efficiency", "revenue_recovery_efficiency",    ".2%"),
            ("Net Recovery Value",      "net_recovery_value",             ",.2f"),
            ("Avg Attempts",            "average_recovery_attempts",      ".3f"),
            ("Safety Violations",       "safety_violation_count",         "d"),
            ("Stopped Transactions",    "stopped_transactions",           "d"),
            ("Merchant Review",         "merchant_review_transactions",   "d"),
        ]
        for label, key, fmt in key_metrics:
            row = f"| {label} |"
            for sr in strategy_results:
                val = sr.metrics.get(key, 0)
                try:
                    if fmt == "d":
                        row += f" {val:d} |"
                    elif "%" in fmt:
                        row += f" {val:{fmt}} |"
                    else:
                        row += f" {val:{fmt}} |"
                except (ValueError, TypeError):
                    row += f" {val} |"
            lines.append(row)
        return lines

    def _multi_seed_to_markdown(
        self,
        multi_results: List[MultiSeedResult],
        seeds: List[int],
        n: int,
        ts: str,
    ) -> str:
        seed_str = ", ".join(str(s) for s in seeds)
        lines = [
            f"# RecoverAI Multi-Seed Experiment Report",
            f"",
            f"> {DISCLAIMER}",
            f"",
            f"## Configuration",
            f"",
            f"| Field | Value |",
            f"|-------|-------|",
            f"| Seeds | `{seed_str}` |",
            f"| Dataset Size (per seed) | `{n}` |",
            f"| Generated At | `{ts}` |",
            f"",
            f"## Aggregate Statistics by Strategy",
            f"",
            f"Statistics computed over {len(seeds)} seeds.",
            f"",
        ]

        key_metrics = [
            ("Recovery Rate",        "recovery_rate"),
            ("Recovered Revenue",    "recovered_revenue"),
            ("Rev Recovery Effic.",  "revenue_recovery_efficiency"),
            ("Net Recovery Value",   "net_recovery_value"),
            ("Avg Attempts",         "average_recovery_attempts"),
            ("Stopped Transactions", "stopped_transactions"),
            ("Safety Violations",    "safety_violation_count"),
        ]

        for mr in multi_results:
            lines += [f"### {mr.strategy_name}", f"", f"| Metric | Mean | Std Dev | Min | Max |",
                      f"|--------|------|---------|-----|-----|"]
            for label, key in key_metrics:
                agg = mr.aggregate_stats.get(key, {})
                mean  = agg.get("mean", 0)
                std   = agg.get("std_dev", 0)
                mn    = agg.get("min", 0)
                mx    = agg.get("max", 0)
                lines.append(f"| {label} | {mean:.4f} | {std:.4f} | {mn:.4f} | {mx:.4f} |")
            lines.append("")

        lines += [
            f"## Limitations",
            f"",
            f"- RecoverAI ML strategy is a Phase 2 placeholder (returns STOP).",
            f"- All metrics are synthetic simulation values.",
            f"- Standard deviation across seeds reflects environment randomness.",
            f"",
        ]
        return "\n".join(lines)
