import {
  PaymentGatewayAdapter,
  PaymentLinkResult,
  RetryPaymentResult,
} from './PaymentGatewayAdapter.js';
import { MockPaymentGateway } from './MockPaymentGateway.js';

export class RazorpaySandboxAdapter implements PaymentGatewayAdapter {
  public name = 'RazorpaySandboxAdapter';
  private fallback: MockPaymentGateway;
  private keyId?: string;
  private keySecret?: string;

  constructor() {
    this.fallback = new MockPaymentGateway();
    if (process.env.RAZORPAY_KEY_ID) {
      this.keyId = process.env.RAZORPAY_KEY_ID;
    }
    if (process.env.RAZORPAY_KEY_SECRET) {
      this.keySecret = process.env.RAZORPAY_KEY_SECRET;
    }
  }

  private hasCredentials(): boolean {
    return Boolean(this.keyId && this.keySecret);
  }

  public async createPaymentLink(
    transactionId: string,
    amount: number,
    description: string,
    customerDetails: { email?: string; contact?: string },
  ): Promise<PaymentLinkResult> {
    if (!this.hasCredentials()) {
      return this.fallback.createPaymentLink(transactionId, amount, description, customerDetails);
    }

    try {
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
        }),
      });

      if (!response.ok) {
        throw new Error(`Razorpay API error HTTP ${response.status}`);
      }

      const data: any = await response.json();
      return {
        paymentLinkId: data.id,
        shortUrl: data.short_url,
        status: data.status === 'created' ? 'created' : 'created',
        amount: data.amount,
        currency: data.currency,
      };
    } catch (err) {
      console.warn('Razorpay Sandbox API unavailable, using Mock fallback:', (err as Error).message);
      return this.fallback.createPaymentLink(transactionId, amount, description, customerDetails);
    }
  }

  public async retryPayment(
    transactionId: string,
    amount: number,
    paymentMethod: string,
  ): Promise<RetryPaymentResult> {
    return this.fallback.retryPayment(transactionId, amount, paymentMethod);
  }

  public async getPaymentStatus(
    paymentId: string,
  ): Promise<{ status: string; amountPaid?: number }> {
    return this.fallback.getPaymentStatus(paymentId);
  }

  public async cancelPaymentLink(
    paymentLinkId: string,
  ): Promise<{ cancelled: boolean }> {
    return this.fallback.cancelPaymentLink(paymentLinkId);
  }
}
