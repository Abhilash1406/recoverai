"""
RecoverAI ML — Simulation Package

Phase 2: Synthetic Data + Recovery Simulation Foundation

This package provides a reproducible simulation environment for evaluating
payment recovery strategies on identical synthetic transaction batches.

IMPORTANT: This is a synthetic research environment. It does NOT call Razorpay,
Gemini, or any external API. It does NOT use real customer data. All transactions
are pseudonymous and generated from parameterised statistical distributions.

Subpackages:
    generator:    Deterministic synthetic transaction generation
    environment:  Ground-truth probabilistic outcome model
    strategies:   Recovery strategy implementations (baseline + contract)
    scoring:      Metric calculations and formulas
    runner:       Experiment orchestration and state machine
    reports:      JSON and Markdown report generation
"""

from ml.src.simulation.config import SimulationConfig  # noqa: F401

__all__ = ["SimulationConfig"]
