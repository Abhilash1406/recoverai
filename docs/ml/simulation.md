# RecoverAI — Simulation Environment Documentation

> **Razorpay Buildathon 2026 — Track 03: AI Revenue Recovery**
>
> Phase 2: Synthetic Data + Recovery Simulation Foundation

---

> ⚠️ **DISCLAIMER**
>
> The simulation environment is a synthetic research environment and does **not** represent real Razorpay production behavior. All transaction amounts, customer profiles, recovery probabilities, and metrics are simulation parameters only. No real payment data, no real customer data, and no real payment processing occurs anywhere in this codebase.

---

## 1. Why This Simulation Exists

The Razorpay Track 03 judging brief requires:

- Measured money recovered across a batch
- Compliant escalation
- Stopping rules
- Audit trail

To meet these requirements with **defensible, verifiable numbers**, we need a controlled experimental environment that:

1. Generates a **fixed, reproducible** transaction dataset
2. Runs **multiple recovery strategies** on the **exact same dataset**
3. Measures **identical metrics** across all strategies
4. Produces **every reported number from an actual simulation** (no fabrication)

This simulation environment is the foundation. Later phases will train real ML models using simulation-generated data and eventually validate against Razorpay sandbox data.

---

## 2. Dataset Generation

### Generator

**File:** `ml/src/simulation/generator/transaction_generator.py`

The `TransactionGenerator` creates synthetic failed transaction records deterministically using Python's `random.Random(seed)`. All randomness flows from one seeded RNG instance.

**Reproducibility guarantee:**
```python
gen1 = TransactionGenerator(seed=42)
gen2 = TransactionGenerator(seed=42)
assert gen1.generate(1000) == gen2.generate(1000)  # Always True
```

### Transaction Fields

Each synthetic transaction contains 21 fields:

| Field | Type | Description |
|-------|------|-------------|
| `transaction_id` | str | Pseudonymous ID (`txn_<hex>`) |
| `customer_id` | str | Pseudonymous ID (`cust_<hex>`) |
| `amount` | float | Transaction amount in INR |
| `currency` | str | Always `"INR"` |
| `payment_method` | enum | card, upi, netbanking, wallet, emi |
| `failure_category` | enum | TEMPORARY / CUSTOMER_ACTION / HARD_FAILURE / RISK_RELATED |
| `failure_code` | enum | Specific failure code (10 types) |
| `transaction_hour` | int | Hour of day (0–23) |
| `customer_account_age_days` | int | Synthetic account age |
| `previous_transaction_count` | int | Total prior transactions |
| `previous_successful_transactions` | int | Count of prior successes |
| `previous_failed_transactions` | int | Count of prior failures |
| `historical_success_rate` | float | Prior successes / prior total |
| `previous_recovery_success_rate` | float | Recovery success rate (0.0 if no history) |
| `attempt_count` | int | Always 0 at generation time |
| `time_since_last_attempt_hours` | float | Always 0.0 at generation time |
| `transaction_velocity` | float | Transactions per 24 hours |
| `device_changed` | bool | Whether device changed since last transaction |
| `location_changed` | bool | Whether location/IP region changed |
| `amount_deviation` | float | \|amount − avg\| / avg |
| `customer_opted_out` | bool | Whether customer opted out of recovery |

**No PII is generated.** No names, phone numbers, email addresses, card numbers, or real payment credentials exist anywhere.

---

## 3. Customer Profiles

**File:** `ml/src/simulation/generator/profiles.py`

Five customer behavioural profiles influence transaction generation:

### Population Distribution

| Profile | Weight | Rationale |
|---------|--------|-----------|
| `NEW_CUSTOMER` | 20% | First-time or early users |
| `REGULAR_CUSTOMER` | 40% | Core platform user base |
| `HIGH_SUCCESS_CUSTOMER` | 15% | Reliable, established users |
| `FAILURE_PRONE_CUSTOMER` | 15% | Poor instruments or abandonment tendency |
| `PREVIOUSLY_RECOVERED_CUSTOMER` | 10% | Successfully recovered before |

Weights are **intentionally unequal** — equal weights would not reflect real payment platform distributions.

### Profile Characteristics

| Profile | Success Rate | Top Failure Type | Opt-Out Rate | Recovery Rate |
|---------|-------------|------------------|--------------|---------------|
| NEW_CUSTOMER | 50–75% | Authentication failure | 5% | 0% (no history) |
| REGULAR_CUSTOMER | 70–88% | Mixed | 8% | 30–60% |
| HIGH_SUCCESS_CUSTOMER | 88–98% | Network/gateway | 2% | 60–90% |
| FAILURE_PRONE_CUSTOMER | 25–55% | Insufficient funds | 20% | 10–35% |
| PREVIOUSLY_RECOVERED | 60–82% | Mixed | 3% | 60–90% |

**All values are simulation assumptions — not real Razorpay data.**

---

## 4. Failure Taxonomy

**File:** `ml/src/simulation/types.py`

### Categories and Codes

| Category | Code | Meaning |
|----------|------|---------|
| `TEMPORARY` | `network_timeout` | Network layer timeout |
| `TEMPORARY` | `gateway_timeout` | Payment gateway unresponsive |
| `TEMPORARY` | `bank_unavailable` | Issuing bank temporarily down |
| `CUSTOMER_ACTION` | `authentication_failure` | 3DS/OTP failed or timed out |
| `CUSTOMER_ACTION` | `payment_abandoned` | Customer closed payment page |
| `CUSTOMER_ACTION` | `invalid_details` | Incorrect card details |
| `HARD_FAILURE` | `expired_instrument` | Card/UPI/wallet has expired |
| `HARD_FAILURE` | `insufficient_funds` | Insufficient account balance |
| `HARD_FAILURE` | `invalid_payment_instrument` | Instrument blocked or closed |
| `RISK_RELATED` | `suspicious_pattern` | Risk engine flag |

The mapping `FailureCode → FailureCategory` is enforced via `FAILURE_CODE_TO_CATEGORY` (strongly typed dictionary).

---

## 5. Ground-Truth Recovery Environment

**File:** `ml/src/simulation/environment/ground_truth.py`

The `GroundTruthEnvironment` is the simulated world's oracle. It computes the **true recovery probability** for any `(transaction, action)` pair and samples outcomes from it.

**SEPARATION PRINCIPLE:** The ground-truth model must never be imported by any strategy or ML model. Strategies make decisions without access to the ground truth. ML models in Phase 3+ will *learn* to approximate it from observed data.

### Probability Formula

```
p = clamp(
    base × profile_factor × history_factor × recovery_factor
    × attempt_penalty × velocity_penalty × device_penalty
    × location_penalty × deviation_penalty × delay_bonus,
    0.0, 1.0
)
```

#### Step 1 — Base Probability Matrix

| | WAIT | RETRY | PAYMENT_LINK | NOTIFICATION | MERCHANT_REVIEW | STOP |
|---|------|-------|--------------|--------------|-----------------|------|
| TEMPORARY | 0.10 | **0.72** | 0.45 | 0.30 | 0.35 | 0.00 |
| CUSTOMER_ACTION | 0.05 | 0.15 | **0.68** | 0.38 | 0.28 | 0.00 |
| HARD_FAILURE | 0.02 | 0.08 | 0.30 | 0.20 | 0.25 | 0.00 |
| RISK_RELATED | 0.05 | 0.05 | 0.15 | 0.10 | **0.55** | 0.00 |

**Intuition:** RETRY is best for transient failures. PAYMENT_LINK is best when customer re-engagement is needed. MERCHANT_REVIEW is correct for risk-flagged transactions.

#### Steps 2–10 — Contextual Multipliers

| Step | Factor | Formula |
|------|--------|---------|
| Profile | `profile_factor` | HIGH_SUCCESS × 1.20, FAILURE_PRONE × 0.70, etc. |
| History | `history_factor` | `0.6 + 0.8 × historical_success_rate` → [0.60, 1.40] |
| Recovery history | `recovery_factor` | `0.7 + 0.6 × prev_recovery_rate` → [0.70, 1.30] |
| Attempt penalty | `attempt_penalty` | `max(0.40, 1.0 − 0.25 × attempt_count)` |
| Velocity penalty | `velocity_penalty` | `max(0.60, 1.0 − 0.04 × max(0, velocity − 5))` |
| Device change | `device_penalty` | 0.85 if changed, 1.00 otherwise |
| Location change | `location_penalty` | 0.88 if changed, 1.00 otherwise |
| Amount deviation | `deviation_penalty` | `max(0.60, 1.0 − 0.30 × deviation)` |
| Delay bonus | `delay_bonus` | 1.05 for PAYMENT_LINK/NOTIFICATION if delay > 0.5h |

#### Outcome Sampling

```python
outcome = SUCCESS if rng.random() < p else FAILED
```

The same seed + same inputs always produce the same outcome.

---

## 6. Recovery Actions

**File:** `ml/src/simulation/types.py`

| Action | Meaning | Friction | Cost |
|--------|---------|----------|------|
| `WAIT` | Take no action | 0 | 0.0 ACU |
| `RETRY` | Auto-retry payment | 1 | 0.5 ACU |
| `PAYMENT_LINK` | Send customer a new payment link | 3 | 1.0 ACU |
| `NOTIFICATION` | Send customer a reminder | 2 | 0.3 ACU |
| `MERCHANT_REVIEW` | Escalate to merchant | 5 | 2.0 ACU |
| `STOP` | Cease recovery | 0 | 0.0 ACU |

**Friction scores and action costs are simulation assumptions only.** They do not represent real Razorpay operational costs or real customer friction measurements.

---

## 7. Recovery State Machine

**File:** `ml/src/simulation/runner/experiment_runner.py`

```
FAILED
  ↓
ANALYZING     ← Risk score computed; opt-out check
  ↓
ELIGIBLE      ← (or STOPPED if opted-out, MERCHANT_REVIEW if high-risk)
  ↓
ACTION_SELECTED  ← strategy.select_action() called
  ↓
EXECUTING     ← environment.sample_outcome() called
  ↓
VERIFYING     ← outcome evaluated
  ↓
┌─────────────────────────────────────────┐
│ SUCCESS     → RECOVERED (terminal)      │
│ FAILED      → RETRY_PENDING             │
│ STOP action → STOPPED (terminal)        │
│ MR action   → MERCHANT_REVIEW (terminal)│
└─────────────────────────────────────────┘
  ↓ (from RETRY_PENDING)
ELIGIBLE (loop) or STOPPED (terminal)
```

**Terminal states:** `RECOVERED`, `STOPPED`, `MERCHANT_REVIEW`

No strategy can create an infinite loop — the state machine is bounded by `MAX_AUTOMATIC_ACTIONS`.

---

## 8. Stopping Rules

**File:** `ml/src/simulation/runner/experiment_runner.py`

| Rule | Trigger | Outcome |
|------|---------|---------|
| SR-1 | Payment succeeded | RECOVERED |
| SR-2 | `attempt_count >= MAX_AUTOMATIC_ACTIONS` | STOPPED |
| SR-3 | `retry_count >= MAX_RETRIES` + RETRY action | STOP substituted |
| SR-4 | `customer_opted_out == True` | BLOCKED |
| SR-5 | `risk_score > HIGH_RISK_THRESHOLD` | MERCHANT_REVIEW |
| SR-6 | `recovery_probability < MIN_RECOVERY_PROBABILITY` | STOPPED |
| SR-7 | Strategy returns `STOP` | STOPPED |
| SR-8 | Strategy returns `MERCHANT_REVIEW` | MERCHANT_REVIEW |

### Default Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MAX_AUTOMATIC_ACTIONS` | 2 | Max total recovery actions per transaction |
| `MAX_RETRIES` | 2 | Max RETRY actions specifically |
| `HIGH_RISK_THRESHOLD` | 0.70 | Risk score above which escalation is required |
| `MIN_RECOVERY_PROBABILITY` | 0.60 | Below which recovery is stopped |

All are configurable via `SimulationConfig`.

---

## 9. Baseline Strategies

**File:** `ml/src/simulation/strategies/`

### AlwaysRetry

Selects `RETRY` for every eligible transaction. Simple baseline. Performs well on `TEMPORARY` failures, poorly on `HARD_FAILURE` and `CUSTOMER_ACTION`.

### AlwaysPaymentLink

Selects `PAYMENT_LINK` for every eligible transaction. Performs well on `CUSTOMER_ACTION` failures. Higher friction than retry.

### RuleBased

Decision tree with 7 explicitly documented rules (in priority order):

1. `customer_opted_out` → STOP
2. `risk_score > HIGH_RISK_THRESHOLD` → MERCHANT_REVIEW
3. `TEMPORARY` failure → RETRY
4. `CUSTOMER_ACTION` failure → PAYMENT_LINK
5. `HARD_FAILURE`, first attempt → NOTIFICATION
6. `HARD_FAILURE`, subsequent → STOP
7. `RISK_RELATED` → MERCHANT_REVIEW

### RecoverAI (Phase 2 Placeholder)

Returns `STOP` for all transactions. Clearly labelled as a Phase 2 stub. Phase 3+ will implement Expected Utility maximization with a trained ML model.

**Do not interpret Phase 2 RecoverAI results as indicating poor ML performance.**

---

## 10. Metrics

**File:** `ml/src/simulation/scoring/metrics.py`

| Metric | Formula |
|--------|---------|
| `total_transactions` | `len(outcomes)` |
| `successful_recoveries` | `count(outcome == SUCCESS)` |
| `failed_recoveries` | `count(outcome == FAILED)` |
| `stopped_transactions` | `count(outcome == STOPPED)` |
| `merchant_review_transactions` | `count(outcome == MERCHANT_REVIEW)` |
| `revenue_at_risk` | `sum(all transaction amounts)` |
| `eligible_revenue` | `sum(amounts for non-BLOCKED outcomes)` |
| `recovered_revenue` | `sum(recovered_amount for all outcomes)` |
| `recovery_rate` | `successful / eligible_count` |
| `revenue_recovery_efficiency` | `recovered_revenue / eligible_revenue` |
| `average_recovery_attempts` | `sum(attempts) / total` |
| `total_friction_cost` | `sum(friction_cost for all outcomes)` |
| `total_action_cost` | `sum(action_cost for all outcomes)` |
| `total_risk_cost` | `sum(risk_cost for all outcomes)` |
| `safety_violation_count` | `count(policy_violation == True)` |
| `safety_violation_rate` | `safety_violations / total` |
| `net_recovery_value` | `recovered_revenue − risk_cost − friction_cost − action_cost` |

---

## 11. Cost Assumptions

> All cost values are simulation parameters. They do NOT represent real Razorpay operational costs or real industry measurements.

### Action Costs (ACU — Arbitrary Cost Units)

| Action | Cost |
|--------|------|
| WAIT | 0.0 |
| RETRY | 0.5 |
| PAYMENT_LINK | 1.0 |
| NOTIFICATION | 0.3 |
| MERCHANT_REVIEW | 2.0 |
| STOP | 0.0 |

### Friction Scores (FSU — Friction Score Units)

| Action | Score |
|--------|-------|
| WAIT | 0 |
| RETRY | 1 |
| NOTIFICATION | 2 |
| PAYMENT_LINK | 3 |
| MERCHANT_REVIEW | 5 |
| STOP | 0 |

### Risk Cost Formula

```
risk_cost = risk_score × amount × RISK_COST_MULTIPLIER (default: 0.05)
```

Net Recovery Value uses all three cost types:
```
NRV = recovered_revenue − risk_cost − friction_cost − action_cost
```

Note: friction and action costs are in simulation units, not INR. NRV is a composite simulation metric for **comparative** use only.

---

## 12. Reproducibility

The simulation is fully deterministic:

```python
# Always produces identical results:
runner = ExperimentRunner(config=SimulationConfig())
r1 = runner.run_experiment(seed=42, n=1000, strategies=strategies)
r2 = runner.run_experiment(seed=42, n=1000, strategies=strategies)
assert r1.dataset_hash == r2.dataset_hash       # Same dataset
assert r1.strategy_results[0].metrics == r2.strategy_results[0].metrics  # Same metrics
```

### Seed Derivation

- Dataset seed: `master_seed` (e.g., 42)
- Strategy 0 environment seed: `master_seed + 1`
- Strategy 1 environment seed: `master_seed + 2`
- etc.

All strategies run on the **same transaction dataset** but their environments are seeded independently to prevent cross-contamination while maintaining reproducibility.

---

## 13. Experimental Methodology

### Fair Comparison

All strategies receive:
- The **exact same** list of `SyntheticTransaction` objects
- The **same dataset hash** (verified programmatically)
- An independently seeded but reproducible `GroundTruthEnvironment`
- The **same** `SimulationConfig` (stopping rules, costs, friction)

### Multi-Seed Validation

Experiments run across 5 seeds (42, 123, 456, 789, 1001) to:
- Verify results are stable across random variation
- Compute mean / std_dev / min / max for major metrics
- Enable statistically more defensible claims

### What This Phase Does NOT Do

- ❌ Does not call Razorpay
- ❌ Does not call Gemini
- ❌ Does not use real customer data
- ❌ Does not train any ML model
- ❌ Does not fabricate any result

---

## 14. Limitations

1. **Synthetic data only.** The simulation uses parameterised distributions, not real Razorpay transaction data. Real distributions may differ significantly.

2. **Ground-truth model is a parametric assumption.** The probability formula (base matrix + multipliers) was designed to be reasonable, not empirically validated. Future phases will validate against Razorpay sandbox outcomes.

3. **Amount distribution is uniform.** Real payment amounts follow log-normal or power-law distributions. This simplification may affect revenue metrics.

4. **Single-action recovery.** The current simulation applies at most `MAX_AUTOMATIC_ACTIONS` recovery actions per transaction. Real recovery flows may be more complex.

5. **No temporal effects.** Time of day, day of week, and seasonal patterns are not modelled in the ground truth.

6. **RecoverAI is a placeholder.** Phase 2 RecoverAI produces zero recoveries by design. This is intentional — the ML implementation belongs to Phase 3+.

7. **Action costs are assumed.** Real operational costs for SMS, payment link generation, etc., depend on platform-specific pricing that is not available for this simulation.

8. **Risk score is heuristic.** The current risk score is a weighted sum of observable signals, not a trained model. Phase 3+ will replace it with a trained classifier.

---

## Files Reference

| File | Purpose |
|------|---------|
| `ml/src/simulation/config.py` | All configurable parameters |
| `ml/src/simulation/types.py` | All enums and dataclasses |
| `ml/src/simulation/generator/profiles.py` | 5 customer profiles |
| `ml/src/simulation/generator/transaction_generator.py` | Deterministic generator |
| `ml/src/simulation/environment/ground_truth.py` | Ground-truth probability model |
| `ml/src/simulation/strategies/base.py` | Strategy interface |
| `ml/src/simulation/strategies/always_retry.py` | Baseline strategy |
| `ml/src/simulation/strategies/always_payment_link.py` | Baseline strategy |
| `ml/src/simulation/strategies/rule_based.py` | Rule-based strategy |
| `ml/src/simulation/strategies/recoverai_strategy.py` | Phase 3+ contract |
| `ml/src/simulation/scoring/metrics.py` | Metric formulas |
| `ml/src/simulation/runner/experiment_runner.py` | State machine + orchestration |
| `ml/src/simulation/reports/report_generator.py` | JSON + Markdown output |
| `ml/experiments/results/` | Generated experiment reports |
