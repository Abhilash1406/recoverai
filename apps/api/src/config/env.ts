import dotenv from 'dotenv';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Monorepo root is 4 levels up: apps/api/src/config -> apps/api/src -> apps/api -> apps -> root
// In compiled dist: apps/api/dist/config -> apps/api/dist -> apps/api -> apps -> root
const rootEnvPath = path.resolve(__dirname, '../../../../.env');
const cwdEnvPath = path.resolve(process.cwd(), '.env');

if (fs.existsSync(rootEnvPath)) {
  dotenv.config({ path: rootEnvPath });
}
if (fs.existsSync(cwdEnvPath) && cwdEnvPath !== rootEnvPath) {
  dotenv.config({ path: cwdEnvPath });
}

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

  persistenceMode: ((process.env['NODE_ENV'] === 'test' && !process.env['RUN_MONGODB_TESTS'] && !process.env['TEST_MONGODB_URI']) ? 'memory' : (optionalEnv('PERSISTENCE_MODE', 'memory').toLowerCase() === 'mongodb' ? 'mongodb' : 'memory')) as 'memory' | 'mongodb',
  mongodbUri: optionalEnv('MONGODB_URI', 'mongodb://localhost:27017/recoverai'),

  // Phase 5B Razorpay Sandbox
  razorpayKeyId: optionalEnv('RAZORPAY_KEY_ID', ''),
  razorpayKeySecret: optionalEnv('RAZORPAY_KEY_SECRET', ''),
  razorpayWebhookSecret: optionalEnv('RAZORPAY_WEBHOOK_SECRET', ''),
  gatewayMode: (
    (process.env['NODE_ENV'] === 'test' && process.env['RUN_LIVE_RAZORPAY_TESTS'] !== 'true' && process.env['RUN_RAZORPAY_TESTS'] !== 'true')
      ? 'MOCK_DEMO'
      : (optionalEnv('GATEWAY_MODE', '').toUpperCase() === 'RAZORPAY_SANDBOX' || (Boolean(process.env['RAZORPAY_KEY_ID'] && process.env['RAZORPAY_KEY_SECRET']) && optionalEnv('GATEWAY_MODE', '').toUpperCase() !== 'MOCK') ? 'RAZORPAY_SANDBOX' : 'MOCK_DEMO')
  ) as 'MOCK_DEMO' | 'RAZORPAY_SANDBOX',
} as const;

export type Config = typeof config;
