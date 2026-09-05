import type { Request, Response, NextFunction } from 'express';

/**
 * Application error class
 *
 * Extend this to create domain-specific errors in later phases
 * (e.g., ValidationError, NotFoundError, PolicyViolationError).
 */
export class AppError extends Error {
  public readonly statusCode: number;
  public readonly isOperational: boolean;

  constructor(message: string, statusCode = 500, isOperational = true) {
    super(message);
    this.name = 'AppError';
    this.statusCode = statusCode;
    this.isOperational = isOperational;
    Error.captureStackTrace(this, this.constructor);
  }
}

/**
 * Centralized error handler middleware
 *
 * All errors flow through here. In later phases this will:
 * - Log to a structured logger (e.g., Winston/Pino)
 * - Report unexpected errors to an error tracking service
 * - Return standardized error envelopes
 */
export function errorHandler(
  err: unknown,
  _req: Request,
  res: Response,
  _next: NextFunction,
): void {
  if (err instanceof AppError) {
    res.status(err.statusCode).json({
      success: false,
      error: {
        message: err.message,
        ...(process.env['NODE_ENV'] === 'development' && { stack: err.stack }),
      },
    });
    return;
  }

  // Unknown/unhandled error
  const message = err instanceof Error ? err.message : 'Internal server error';

  console.error(
    JSON.stringify({
      level: 'ERROR',
      timestamp: new Date().toISOString(),
      message,
      ...(process.env['NODE_ENV'] === 'development' && err instanceof Error && { stack: err.stack }),
    }),
  );

  res.status(500).json({
    success: false,
    error: {
      message: 'Internal server error',
    },
  });
}
