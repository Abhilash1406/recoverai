import { Router } from 'express';
import { dataStore } from '../../services/store.js';

const decisionsRouter = Router();

// GET /api/v1/decisions
decisionsRouter.get('/', (_req, res) => {
  const decisions = dataStore.getAllDecisions();
  res.json({
    success: true,
    data: decisions,
    meta: { total: decisions.length },
  });
});

export default decisionsRouter;
