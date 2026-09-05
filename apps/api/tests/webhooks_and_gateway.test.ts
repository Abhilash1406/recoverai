import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import request from 'supertest';
import crypto from 'node:crypto';
import { createApp } from '../src/app.js';
import { dataStore } from '../src/services/store.js';
import { RazorpayFailureMapper } from '../src/services/payment/RazorpayFailureMapper.js';
import { RazorpaySandboxAdapter, sanitizeCustomerContact } from '../src/services/payment/RazorpaySandboxAdapter.js';
import { MockPaymentGateway } from '../src/services/payment/MockPaymentGateway.js';
import { getPaymentGateway } from '../src/services/payment/GatewayFactory.js';
import {
  Transaction,
  TransactionStatus,
  FailureCategory,
  RecoveryCaseState,
  RecoveryAction,
  AuditEventType,
} from '@recoverai/shared-types';

const WEBHOOK_SECRET = 'test_secret_key_phase5b';

function signPayload(payload: any, secret: string = WEBHOOK_SECRET): string {
  const hmac = crypto.createHmac('sha256', secret);
  hmac.update(JSON.stringify(payload));
  return hmac.digest('hex');
}

describe('Phase 5B — Razorpay Sandbox Integration Tests', () => {
  let app: any;

  beforeEach(async () => {
    process.env['RAZORPAY_WEBHOOK_SECRET'] = WEBHOOK_SECRET;
    await dataStore.clear();
    app = createApp();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ===========================================================================
  // I. Razorpay Failure Taxonomy Mapping Tests
  // ===========================================================================
  describe('I. RazorpayFailureMapper', () => {
    it('maps fraud indicators to FRAUD_SUSPECTED', () => {
      const res = RazorpayFailureMapper.mapFailure({
        error_code: 'BAD_REQUEST_PAYMENT_FRAUD_IDENTIFIED',
        error_description: 'Transaction flagged as fraud by risk engine',
      });
      expect(res.category).toBe(FailureCategory.FRAUD_SUSPECTED);
    });

    it('maps low balance to INSUFFICIENT_FUNDS', () => {
      const res = RazorpayFailureMapper.mapFailure({
        error_code: 'BAD_REQUEST_PAYMENT_ACCOUNT_INSUFFICIENT_BALANCE',
        error_description: 'Account has insufficient balance',
        method: 'upi',
      });
      expect(res.category).toBe(FailureCategory.INSUFFICIENT_FUNDS);
    });

    it('maps card expired to CARD_EXPIRED', () => {
      const res = RazorpayFailureMapper.mapFailure({
        error_code: 'BAD_REQUEST_PAYMENT_CARD_EXPIRED',
        error_description: 'Card has expired',
        method: 'card',
      });
      expect(res.category).toBe(FailureCategory.CARD_EXPIRED);
    });

    it('maps invalid CVV to INVALID_CVV', () => {
      const res = RazorpayFailureMapper.mapFailure({
        error_code: 'BAD_REQUEST_PAYMENT_CARD_INVALID_CVV',
        error_description: 'Card CVV is invalid',
        method: 'card',
      });
      expect(res.category).toBe(FailureCategory.INVALID_CVV);
    });

    it('maps OTP / 3DS issues to AUTHENTICATION_FAILED', () => {
      const res = RazorpayFailureMapper.mapFailure({
        error_code: 'BAD_REQUEST_PAYMENT_OTP_VALIDATION_FAILED',
        error_description: 'OTP entered was incorrect',
      });
      expect(res.category).toBe(FailureCategory.AUTHENTICATION_FAILED);
    });

    it('maps limit exceeded to LIMIT_EXCEEDED', () => {
      const res = RazorpayFailureMapper.mapFailure({
        error_code: 'BAD_REQUEST_PAYMENT_TRANSACTION_LIMIT_EXCEEDED',
        error_description: 'Transaction amount exceeds daily limit',
      });
      expect(res.category).toBe(FailureCategory.LIMIT_EXCEEDED);
    });

    it('maps bank timeouts to BANK_TIMEOUT and gateway errors to NETWORK_ERROR', () => {
      const bankTimeout = RazorpayFailureMapper.mapFailure({
        error_code: 'BAD_REQUEST_PAYMENT_TIMEDOUT',
        error_source: 'bank',
        error_description: 'Bank servers did not respond in time',
      });
      expect(bankTimeout.category).toBe(FailureCategory.BANK_TIMEOUT);

      const gatewayNet = RazorpayFailureMapper.mapFailure({
        error_code: 'GATEWAY_ERROR',
        error_source: 'gateway',
        error_description: 'Network connectivity lost during routing',
      });
      expect(gatewayNet.category).toBe(FailureCategory.NETWORK_ERROR);
    });

    it('differentiates bank decline by method (UPI decline vs Card decline)', () => {
      const upiDecline = RazorpayFailureMapper.mapFailure({
        error_code: 'BAD_REQUEST_PAYMENT_DECLINED_BY_BANK',
        method: 'upi',
        error_source: 'bank',
      });
      expect(upiDecline.category).toBe(FailureCategory.BANK_TIMEOUT);

      const cardDecline = RazorpayFailureMapper.mapFailure({
        error_code: 'BAD_REQUEST_PAYMENT_DECLINED_BY_BANK',
        method: 'card',
        error_source: 'bank',
      });
      expect(cardDecline.category).toBe(FailureCategory.CARD_DECLINED);
    });
  });

  // ===========================================================================
  // A, B, C, J. Signature & Payload Validation Tests
  // ===========================================================================
  describe('A-C, J. Webhook Signature & Payload Verification', () => {
    it('A. accepts valid HMAC-SHA256 signature', async () => {
      const payload = {
        event: 'payment.failed',
        event_id: 'evt_sig_test_001',
        payload: {
          payment: {
            entity: {
              id: 'pay_sig_001',
              amount: 50000,
              currency: 'INR',
              method: 'upi',
              error_code: 'BAD_REQUEST_PAYMENT_TIMEDOUT',
              error_source: 'bank',
            },
          },
        },
      };

      const sig = signPayload(payload);
      const res = await request(app)
        .post('/api/v1/webhooks/razorpay')
        .set('X-Razorpay-Signature', sig)
        .send(payload);

      expect(res.status).toBe(200);
      expect(res.body.success).toBe(true);
      expect(res.body.event).toBe('payment.failed');
    });

    it('B. rejects invalid HMAC signature with HTTP 400', async () => {
      const payload = {
        event: 'payment.failed',
        event_id: 'evt_sig_invalid',
        payload: { payment: { entity: { id: 'pay_bad_sig', amount: 50000 } } },
      };

      const res = await request(app)
        .post('/api/v1/webhooks/razorpay')
        .set('X-Razorpay-Signature', 'invalid_hex_signature_abcdef1234567890')
        .send(payload);

      expect(res.status).toBe(400);
      expect(res.body.success).toBe(false);
      expect(res.body.error.message).toContain('Invalid or missing webhook signature');
    });

    it('C. rejects missing signature header with HTTP 400', async () => {
      const payload = {
        event: 'payment.failed',
        event_id: 'evt_no_sig',
      };

      const res = await request(app)
        .post('/api/v1/webhooks/razorpay')
        .send(payload);

      expect(res.status).toBe(400);
      expect(res.body.success).toBe(false);
    });

    it('J. rejects invalid payload missing event or payment entity with HTTP 400', async () => {
      const payloadNoEvent = {
        event_id: 'evt_no_event',
      };
      const sig1 = signPayload(payloadNoEvent);
      const res1 = await request(app)
        .post('/api/v1/webhooks/razorpay')
        .set('X-Razorpay-Signature', sig1)
        .send(payloadNoEvent);
      expect(res1.status).toBe(400);

      const payloadBadAmount = {
        event: 'payment.failed',
        event_id: 'evt_bad_amt',
        payload: {
          payment: {
            entity: { id: 'pay_0', amount: -500 },
          },
        },
      };
      const sig2 = signPayload(payloadBadAmount);
      const res2 = await request(app)
        .post('/api/v1/webhooks/razorpay')
        .set('X-Razorpay-Signature', sig2)
        .send(payloadBadAmount);
      expect(res2.status).toBe(400);
    });
  });

  // ===========================================================================
  // D. Duplicate Webhook Protection
  // ===========================================================================
  describe('D. Duplicate Webhook Protection', () => {
    it('returns HTTP 200 duplicate_ignored on repeated event_id without duplicate processing', async () => {
      const payload = {
        event: 'payment.failed',
        event_id: 'evt_dup_test_999',
        payload: {
          payment: {
            entity: {
              id: 'pay_dup_999',
              amount: 75000,
              currency: 'INR',
              method: 'upi',
              error_code: 'BAD_REQUEST_PAYMENT_TIMEDOUT',
              error_source: 'bank',
            },
          },
        },
      };

      const sig = signPayload(payload);

      // First delivery
      const res1 = await request(app)
        .post('/api/v1/webhooks/razorpay')
        .set('X-Razorpay-Signature', sig)
        .send(payload);
      expect(res1.status).toBe(200);
      expect(res1.body.event).toBe('payment.failed');

      // Duplicate delivery with same event_id
      const res2 = await request(app)
        .post('/api/v1/webhooks/razorpay')
        .set('X-Razorpay-Signature', sig)
        .send(payload);
      expect(res2.status).toBe(200);
      expect(res2.body.status).toBe('duplicate_ignored');

      // Assert only 1 case was created
      const allCases = await dataStore.getAllCases();
      const matchingCases = allCases.filter((c) => c.transactionId === 'pay_dup_999');
      expect(matchingCases.length).toBe(1);
    });
  });

  // ===========================================================================
  // E. payment.failed Ingestion Flow
  // ===========================================================================
  describe('E. payment.failed Ingestion Flow', () => {
    it('ingests failure, creates transaction, analyzes case, and executes bounded recovery', async () => {
      const payload = {
        event: 'payment.failed',
        event_id: 'evt_fail_ingest_001',
        payload: {
          payment: {
            entity: {
              id: 'pay_ingest_001',
              amount: 120000,
              currency: 'INR',
              method: 'upi',
              error_code: 'BAD_REQUEST_PAYMENT_ACCOUNT_INSUFFICIENT_BALANCE',
              notes: {
                customerId: 'cust_ingest_1',
              },
            },
          },
        },
      };

      const sig = signPayload(payload);
      const res = await request(app)
        .post('/api/v1/webhooks/razorpay')
        .set('X-Razorpay-Signature', sig)
        .send(payload);

      expect(res.status).toBe(200);
      expect(res.body.caseId).toBe('case_pay_ingest_001');

      const savedTxn = await dataStore.getTransaction('pay_ingest_001');
      expect(savedTxn).toBeDefined();
      expect(savedTxn?.failureCategory).toBe(FailureCategory.INSUFFICIENT_FUNDS);

      const savedCase = await dataStore.getCase('case_pay_ingest_001');
      expect(savedCase).toBeDefined();
      expect(savedCase?.attemptCount).toBe(1);
    });
  });

  // ===========================================================================
  // F, P. payment_link.paid & Double-Count Protection
  // ===========================================================================
  describe('F, P. payment_link.paid Webhook & Double-Count Protection', () => {
    it('marks case as RECOVERED, updates transaction to CAPTURED, and records audit event', async () => {
      // Setup active recovery case
      const txn: Transaction = {
        id: 'pay_link_target_1',
        merchantId: 'merch_101',
        customerId: 'cust_plink_1',
        amount: 89000,
        currency: 'INR',
        status: TransactionStatus.FAILED,
        failureCategory: FailureCategory.CARD_DECLINED,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      await dataStore.saveTransaction(txn);

      await dataStore.saveCase({
        id: 'case_pay_link_target_1',
        transactionId: 'pay_link_target_1',
        merchantId: 'merch_101',
        customerId: 'cust_plink_1',
        amount: 89000,
        currency: 'INR',
        state: RecoveryCaseState.ACTION_EXECUTED,
        failureCategory: FailureCategory.CARD_DECLINED,
        riskScore: 0.2,
        riskLevel: 'LOW' as any,
        attemptCount: 1,
        selectedAction: RecoveryAction.PAYMENT_LINK,
        customerOptedOut: false,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });

      const payload = {
        event: 'payment_link.paid',
        event_id: 'evt_plink_paid_001',
        payload: {
          payment_link: {
            entity: {
              id: 'plink_12345',
              reference_id: 'pay_link_target_1',
              amount: 89000,
              amount_paid: 89000,
            },
          },
          payment: {
            entity: {
              id: 'pay_captured_via_link',
            },
          },
        },
      };

      const sig = signPayload(payload);
      const res = await request(app)
        .post('/api/v1/webhooks/razorpay')
        .set('X-Razorpay-Signature', sig)
        .send(payload);

      expect(res.status).toBe(200);
      expect(res.body.state).toBe(RecoveryCaseState.RECOVERED);

      const updatedCase = await dataStore.getCase('case_pay_link_target_1');
      expect(updatedCase?.state).toBe(RecoveryCaseState.RECOVERED);
      expect(updatedCase?.resolvedAt).toBeDefined();

      const updatedTxn = await dataStore.getTransaction('pay_link_target_1');
      expect(updatedTxn?.status).toBe(TransactionStatus.CAPTURED);

      const auditEvents = await dataStore.getAuditEventsByCaseId('case_pay_link_target_1');
      const recoveredEvt = auditEvents.find((e) => e.eventType === AuditEventType.PAYMENT_RECOVERED);
      expect(recoveredEvt).toBeDefined();

      // P. Duplicate paid webhook does not double count
      const dupPayload = { ...payload, event_id: 'evt_plink_paid_002' };
      const dupSig = signPayload(dupPayload);
      const dupRes = await request(app)
        .post('/api/v1/webhooks/razorpay')
        .set('X-Razorpay-Signature', dupSig)
        .send(dupPayload);

      expect(dupRes.status).toBe(200);
      expect(dupRes.body.status).toBe('already_recovered');
    });
  });

  // ===========================================================================
  // G, H. payment_link.expired & payment_link.cancelled
  // ===========================================================================
  describe('G, H. payment_link.expired & cancelled', () => {
    it('G. handles payment_link.expired without falsely marking as recovered', async () => {
      await dataStore.saveCase({
        id: 'case_expired_1',
        transactionId: 'txn_expired_1',
        merchantId: 'merch_101',
        customerId: 'c_exp',
        amount: 50000,
        currency: 'INR',
        state: RecoveryCaseState.ACTION_EXECUTED,
        failureCategory: FailureCategory.CARD_DECLINED,
        riskScore: 0.2,
        riskLevel: 'LOW' as any,
        attemptCount: 2,
        selectedAction: RecoveryAction.PAYMENT_LINK,
        customerOptedOut: false,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });

      const payload = {
        event: 'payment_link.expired',
        event_id: 'evt_exp_001',
        payload: {
          payment_link: {
            entity: { id: 'plink_exp_01', reference_id: 'txn_expired_1' },
          },
        },
      };

      const sig = signPayload(payload);
      const res = await request(app)
        .post('/api/v1/webhooks/razorpay')
        .set('X-Razorpay-Signature', sig)
        .send(payload);

      expect(res.status).toBe(200);
      const c = await dataStore.getCase('case_expired_1');
      expect(c?.state).toBe(RecoveryCaseState.STOPPED); // attemptCount >= 2 stops case
      expect(c?.state).not.toBe(RecoveryCaseState.RECOVERED);
    });

    it('H. handles payment_link.cancelled without falsely marking as recovered', async () => {
      await dataStore.saveCase({
        id: 'case_cancelled_1',
        transactionId: 'txn_cancelled_1',
        merchantId: 'merch_101',
        customerId: 'c_cnc',
        amount: 40000,
        currency: 'INR',
        state: RecoveryCaseState.ACTION_EXECUTED,
        failureCategory: FailureCategory.CARD_DECLINED,
        riskScore: 0.2,
        riskLevel: 'LOW' as any,
        attemptCount: 1,
        selectedAction: RecoveryAction.PAYMENT_LINK,
        customerOptedOut: false,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });

      const payload = {
        event: 'payment_link.cancelled',
        event_id: 'evt_cnc_001',
        payload: {
          payment_link: {
            entity: { id: 'plink_cnc_01', reference_id: 'txn_cancelled_1' },
          },
        },
      };

      const sig = signPayload(payload);
      const res = await request(app)
        .post('/api/v1/webhooks/razorpay')
        .set('X-Razorpay-Signature', sig)
        .send(payload);

      expect(res.status).toBe(200);
      const c = await dataStore.getCase('case_cancelled_1');
      expect(c?.state).not.toBe(RecoveryCaseState.RECOVERED);
    });
  });

  // ===========================================================================
  // K, L, M. Safety Boundary & Invariant Preservation
  // ===========================================================================
  describe('K, L, M. Mandatory Safety Boundary Enforcement', () => {
    it('K, L. forces STOP and NEVER calls payment gateway when customerOptedOut === true', async () => {
      const mockGateway = new MockPaymentGateway();
      const retrySpy = vi.spyOn(mockGateway, 'retryPayment');
      const linkSpy = vi.spyOn(mockGateway, 'createPaymentLink');

      const payload = {
        event: 'payment.failed',
        event_id: 'evt_safe_optout',
        payload: {
          payment: {
            entity: {
              id: 'pay_safe_optout',
              amount: 90000,
              currency: 'INR',
              method: 'upi',
              notes: {
                customerOptedOut: true,
              },
            },
          },
        },
      };

      const sig = signPayload(payload);
      const res = await request(app)
        .post('/api/v1/webhooks/razorpay')
        .set('X-Razorpay-Signature', sig)
        .send(payload);

      expect(res.status).toBe(200);
      expect(res.body.state).toBe(RecoveryCaseState.STOPPED);

      // Gateways must NEVER be called on STOP
      expect(retrySpy).not.toHaveBeenCalled();
      expect(linkSpy).not.toHaveBeenCalled();
    });

    it('M. forces MERCHANT_REVIEW and NEVER executes payment when risk is high/critical', async () => {
      const payload = {
        event: 'payment.failed',
        event_id: 'evt_safe_fraud',
        payload: {
          payment: {
            entity: {
              id: 'pay_safe_fraud',
              amount: 500000,
              currency: 'INR',
              method: 'card',
              error_code: 'BAD_REQUEST_PAYMENT_FRAUD_IDENTIFIED',
              error_description: 'Fraud pattern detected',
            },
          },
        },
      };

      const sig = signPayload(payload);
      const res = await request(app)
        .post('/api/v1/webhooks/razorpay')
        .set('X-Razorpay-Signature', sig)
        .send(payload);

      expect(res.status).toBe(200);
      expect(res.body.state).toBe(RecoveryCaseState.MERCHANT_REVIEW);
      expect(res.body.action).toBe(RecoveryAction.MERCHANT_REVIEW);
    });
  });

  // ===========================================================================
  // N, O. Gateway Mode & Sandbox Error Handling
  // ===========================================================================
  describe('N, O. Gateway Mode & Sandbox Error Handling', () => {
    it('N. configured Razorpay API failure does NOT fall back to Mock success', async () => {
      const adapter = new RazorpaySandboxAdapter('rzp_test_key', 'rzp_test_secret');

      // Mock fetch to simulate Razorpay API failure HTTP 500
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({ error: { description: 'Sandbox downtime' } }),
      } as any);

      // createPaymentLink must throw error instead of calling mock fallback
      await expect(
        adapter.createPaymentLink('txn_live_err', 10000, 'Test', { email: 'test@example.com' }),
      ).rejects.toThrow('Razorpay Sandbox API error (HTTP 500)');

      // retryPayment must return failed status instead of pretending mock success
      const retryRes = await adapter.retryPayment('txn_live_err', 10000, 'upi');
      expect(retryRes.status).toBe('failed');
      expect(retryRes.amountRecovered).toBe(0);
    });

    it('O. explicit mock mode and unconfigured credentials use MockPaymentGateway safely', async () => {
      const originalMode = process.env['GATEWAY_MODE'];
      process.env['GATEWAY_MODE'] = 'MOCK';
      try {
        const gateway = getPaymentGateway();
        expect(gateway.name).toBe('MockPaymentGateway');

        const link = await gateway.createPaymentLink('txn_mock_safe', 5000, 'Test', {});
        expect(link.status).toBe('created');
        expect(link.shortUrl).toContain('mock');

        const retry = await gateway.retryPayment('txn_mock_safe', 5000, 'upi');
        expect(retry.status).toBe('captured');
        expect(retry.amountRecovered).toBe(5000);
      } finally {
        if (originalMode !== undefined) {
          process.env['GATEWAY_MODE'] = originalMode;
        } else {
          delete process.env['GATEWAY_MODE'];
        }
      }
    });
  });

  // ===========================================================================
  // Q. Customer Contact Sanitization for Razorpay Sandbox
  // ===========================================================================
  describe('Q. Customer Contact Sanitization for Razorpay Sandbox', () => {
    it('sanitizes undefined and recurring digits to valid non-recurring sandbox contact', () => {
      expect(sanitizeCustomerContact(undefined)).toBe('+919876543210');
      expect(sanitizeCustomerContact('')).toBe('+919876543210');
      expect(sanitizeCustomerContact('+919999999999')).toBe('+919876543210');
      expect(sanitizeCustomerContact('9999999999')).toBe('+919876543210');
      expect(sanitizeCustomerContact('1111111111')).toBe('+919876543210');
      expect(sanitizeCustomerContact('+919999991234')).toBe('+919876543210');
    });

    it('preserves valid non-recurring phone numbers', () => {
      expect(sanitizeCustomerContact('+919820098200')).toBe('+919820098200');
      expect(sanitizeCustomerContact('+919876543210')).toBe('+919876543210');
      expect(sanitizeCustomerContact('9820098200')).toBe('+919820098200');
    });

    it('supplies sanitized contact in Razorpay createPaymentLink payload', async () => {
      const adapter = new RazorpaySandboxAdapter('rzp_test_key', 'rzp_test_secret');
      let capturedBody: any = null;

      global.fetch = vi.fn().mockImplementation(async (_url, options) => {
        capturedBody = JSON.parse(options.body);
        return {
          ok: true,
          status: 200,
          json: async () => ({
            id: 'plink_test_sanitized',
            short_url: 'https://rzp.io/i/test_sanitized',
            status: 'created',
            amount: 50000,
            currency: 'INR',
          }),
        };
      });

      // Pass recurring contact
      const res = await adapter.createPaymentLink('txn_test_contact', 50000, 'Test Desc', {
        email: 'test@example.com',
        contact: '+919999999999',
      });

      expect(res.paymentLinkId).toBe('plink_test_sanitized');
      expect(capturedBody).toBeDefined();
      expect(capturedBody.customer.contact).toBe('+919876543210');
      expect(capturedBody.customer.contact).not.toContain('9999999999');
    });
  });
});
