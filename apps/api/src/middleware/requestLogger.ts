import type { Request, Response, NextFunction } from 'express';

/**
 * Request logger middleware
 *
 * Logs method, path, status, and duration for every request.
 * Uses a structured format to be machine-parseable in later phases.
 */
export function requestLogger(req: Request, res: Response, next: NextFunction): void {
  const start = Date.now();
  const { method, path } = req;

  res.on('finish', () => {
    const duration = Date.now() - start;
    const { statusCode } = res;

    const level = statusCode >= 500 ? 'ERROR' : statusCode >= 400 ? 'WARN' : 'INFO';

    console.log(
      JSON.stringify({
        level,
        timestamp: new Date().toISOString(),
        method,
        path,
        statusCode,
        durationMs: duration,
      }),
    );
  });

  next();
}
