import express from 'express';
import cors from 'cors';
import { config } from './config/env.js';
import { requestLogger } from './middleware/requestLogger.js';
import { errorHandler } from './middleware/errorHandler.js';
import rootRouter from './routes/index.js';

/**
 * Express application factory
 *
 * Returns a configured Express app instance.
 * Keeping this separate from server.ts makes the app importable for testing
 * without starting the HTTP server.
 */
export function createApp(): express.Application {
  const app = express();

  // ── Middleware ─────────────────────────────────────────────────────────────
  app.use(
    cors({
      origin: config.clientUrl,
      methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
      allowedHeaders: ['Content-Type', 'Authorization'],
    }),
  );
  app.use(express.json({ limit: '1mb' }));
  app.use(express.urlencoded({ extended: true }));
  app.use(requestLogger);

  // ── Routes ─────────────────────────────────────────────────────────────────
  app.use('/api', rootRouter);

  // ── 404 handler ────────────────────────────────────────────────────────────
  app.use((_req, res) => {
    res.status(404).json({
      success: false,
      error: { message: 'Route not found' },
    });
  });

  // ── Centralized error handler ───────────────────────────────────────────────
  app.use(errorHandler);

  return app;
}
