import { Router } from 'express';
import { dataStore } from '../../services/store.js';

const auditRouter = Router();

// GET /api/v1/audit
auditRouter.get('/', (_req, res) => {
  const events = dataStore.getAllAuditEvents();
  res.json({
    success: true,
    data: events,
    meta: { total: events.length },
  });
});

export default auditRouter;
