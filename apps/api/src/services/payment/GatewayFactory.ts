import { PaymentGatewayAdapter } from './PaymentGatewayAdapter.js';
import { MockPaymentGateway } from './MockPaymentGateway.js';
import { RazorpaySandboxAdapter } from './RazorpaySandboxAdapter.js';
import { config } from '../../config/env.js';

export function getPaymentGateway(explicitAdapter?: PaymentGatewayAdapter): PaymentGatewayAdapter {
  if (explicitAdapter) {
    return explicitAdapter;
  }

  const isTest = process.env['NODE_ENV'] === 'test';
  const liveOptIn = process.env['RUN_LIVE_RAZORPAY_TESTS'] === 'true' || process.env['RUN_RAZORPAY_TESTS'] === 'true';

  // In test environment, default to MockPaymentGateway unless explicitly opted into live tests
  if (isTest && !liveOptIn) {
    return new MockPaymentGateway();
  }

  const gatewayMode = process.env['GATEWAY_MODE'] || config.gatewayMode;
  const keyId = process.env['RAZORPAY_KEY_ID'] || config.razorpayKeyId;
  const keySecret = process.env['RAZORPAY_KEY_SECRET'] || config.razorpayKeySecret;

  if (
    gatewayMode === 'RAZORPAY_SANDBOX' &&
    keyId &&
    keySecret
  ) {
    return new RazorpaySandboxAdapter(keyId, keySecret);
  }

  return new MockPaymentGateway();
}
