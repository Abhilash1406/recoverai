# @recoverai/decision-engine

> **Status: Phase 1 Placeholder — Not Implemented**
>
> This package will be implemented in **Phase 3** of RecoverAI.

## Purpose

The Decision Engine is the core intelligence of RecoverAI. It evaluates candidate recovery actions and selects the one with the highest expected utility, subject to policy constraints.

## Expected Utility Formula

```
ExpectedUtility(transaction, action)
= P(recovery | transaction, action) × transactionValue
  − riskCost
  − customerFrictionCost
  − actionCost
```

Where:
- **P(recovery | transaction, action)** — probability of successful recovery given transaction features and proposed action (ML model output)
- **transactionValue** — transaction amount in paise
- **riskCost** — cost of exposing the system to risk (fraud, chargebacks)
- **customerFrictionCost** — cost of customer experience degradation
- **actionCost** — operational cost of executing the action

## Candidate Actions

| Action | Description |
|--------|-------------|
| `WAIT` | Do nothing; retry naturally later |
| `RETRY` | Immediately retry the payment |
| `PAYMENT_LINK` | Send a fresh payment link to the customer |
| `NOTIFICATION` | Notify customer of failure, prompt re-attempt |
| `MERCHANT_REVIEW` | Escalate to merchant for manual review |
| `STOP` | Cease all recovery attempts |

## Processing Flow (Phase 3+)

```
1. Receive DecisionInput (transaction + risk + candidates)
2. For each candidate action:
   a. Query recovery probability model (ML)
   b. Compute expected utility
   c. Compute costs
3. Rank by expected utility (descending)
4. Pass top action → Policy Engine
5. If policy blocks → try next action
6. Return approved DecisionResult
```

## Files

- `src/index.ts` — Interfaces and placeholder stub

## Implementation Phase

Phase 3 — after:
- Phase 2: MongoDB models + Razorpay sandbox integration
- Phase 3: ML risk + recovery probability models ready
