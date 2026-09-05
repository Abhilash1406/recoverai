import { Router } from 'express';
import { dataStore } from '../../services/store.js';

const analyticsRouter = Router();

// GET /api/v1/analytics/summary
analyticsRouter.get('/summary', async (_req, res, next) => {
  try {
    const summary = await dataStore.getAnalyticsSummary();
    res.json({
      success: true,
      data: summary,
    });
  } catch (err) {
    next(err);
  }
});

// GET /api/v1/analytics/revenue
analyticsRouter.get('/revenue', async (_req, res, next) => {
  try {
    const summary = await dataStore.getAnalyticsSummary();
    res.json({
      success: true,
      data: {
        totalRevenueAtRisk: summary.totalRevenueAtRisk,
        totalRecoveredRevenue: summary.totalRecoveredRevenue,
        netRecoveryValue: summary.netRecoveryValue,
        recoveryEfficiency: summary.recoveryEfficiency,
      },
    });
  } catch (err) {
    next(err);
  }
});

// GET /api/v1/analytics/actions
analyticsRouter.get('/actions', async (_req, res, next) => {
  try {
    const cases = await dataStore.getAllCases();
    const actionCounts: Record<string, number> = {};
    for (const c of cases) {
      if (c.selectedAction) {
        actionCounts[c.selectedAction] = (actionCounts[c.selectedAction] || 0) + 1;
      }
    }

    res.json({
      success: true,
      data: actionCounts,
    });
  } catch (err) {
    next(err);
  }
});

export default analyticsRouter;
