# RecoverAI — Architecture Documentation

> **Razorpay Buildathon 2026 — Track 03: AI Revenue Recovery**

---

## 1. Product Purpose

RecoverAI is a **Risk-Aware Autonomous Revenue Recovery & Decision Engine**.

It detects payment failures, diagnoses their root cause, assesses transaction risk, estimates recovery probability, evaluates candidate recovery actions, and executes the highest-value action that passes deterministic safety constraints — while maintaining a full audit trail.

**Core Innovation**: RecoverAI treats payment recovery as a **constrained decision-optimization problem**, not a rules-based retry loop.

---

## 2. Track 03 Alignment

Track brief: *"Find revenue that's slipping away and win it back."*

RecoverAI addresses this by:

| Capability | How RecoverAI addresses it |
|-----------|---------------------------|
| Find revenue at risk | ML risk model scores every failed transaction |
| Diagnose the problem | Failure category classification |
| Determine the right intervention | Expected utility decision engine |
| Execute recovery | Bounded AI agent with policy gate |
| Measure money recovered | Per-transaction audit trail |
| Compliant escalation | Deterministic policy engine |
| Stopping rules | Policy engine MAX_RETRIES + STOPPING_RULE |
| Audit trail | Immutable decision + action log |

---

## 3. High-Level Architecture

```
Payment Failure
      │
      ▼
Verify Current Payment State        ← Razorpay API (Phase 3+)
      │
      ▼
Diagnose Failure                    ← Rule-based classifier
      │
      ▼
Assess Transaction Risk             ← ML Risk Model (Phase 3+)
      │
      ▼
Estimate Recovery Probability       ← ML Recovery Model (Phase 3+)
      │
      ▼
Evaluate Recovery Actions           ← Decision Engine (Phase 3+)
      │
      ▼
Expected-Utility Decision Engine    ← packages/decision-engine
      │
      ▼
Deterministic Safety / Policy Gate  ← packages/policy-engine
      │
      ▼
Bounded AI Agent                    ← Gemini-backed (Phase 4+)
      │
      ▼
Execute Approved Recovery Action    ← Razorpay API (Phase 3+)
      │
      ▼
Verify Payment Outcome              ← Razorpay Webhook (Phase 3+)
      │
      ▼
Measure Revenue Recovered           ← Analytics service
      │
      ▼
Audit Trail + Analytics             ← MongoDB (Phase 2+)
      │
      ▼
Model Feedback                      ← ML retraining loop (Phase 4+)
```

---

## 4. Frontend (`apps/web`)

- **Framework**: React 18 + Vite + TypeScript
- **Styling**: Tailwind CSS
- **Routing**: React Router v6
- **State**: Zustand (Phase 2+)
- **API client**: Axios / Fetch wrapper (Phase 2+)

**Planned pages**:

| Route | Purpose |
|-------|---------|
| `/` | Landing/overview |
| `/dashboard` | Recovery KPI dashboard |
| `/transactions` | Transaction list + failure details |
| `/recovery` | Active recovery workflows |
| `/risk` | Risk assessment explorer |
| `/decisions` | Decision history |
| `/audit` | Immutable audit log |
| `/analytics` | Revenue recovered analytics |
| `/settings` | Configuration |

---

## 5. Backend (`apps/api`)

- **Runtime**: Node.js 22
- **Framework**: Express 4 + TypeScript
- **API versioning**: `/api/v1/...`
- **Middleware**: CORS, JSON body parsing, request logger, error handler
- **Planned**: MongoDB via Mongoose (Phase 2), Auth (Phase 2), Razorpay webhooks (Phase 3)

**Current endpoints**:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/health` | Service health check |

---

## 6. ML Layer (`ml/`)

- **Language**: Python 3.10+
- **Models under evaluation**: Logistic Regression (baseline), Random Forest, XGBoost
- **Training data**: Synthetic (Phase 3), Razorpay sandbox (Phase 4+)

Two models will be trained:

1. **Risk Model** → `RiskLevel` + `risk_score` (0–1)
2. **Recovery Probability Model** → `P(recovery | transaction, action)` per action

---

## 7. Decision Engine (`packages/decision-engine`)

The Decision Engine scores each candidate recovery action using the Expected Utility formula:

```
EU(transaction, action)
= P(recovery | transaction, action) × transactionValue
  − riskCost
  − customerFrictionCost
  − actionCost
```

It returns a ranked list of `ScoredAction` objects and passes the top action to the Policy Engine.

**Status**: Phase 1 placeholder. Interfaces defined. No logic implemented.

---

## 8. Policy Engine (`packages/policy-engine`)

The Policy Engine is a **deterministic safety gate** that enforces hard business rules. It runs after the Decision Engine proposes an action. No AI model can override it.

**Rules** (Phase 3+):
- MAX_RETRIES
- MAX_AUTO_ACTIONS
- HIGH_RISK_BLOCK
- PAYMENT_STATE_VALID
- CUSTOMER_OPT_OUT
- MIN_RECOVERY_PROBABILITY
- HIGH_VALUE_ESCALATION
- STOPPING_RULE

**Status**: Phase 1 placeholder. Rule names defined. No logic implemented.

---

## 9. Future AI Agent (Phase 4+)

The Bounded AI Agent will:
- Be powered by Gemini
- Operate through a **limited, pre-approved tool set** only
- Never have direct database or payment API authority
- Every tool call must pass through the Policy Engine
- All actions are logged to the audit trail

The agent is bounded by design — it cannot take actions outside its defined tool set.

---

## 10. Future Razorpay Integration (Phase 3+)

- **Mode**: Test mode only during all development phases
- **Never** use production credentials in development
- Credentials stored in environment variables only (never source code)
- Webhook signature verification required
- All payment state transitions verified against Razorpay before action

---

## 11. Security Principles

1. No hard-coded secrets — ever
2. `.env` never committed to Git
3. Backend secrets never exposed to frontend
4. Strict TypeScript throughout
5. Environment variables validated at startup
6. Centralized error handling — no raw stack traces in production
7. All AI agent actions pass through deterministic policy controls
8. No real customer PII in development
9. No unrestricted AI tools — every tool is scoped and bounded

---

## 12. Development Phases

| Phase | Focus | Status |
|-------|-------|--------|
| **1** | Repository + Engineering Foundation | ✅ Current |
| **2** | MongoDB Models + API Endpoints + Auth | ⏳ Pending |
| **3** | Razorpay Sandbox + Synthetic Data + ML Training | ⏳ Pending |
| **4** | Decision Engine + Policy Engine + Gemini Agent | ⏳ Pending |
| **5** | Full Recovery Pipeline + Audit Trail + Analytics | ⏳ Pending |
| **6** | Evaluation + Benchmarks + Buildathon submission | ⏳ Pending |

> **Phase 1 is foundation only.** No business logic, no real integrations, no ML training.
> The codebase must compile, lint cleanly, and pass basic tests before Phase 2 begins.
