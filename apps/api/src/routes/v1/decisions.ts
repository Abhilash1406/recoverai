import { Router } from 'express';
import { dataStore } from '../../services/store.js';

const decisionsRouter = Router();

// GET /api/v1/decisions
decisionsRouter.get('/', async (_req, res, next) => {
  try {
    const decisions = await dataStore.getAllDecisions();
    res.json({
      success: true,
      data: decisions,
      meta: { total: decisions.length },
    });
  } catch (err) {
    next(err);
  }
});

export default decisionsRouter;
