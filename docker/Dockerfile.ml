# =============================================================================
# Dockerfile.ml — RecoverAI ML Server
# Phase 1: Foundation only — no model serving yet
# Phase 4+: Will serve FastAPI ML inference endpoints
# =============================================================================

FROM python:3.11-slim AS base
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

FROM base AS deps
COPY ml/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

FROM deps AS runner
COPY ml/src ./src
COPY ml/models ./models

# Phase 4+: Uncomment when FastAPI server is added
# EXPOSE 8000
# CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

CMD ["python", "-c", "print('RecoverAI ML container ready — Phase 4+ for inference server')"]
