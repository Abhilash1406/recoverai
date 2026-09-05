import { Router } from 'express';
import type { Request, Response } from 'express';
import { dataStore } from '../../services/store.js';

const router = Router();

/**
 * GET /api/v1/health
 *
 * Health check endpoint. Returns service status.
 */
router.get('/', (_req: Request, res: Response) => {
  const mode = dataStore.getSystemMode();
  res.status(200).json({
    success: true,
    service: 'recoverai-api',
    status: 'healthy',
    version: '1.0.0',
    timestamp: new Date().toISOString(),
    environment: process.env['NODE_ENV'] ?? 'development',
    gatewayMode: mode.gatewayMode,
    geminiAvailable: mode.geminiAvailable,
  });
});

export default router;
