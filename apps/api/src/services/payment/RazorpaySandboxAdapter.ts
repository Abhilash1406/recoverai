import {
  PaymentGatewayAdapter,
  PaymentLinkResult,
  RetryPaymentResult,
} from './PaymentGatewayAdapter.js';
import { MockPaymentGateway } from './MockPaymentGateway.js';
import { config } from '../../config/env.js';

export class RazorpaySandboxAdapter implements PaymentGatewayAdapter {
  public name = 'RazorpaySandboxAdapter';
  private fallback: MockPaymentGateway;
  private keyId: string;
  private keySecret: string;

  constructor(keyId?: string, keySecret?: string) {
    this.fallback = new MockPaymentGateway();
    this.keyId = keyId || config.razorpayKeyId || process.env['RAZORPAY_KEY_ID'] || '';
    this.keySecret = keySecret || config.razorpayKeySecret || process.env['RAZORPAY_KEY_SECRET'] || '';
  }

  public hasCredentials(): boolean {
    return Boolean(this.keyId && this.keySecret);
  }

  public async createPaymentLink(
    transactionId: string,
    amount: number,
    description: string,
    customerDetails: { email?: string; contact?: string },
  ): Promise<PaymentLinkResult> {
    if (amount <= 0) {
      throw new Error('Invalid payment amount: must be greater than zero.');
    }

    if (!this.hasCredentials()) {
      return this.fallback.createPaymentLink(transactionId, amount, description, customerDetails);
    }

    // Live call to Razorpay Sandbox API
    const auth = Buffer.from(`${this.keyId}:${this.keySecret}`).toString('base64');
    const response = await fetch('https://api.razorpay.com/v1/payment_links', {
      method: 'POST',
      headers: {
        Authorization: `Basic ${auth}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        amount,
        currency: 'INR',
        description,
        reference_id: transactionId,
        customer: {
          name: 'RecoverAI Customer',
          email: customerDetails.email || 'customer@example.com',
          contact: customerDetails.contact || '+919999999999',
        },
        notify: {
          sms: true,
          email: true,
        },
        reminder_enable: true,
        notes: {
          transactionId,
        },
      }),
    });

    if (!response.ok) {
      let errorDetail = '';
      try {
        const errJson: any = await response.json();
        errorDetail = errJson?.error?.description || errJson?.error?.code || response.statusText;
      } catch {
        errorDetail = response.statusText;
      }
      // CRITICAL: Do NOT fall back to MockPaymentGateway when configured Razorpay Sandbox call fails!
      throw new Error(`Razorpay Sandbox API error (HTTP ${response.status}): ${errorDetail}`);
    }

    const data: any = await response.json();
    return {
      paymentLinkId: data.id,
      shortUrl: data.short_url,
      status: data.status === 'created' || data.status === 'paid' ? data.status : 'created',
      amount: data.amount,
      currency: data.currency,
    };
  }

  public async retryPayment(
    transactionId: string,
    amount: number,
    paymentMethod: string,
  ): Promise<RetryPaymentResult> {
    if (amount <= 0) {
      throw new Error('Invalid payment amount: must be greater than zero.');
    }

    if (!this.hasCredentials()) {
      return this.fallback.retryPayment(transactionId, amount, paymentMethod);
    }

    try {
      const auth = Buffer.from(`${this.keyId}:${this.keySecret}`).toString('base64');
      // Create a Razorpay order for this retry attempt
      const response = await fetch('https://api.razorpay.com/v1/orders', {
        method: 'POST',
        headers: {
          Authorization: `Basic ${auth}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          amount,
          currency: 'INR',
          receipt: `rcpt_${transactionId.slice(-14)}`,
          notes: {
            transactionId,
            retryMethod: paymentMethod,
          },
        }),
      });

      if (!response.ok) {
        let errDesc = '';
        try {
          const errData: any = await response.json();
          errDesc = errData?.error?.description || response.statusText;
        } catch {
          errDesc = response.statusText;
        }
        // Return explicit failure without pretending success
        return {
          retryId: `retry_fail_${Date.now()}`,
          status: 'failed',
          amountRecovered: 0,
          failureReason: `Razorpay order creation failed: ${errDesc}`,
        };
      }

      const orderData: any = await response.json();
      return {
        retryId: orderData.id,
        status: 'pending',
        amountRecovered: 0,
      };
    } catch (err: any) {
      // Return failure instead of falling back to mock success
      return {
        retryId: `retry_err_${Date.now()}`,
        status: 'failed',
        amountRecovered: 0,
        failureReason: err?.message || 'Razorpay retry payment network error',
      };
    }
  }

  public async getPaymentStatus(
    paymentId: string,
  ): Promise<{ status: string; amountPaid?: number }> {
    if (!this.hasCredentials()) {
      return this.fallback.getPaymentStatus(paymentId);
    }

    try {
      const auth = Buffer.from(`${this.keyId}:${this.keySecret}`).toString('base64');
      const response = await fetch(`https://api.razorpay.com/v1/payments/${paymentId}`, {
        method: 'GET',
        headers: {
          Authorization: `Basic ${auth}`,
        },
      });

      if (!response.ok) {
        return { status: 'failed' };
      }

      const data: any = await response.json();
      return {
        status: data.status,
        amountPaid: data.amount,
      };
    } catch {
      return { status: 'failed' };
    }
  }

  public async cancelPaymentLink(
    paymentLinkId: string,
  ): Promise<{ cancelled: boolean }> {
    if (!this.hasCredentials()) {
      return this.fallback.cancelPaymentLink(paymentLinkId);
    }

    try {
      const auth = Buffer.from(`${this.keyId}:${this.keySecret}`).toString('base64');
      const response = await fetch(`https://api.razorpay.com/v1/payment_links/${paymentLinkId}/cancel`, {
        method: 'POST',
        headers: {
          Authorization: `Basic ${auth}`,
        },
      });

      return { cancelled: response.ok };
    } catch {
      return { cancelled: false };
    }
  }
}
