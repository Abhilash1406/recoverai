import {
  PaymentGatewayAdapter,
  PaymentLinkResult,
  RetryPaymentResult,
} from './PaymentGatewayAdapter.js';

export class MockPaymentGateway implements PaymentGatewayAdapter {
  public name = 'MockPaymentGateway';

  public async createPaymentLink(
    transactionId: string,
    amount: number,
    _description: string,
    _customerDetails: { email?: string; contact?: string },
  ): Promise<PaymentLinkResult> {
    if (amount <= 0) {
      throw new Error('Invalid payment amount: must be greater than zero.');
    }
    const linkId = `plink_mock_${transactionId}_${Date.now()}`;
    return {
      paymentLinkId: linkId,
      shortUrl: `https://rzp.io/i/mock_${linkId.slice(-6)}`,
      status: 'created',
      amount,
      currency: 'INR',
    };
  }

  public async retryPayment(
    transactionId: string,
    amount: number,
    _paymentMethod: string,
  ): Promise<RetryPaymentResult> {
    if (amount <= 0) {
      throw new Error('Invalid payment amount: must be greater than zero.');
    }
    const retryId = `pay_mock_retry_${transactionId}_${Date.now()}`;
    return {
      retryId,
      status: 'captured',
      amountRecovered: amount,
    };
  }

  public async getPaymentStatus(
    _paymentId: string,
  ): Promise<{ status: string; amountPaid?: number }> {
    return {
      status: 'captured',
      amountPaid: 500000,
    };
  }

  public async cancelPaymentLink(
    _paymentLinkId: string,
  ): Promise<{ cancelled: boolean }> {
    return { cancelled: true };
  }
}
