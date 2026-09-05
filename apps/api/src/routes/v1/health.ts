import { Router } from 'express';
import type { Request, Response, NextFunction } from 'express';
import { dataStore } from '../../services/store.js';

const router = Router();

/**
 * GET /api/v1/health
 *
 * Health check endpoint. Returns service status, gateway mode, gemini status, and persistence mode.
 */
router.get('/', async (_req: Request, res: Response, next: NextFunction) => {
  try {
    const mode = await dataStore.getSystemMode();
    res.status(200).json({
      success: true,
      service: 'recoverai-api',
      status: 'healthy',
      version: '1.0.0',
      timestamp: new Date().toISOString(),
      environment: process.env['NODE_ENV'] ?? 'development',
      gatewayMode: mode.gatewayMode,
      geminiAvailable: mode.geminiAvailable,
      persistenceMode: mode.persistenceMode,
      mongoConnected: mode.mongoConnected,
    });
  } catch (err) {
    next(err);
  }
});

export default router;
