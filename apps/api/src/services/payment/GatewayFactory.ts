import { PaymentGatewayAdapter } from './PaymentGatewayAdapter.js';
import { MockPaymentGateway } from './MockPaymentGateway.js';
import { RazorpaySandboxAdapter } from './RazorpaySandboxAdapter.js';
import { config } from '../../config/env.js';

export function getPaymentGateway(explicitAdapter?: PaymentGatewayAdapter): PaymentGatewayAdapter {
  if (explicitAdapter) {
    return explicitAdapter;
  }

  if (
    config.gatewayMode === 'RAZORPAY_SANDBOX' &&
    config.razorpayKeyId &&
    config.razorpayKeySecret
  ) {
    return new RazorpaySandboxAdapter();
  }

  return new MockPaymentGateway();
}
