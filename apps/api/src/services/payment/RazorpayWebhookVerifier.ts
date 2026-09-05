import crypto from 'node:crypto';

export class RazorpayWebhookVerifier {
  /**
   * Verifies the Razorpay webhook signature against the raw request body using HMAC-SHA256 and constant-time comparison.
   *
   * @param rawBody - Exact unparsed request body (string or Buffer)
   * @param signature - Signature provided in 'X-Razorpay-Signature' header
   * @param secret - Webhook secret key
   * @returns boolean true if signature is valid
   */
  public static verifySignature(
    rawBody: string | Buffer,
    signature: string | undefined | null,
    secret: string | undefined | null,
  ): boolean {
    if (!signature || !secret) {
      return false;
    }

    try {
      const hmac = crypto.createHmac('sha256', secret);
      hmac.update(rawBody);
      const expectedSignature = hmac.digest('hex');

      const expectedBuffer = Buffer.from(expectedSignature, 'utf8');
      const receivedBuffer = Buffer.from(signature, 'utf8');

      if (expectedBuffer.length !== receivedBuffer.length) {
        return false;
      }

      return crypto.timingSafeEqual(expectedBuffer, receivedBuffer);
    } catch {
      return false;
    }
  }
}
