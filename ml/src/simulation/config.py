"""
RecoverAI Simulation — Configuration

Single source of truth for all simulation parameters.

IMPORTANT: These are simulation parameters only. They do NOT represent
real Razorpay operational costs, real fraud rates, or real industry metrics.
All values are documented assumptions used for fair comparative evaluation.

To override defaults, construct SimulationConfig with explicit keyword arguments.
Do NOT scatter magic numbers throughout the simulation code — always reference
this config.
"""

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class SimulationConfig:
    """
    All configurable parameters for the recovery simulation environment.

    Stopping Rules
    --------------
    MAX_AUTOMATIC_ACTIONS : int
        Maximum number of automated recovery actions per transaction before
        forcing a STOP or MERCHANT_REVIEW. Prevents infinite retry loops.
    MAX_RETRIES : int
        Maximum number of RETRY actions specifically. A subset of
        MAX_AUTOMATIC_ACTIONS.
    HIGH_RISK_THRESHOLD : float
        If the computed risk score (0.0–1.0) exceeds this threshold, the
        transaction is escalated to MERCHANT_REVIEW rather than automated action.
    MIN_RECOVERY_PROBABILITY : float
        If the ground-truth recovery probability falls below this threshold,
        the strategy must STOP rather than incurring further cost.

    Action Costs
    ------------
    Simulation parameters representing the operational cost of each recovery
    action. These are ASSUMPTIONS for fair comparative evaluation.
    They do NOT represent real Razorpay costs.

    Units: arbitrary cost units (ACU). Net Recovery Value is in INR minus ACU,
    so all amounts should be interpreted relatively, not absolutely.

    Action Cost Assumptions (ACU per action):
        WAIT            : 0.0  — passive, no cost
        RETRY           : 0.5  — minimal automated cost
        PAYMENT_LINK    : 1.0  — link generation and delivery overhead
        NOTIFICATION    : 0.3  — notification delivery cost
        MERCHANT_REVIEW : 2.0  — human review time cost
        STOP            : 0.0  — no cost to stop

    Friction Scores
    ---------------
    Simulation assumptions representing customer experience friction for each
    action. These are NOT real-world industry measurements.

    Friction Score Assumptions (0 = no friction, higher = more friction):
        WAIT            : 0   — customer experiences nothing
        RETRY           : 1   — minor friction (automatic, transparent)
        NOTIFICATION    : 2   — customer receives a message
        PAYMENT_LINK    : 3   — customer must take active action
        MERCHANT_REVIEW : 5   — customer may experience delay / confusion
        STOP            : 0   — no further friction after stopping

    Risk Cost
    ---------
    Risk cost represents the expected downside of executing a risky automated
    action on a suspicious transaction.

    Formula:
        riskCost = risk_score × amount × RISK_COST_MULTIPLIER

    Where:
        risk_score       is 0.0–1.0 (computed from transaction features)
        amount           is the transaction amount in INR
        RISK_COST_MULTIPLIER is a configurable simulation parameter

    This is a simplified linear model. Real risk cost modelling would require
    fraud data that is not available in this synthetic environment.
    """

    # ------------------------------------------------------------------
    # Stopping rules
    # ------------------------------------------------------------------
    MAX_AUTOMATIC_ACTIONS: int = 2
    MAX_RETRIES: int = 2
    HIGH_RISK_THRESHOLD: float = 0.70      # risk_score > 0.70 → merchant review
    MIN_RECOVERY_PROBABILITY: float = 0.60  # prob < 0.60 → must STOP

    # ------------------------------------------------------------------
    # Action costs (ACU — see class docstring for assumptions)
    # ------------------------------------------------------------------
    ACTION_COSTS: Dict[str, float] = field(default_factory=lambda: {
        "WAIT":            0.0,
        "RETRY":           0.5,
        "PAYMENT_LINK":    1.0,
        "NOTIFICATION":    0.3,
        "MERCHANT_REVIEW": 2.0,
        "STOP":            0.0,
    })

    # ------------------------------------------------------------------
    # Customer friction scores (see class docstring for assumptions)
    # ------------------------------------------------------------------
    FRICTION_SCORES: Dict[str, float] = field(default_factory=lambda: {
        "WAIT":            0.0,
        "RETRY":           1.0,
        "NOTIFICATION":    2.0,
        "PAYMENT_LINK":    3.0,
        "MERCHANT_REVIEW": 5.0,
        "STOP":            0.0,
    })

    # ------------------------------------------------------------------
    # Risk cost model (see class docstring for formula)
    # ------------------------------------------------------------------
    RISK_COST_MULTIPLIER: float = 0.05

    # ------------------------------------------------------------------
    # Dataset generation defaults
    # ------------------------------------------------------------------
    DEFAULT_DATASET_SIZE: int = 1000
    DEFAULT_SEED: int = 42

    # ------------------------------------------------------------------
    # Multi-seed experiment defaults
    # ------------------------------------------------------------------
    MULTI_SEED_SEEDS: tuple = (42, 123, 456, 789, 1001)

    def action_cost(self, action_name: str) -> float:
        """Return the cost for a given action name string."""
        return self.ACTION_COSTS.get(action_name, 0.0)

    def friction_score(self, action_name: str) -> float:
        """Return the friction score for a given action name string."""
        return self.FRICTION_SCORES.get(action_name, 0.0)

    def risk_cost(self, risk_score: float, amount: float) -> float:
        """
        Compute the risk cost for an automated action.

        Formula: risk_score × amount × RISK_COST_MULTIPLIER

        Parameters
        ----------
        risk_score : float
            Transaction risk score in [0.0, 1.0].
        amount : float
            Transaction amount in INR.

        Returns
        -------
        float
            Risk cost in INR-equivalent units.
        """
        return risk_score * amount * self.RISK_COST_MULTIPLIER
