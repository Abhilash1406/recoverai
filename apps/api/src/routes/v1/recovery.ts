import { Router } from 'express';
import { recoveryOrchestrator } from '../../services/orchestrator/RecoveryOrchestrator.js';
import { dataStore } from '../../services/store.js';

const recoveryRouter = Router();

// GET /api/v1/recovery/cases
recoveryRouter.get('/cases', async (_req, res, next) => {
  try {
    const cases = await dataStore.getAllCases();
    res.json({
      success: true,
      data: cases,
      meta: { total: cases.length },
    });
  } catch (err) {
    next(err);
  }
});

// GET /api/v1/recovery/cases/:id
recoveryRouter.get('/cases/:id', async (req, res, next) => {
  try {
    const recCase = await dataStore.getCase(req.params.id);
    if (!recCase) {
      res.status(404).json({
        success: false,
        error: { message: `Recovery case ${req.params.id} not found` },
      });
      return;
    }
    const auditEvents = await dataStore.getAuditEventsByCaseId(req.params.id);
    const decision = recCase.currentDecisionId ? await dataStore.getDecision(recCase.currentDecisionId) : undefined;

    res.json({
      success: true,
      data: {
        case: recCase,
        decision,
        auditEvents,
      },
    });
  } catch (err) {
    next(err);
  }
});

// POST /api/v1/recovery/cases/:id/analyze
recoveryRouter.post('/cases/:id/analyze', async (req, res, next) => {
  try {
    const result = await recoveryOrchestrator.analyzeCase(req.params.id);
    res.json({
      success: true,
      data: result,
    });
  } catch (err) {
    next(err);
  }
});

// POST /api/v1/recovery/cases/:id/execute
recoveryRouter.post('/cases/:id/execute', async (req, res, next) => {
  try {
    const idempotencyKey = (req.headers['idempotency-key'] as string) || req.body?.idempotencyKey;
    const updatedCase = await recoveryOrchestrator.executeAction(req.params.id, idempotencyKey);
    res.json({
      success: true,
      data: updatedCase,
    });
  } catch (err) {
    next(err);
  }
});

// POST /api/v1/recovery/cases/:id/stop
recoveryRouter.post('/cases/:id/stop', async (req, res, next) => {
  try {
    const reason = req.body?.reason || 'Merchant stopped recovery manually.';
    const updatedCase = await recoveryOrchestrator.stopCase(req.params.id, reason);
    res.json({
      success: true,
      data: updatedCase,
    });
  } catch (err) {
    next(err);
  }
});

// GET /api/v1/recovery/cases/:id/audit
recoveryRouter.get('/cases/:id/audit', async (req, res, next) => {
  try {
    const auditEvents = await dataStore.getAuditEventsByCaseId(req.params.id);
    res.json({
      success: true,
      data: auditEvents,
    });
  } catch (err) {
    next(err);
  }
});

export default recoveryRouter;
