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

  persistenceMode: (optionalEnv('PERSISTENCE_MODE', 'memory').toLowerCase() === 'mongodb' ? 'mongodb' : 'memory') as 'memory' | 'mongodb',
  mongodbUri: optionalEnv('MONGODB_URI', 'mongodb://localhost:27017/recoverai'),

  // Phase 5B Razorpay Sandbox
  razorpayKeyId: optionalEnv('RAZORPAY_KEY_ID', ''),
  razorpayKeySecret: optionalEnv('RAZORPAY_KEY_SECRET', ''),
  razorpayWebhookSecret: optionalEnv('RAZORPAY_WEBHOOK_SECRET', ''),
  gatewayMode: (optionalEnv('GATEWAY_MODE', '').toUpperCase() === 'RAZORPAY_SANDBOX' || (Boolean(process.env['RAZORPAY_KEY_ID'] && process.env['RAZORPAY_KEY_SECRET']) && optionalEnv('GATEWAY_MODE', '').toUpperCase() !== 'MOCK') ? 'RAZORPAY_SANDBOX' : 'MOCK_DEMO') as 'MOCK_DEMO' | 'RAZORPAY_SANDBOX',
} as const;

export type Config = typeof config;
