import { FailureCategory } from '@recoverai/shared-types';

export interface RazorpayPaymentFailureInput {
  method?: string;
  error_code?: string;
  error_description?: string;
  error_source?: string;
  error_reason?: string;
}

export interface MappedFailureResult {
  category: FailureCategory;
  code: string;
}

export class RazorpayFailureMapper {
  public static mapFailure(input: RazorpayPaymentFailureInput): MappedFailureResult {
    const errorCode = (input.error_code || '').toUpperCase();
    const description = (input.error_description || '').toLowerCase();
    const reason = (input.error_reason || '').toLowerCase();
    const source = (input.error_source || '').toLowerCase();
    const method = (input.method || '').toLowerCase();

    // 1. Fraud / Risk Suspected
    if (
      errorCode.includes('FRAUD') ||
      reason.includes('fraud') ||
      description.includes('fraud') ||
      description.includes('suspicious') ||
      reason.includes('risk')
    ) {
      return {
        category: FailureCategory.FRAUD_SUSPECTED,
        code: input.error_code || 'fraud_suspected',
      };
    }

    // 2. Insufficient Balance / Funds
    if (
      errorCode.includes('INSUFFICIENT') ||
      reason.includes('insufficient_funds') ||
      reason.includes('insufficient_balance') ||
      description.includes('insufficient') ||
      description.includes('low balance')
    ) {
      return {
        category: FailureCategory.INSUFFICIENT_FUNDS,
        code: input.error_code || 'insufficient_funds',
      };
    }

    // 3. Card Expired
    if (
      errorCode.includes('EXPIRED') ||
      reason.includes('expired_card') ||
      description.includes('expired card') ||
      description.includes('card expired')
    ) {
      return {
        category: FailureCategory.CARD_EXPIRED,
        code: input.error_code || 'card_expired',
      };
    }

    // 4. Invalid CVV
    if (
      errorCode.includes('INVALID_CVV') ||
      errorCode.includes('CVV') ||
      reason.includes('invalid_cvv') ||
      description.includes('cvv')
    ) {
      return {
        category: FailureCategory.INVALID_CVV,
        code: input.error_code || 'invalid_cvv',
      };
    }

    // 5. Authentication / 3DS / OTP Failed
    if (
      errorCode.includes('OTP') ||
      errorCode.includes('AUTH') ||
      reason.includes('authentication') ||
      reason.includes('otp') ||
      description.includes('otp') ||
      description.includes('3ds') ||
      description.includes('authentication') ||
      description.includes('password')
    ) {
      return {
        category: FailureCategory.AUTHENTICATION_FAILED,
        code: input.error_code || 'authentication_failed',
      };
    }

    // 6. Transaction Limit Exceeded
    if (
      errorCode.includes('LIMIT') ||
      reason.includes('limit') ||
      description.includes('limit exceeded') ||
      description.includes('maximum amount')
    ) {
      return {
        category: FailureCategory.LIMIT_EXCEEDED,
        code: input.error_code || 'limit_exceeded',
      };
    }

    // 7. Timeouts & Network/Bank Connectivity Errors
    if (
      errorCode.includes('TIMEOUT') ||
      errorCode.includes('TIMEDOUT') ||
      reason.includes('timed_out') ||
      description.includes('timed out') ||
      description.includes('timeout')
    ) {
      // Differentiate bank timeout vs network/gateway timeout
      if (source === 'bank' || source === 'issuer') {
        return {
          category: FailureCategory.BANK_TIMEOUT,
          code: input.error_code || 'bank_timeout',
        };
      }
      return {
        category: FailureCategory.NETWORK_ERROR,
        code: input.error_code || 'network_timeout',
      };
    }

    // 8. General Network / Gateway Errors
    if (
      errorCode.includes('GATEWAY_ERROR') ||
      source === 'gateway' ||
      reason.includes('network') ||
      description.includes('network') ||
      description.includes('connection failed')
    ) {
      return {
        category: FailureCategory.NETWORK_ERROR,
        code: input.error_code || 'network_error',
      };
    }

    // 9. Bank Declines (Contextual by payment method)
    if (
      errorCode.includes('DECLINED') ||
      reason.includes('declined') ||
      description.includes('declined by bank') ||
      source === 'bank'
    ) {
      if (method === 'upi') {
        // UPI declines without balance issue are typically bank PSP timeouts or technical glitches
        return {
          category: FailureCategory.BANK_TIMEOUT,
          code: input.error_code || 'upi_bank_decline',
        };
      }
      if (method === 'netbanking') {
        return {
          category: FailureCategory.BANK_TIMEOUT,
          code: input.error_code || 'netbanking_bank_decline',
        };
      }
      // Card decline
      return {
        category: FailureCategory.CARD_DECLINED,
        code: input.error_code || 'card_declined',
      };
    }

    // 10. Fallback
    return {
      category: FailureCategory.UNKNOWN,
      code: input.error_code || 'unknown_failure',
    };
  }
}
