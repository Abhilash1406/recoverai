# RecoverAI

**Risk-Aware Autonomous Revenue Recovery & Decision Engine**

> Razorpay Buildathon 2026 — Track 03: AI Revenue Recovery

---

## What is RecoverAI?

RecoverAI detects payment failures, diagnoses root causes, assesses risk, estimates recovery probability, and executes the highest-value recovery action that satisfies deterministic safety constraints — with a full audit trail.

**Core Innovation**: Payment recovery as a constrained decision-optimization problem.

```
EU(transaction, action)
= P(recovery | transaction, action) × transactionValue
  − riskCost − customerFrictionCost − actionCost
```

---

## Quick Start

### Prerequisites
- Node.js ≥ 20
- Python ≥ 3.10
- npm ≥ 10

### Setup

```bash
# Clone & install
git clone <repo>
cd recoverai
npm install

# Copy environment template
cp .env.example apps/api/.env
# Edit apps/api/.env — fill PORT, etc.

# Start API
npm run dev:api

# Start Web (new terminal)
npm run dev:web
```

### Verify

```bash
# API health
curl http://localhost:5000/api/v1/health

# Web
open http://localhost:5173
```

### Python ML Setup

```bash
cd ml
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
pytest
```

---

## Monorepo Structure

```
recoverai/
├── apps/
│   ├── api/           # Express + TypeScript backend
│   └── web/           # React + Vite + Tailwind frontend
├── packages/
│   ├── shared-types/  # Shared TypeScript types (enums, interfaces)
│   ├── decision-engine/ # Expected-utility decision engine (Phase 3+)
│   └── policy-engine/  # Deterministic safety gate (Phase 3+)
├── ml/                # Python ML project
├── docs/
│   └── architecture/  # Full architecture documentation
├── docker/            # Dockerfiles (foundation)
├── docker-compose.yml
├── .env.example
└── package.json
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite, TypeScript, Tailwind CSS |
| Backend | Node.js 22, Express 4, TypeScript |
| Database | MongoDB + Mongoose (Phase 2+) |
| ML | Python 3.10+, scikit-learn, XGBoost (Phase 3+) |
| AI | Gemini (Phase 4+) |
| Payments | Razorpay Test Mode (Phase 3+) |

---

## Development Status

| Phase | Status |
|-------|--------|
| **Phase 1**: Repository + Engineering Foundation | ✅ Complete |
| **Phase 2**: MongoDB + API + Auth | ⏳ Pending |
| **Phase 3**: Razorpay + ML Training | ⏳ Pending |
| **Phase 4**: Decision Engine + AI Agent | ⏳ Pending |
| **Phase 5**: Full Recovery Pipeline | ⏳ Pending |

---

## Security

- No secrets in source code — ever
- `.env` never committed — use `.env.example`
- All AI actions pass through deterministic policy controls
- No real customer PII in development
- Test-mode payments only

See [Architecture Documentation](docs/architecture/README.md) for full details.

---

## License

MIT © 2026 RecoverAI
