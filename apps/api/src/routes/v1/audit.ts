import { Router } from 'express';
import { dataStore } from '../../services/store.js';

const auditRouter = Router();

// GET /api/v1/audit
auditRouter.get('/', async (_req, res, next) => {
  try {
    const events = await dataStore.getAllAuditEvents();
    res.json({
      success: true,
      data: events,
      meta: { total: events.length },
    });
  } catch (err) {
    next(err);
  }
});

export default auditRouter;
