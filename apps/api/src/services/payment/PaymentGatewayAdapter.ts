export interface PaymentLinkResult {
  paymentLinkId: string;
  shortUrl: string;
  status: 'created' | 'paid' | 'expired' | 'cancelled';
  amount: number; // paise
  currency: string;
}

export interface RetryPaymentResult {
  retryId: string;
  status: 'captured' | 'failed' | 'pending';
  amountRecovered: number; // paise
  failureReason?: string;
}

export interface PaymentGatewayAdapter {
  name: string;
  
  createPaymentLink(
    transactionId: string,
    amount: number,
    description: string,
    customerDetails: { email?: string; contact?: string },
  ): Promise<PaymentLinkResult>;

  retryPayment(
    transactionId: string,
    amount: number,
    paymentMethod: string,
  ): Promise<RetryPaymentResult>;

  getPaymentStatus(
    paymentId: string,
  ): Promise<{ status: string; amountPaid?: number }>;

  cancelPaymentLink(
    paymentLinkId: string,
  ): Promise<{ cancelled: boolean }>;
}
