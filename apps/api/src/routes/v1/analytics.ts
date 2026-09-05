import { Router } from 'express';
import { dataStore } from '../../services/store.js';

const analyticsRouter = Router();

// GET /api/v1/analytics/summary
analyticsRouter.get('/summary', (_req, res) => {
  const summary = dataStore.getAnalyticsSummary();
  res.json({
    success: true,
    data: summary,
  });
});

// GET /api/v1/analytics/revenue
analyticsRouter.get('/revenue', (_req, res) => {
  const summary = dataStore.getAnalyticsSummary();
  res.json({
    success: true,
    data: {
      totalRevenueAtRisk: summary.totalRevenueAtRisk,
      totalRecoveredRevenue: summary.totalRecoveredRevenue,
      netRecoveryValue: summary.netRecoveryValue,
      recoveryEfficiency: summary.recoveryEfficiency,
    },
  });
});

// GET /api/v1/analytics/actions
analyticsRouter.get('/actions', (_req, res) => {
  const cases = dataStore.getAllCases();
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
});

export default analyticsRouter;
