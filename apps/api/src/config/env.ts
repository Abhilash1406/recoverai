/**
 * Environment configuration
 *
 * All environment variables are validated here at startup.
 * This ensures the application fails fast if required config is missing,
 * rather than encountering undefined values deep in business logic.
 */

/** Require an environment variable — throws at startup if not set. Use in Phase 2+ for MongoDB, Razorpay, Gemini. */
export function requireEnv(key: string): string {
  const value = process.env[key];
  if (!value) {
    throw new Error(`Missing required environment variable: ${key}`);
  }
  return value;
}

function optionalEnv(key: string, defaultValue: string): string {
  return process.env[key] ?? defaultValue;
}

export const config = {
  nodeEnv: optionalEnv('NODE_ENV', 'development'),
  port: parseInt(optionalEnv('PORT', '5000'), 10),
  clientUrl: optionalEnv('CLIENT_URL', 'http://localhost:5173'),

  // These will be validated in later phases when services are integrated
  // mongodbUri: process.env['MONGODB_URI'],
  // razorpayKeyId: process.env['RAZORPAY_KEY_ID'],
  // geminiApiKey: process.env['GEMINI_API_KEY'],
} as const;

export type Config = typeof config;
