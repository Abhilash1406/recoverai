# @recoverai/policy-engine

> **Status: Phase 1 Placeholder — Not Implemented**
>
> This package will be implemented in **Phase 3** of RecoverAI.

## Purpose

The Policy Engine is a **deterministic safety gate**. It sits between the Decision Engine (which proposes an action) and the execution layer (which carries it out).

**Key Principle**: AI proposes, policy validates, humans retain final control.

No ML model or AI agent can bypass the Policy Engine.

## Rules (Phase 3+)

| Rule | Description |
|------|-------------|
| `MAX_RETRIES` | Block if retry count ≥ configured maximum |
| `MAX_AUTO_ACTIONS` | Block if total automated actions exceed threshold |
| `HIGH_RISK_BLOCK` | Block automatic actions for CRITICAL risk transactions |
| `PAYMENT_STATE_VALID` | Block if payment is already settled, refunded, or expired |
| `CUSTOMER_OPT_OUT` | Block all actions if customer has opted out |
| `MIN_RECOVERY_PROBABILITY` | Block if ML probability < minimum threshold |
| `HIGH_VALUE_ESCALATION` | Escalate to merchant review if amount > INR 50,000 |
| `STOPPING_RULE` | Permanently stop recovery after N consecutive failures |

## Policy Outcomes

| Outcome | Meaning |
|---------|---------|
| `ALLOW` | Action approved, proceed to execution |
| `BLOCK` | Action rejected, try next-best action |
| `ESCALATE` | Route to merchant for human review |
| `REQUIRE_REVIEW` | Flag for compliance/audit review |

## Design Rationale

The Policy Engine is intentionally **separate** from the Decision Engine because:

1. Policy rules are **deterministic** — no probabilistic reasoning
2. Policy rules can be **audited** easily (no black-box ML)
3. Policy rules can be **changed by product/compliance** without touching ML code
4. Policy rules form a **hard contract** — the AI cannot override them

## Files

- `src/index.ts` — Interfaces, enums, and placeholder stub

## Implementation Phase

Phase 3 — alongside the Decision Engine.
