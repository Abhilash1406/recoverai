import { describe, it, expect, beforeEach } from 'vitest';
import { RecoveryOrchestrator } from '../src/services/orchestrator/RecoveryOrchestrator.js';
import { dataStore } from '../src/services/store.js';
import { MockPaymentGateway } from '../src/services/payment/MockPaymentGateway.js';
import {
  Transaction,
  TransactionStatus,
  FailureCategory,
  RecoveryCaseState,
  RecoveryAction,
  AuditEventType,
} from '@recoverai/shared-types';

describe('Phase 4.5 Safety Boundary Hardening Tests', () => {
  let orchestrator: RecoveryOrchestrator;

  beforeEach(() => {
    dataStore.clear();
    orchestrator = new RecoveryOrchestrator();
  });

  it('enforces opt-out safety boundary: customerOptedOut === true guarantees STOP state and no gateway execution', async () => {
    const txn: Transaction = {
      id: 'pay_optout_test',
      merchantId: 'merch_101',
      customerId: 'cust_optout_1',
      amount: 50000,
      currency: 'INR',
      status: TransactionStatus.FAILED,
      failureCategory: FailureCategory.INSUFFICIENT_FUNDS,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    const recCase = await orchestrator.createCase(txn);
    recCase.customerOptedOut = true;
    recCase.selectedAction = RecoveryAction.RETRY;
    dataStore.saveCase(recCase);

    const resultCase = await orchestrator.executeAction(recCase.id);

    expect(resultCase.state).toBe(RecoveryCaseState.STOPPED);
    const auditEvents = dataStore.getAuditEventsByCaseId(recCase.id);
    const optOutEvt = auditEvents.find((e) => e.eventType === AuditEventType.CUSTOMER_OPTED_OUT);
    expect(optOutEvt).toBeDefined();
    expect(optOutEvt?.reason).toContain('Customer opted out');
  });

  it('enforces high-risk safety boundary: risk >= 0.70 escalates action to MERCHANT_REVIEW', async () => {
    const txn: Transaction = {
      id: 'pay_highrisk_test',
      merchantId: 'merch_101',
      customerId: 'cust_2',
      amount: 100000,
      currency: 'INR',
      status: TransactionStatus.FAILED,
      failureCategory: FailureCategory.FRAUD_SUSPECTED,
      deviceChanged: true,
      locationChanged: true,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    const recCase = await orchestrator.createCase(txn);
    recCase.riskScore = 0.85;
    recCase.selectedAction = RecoveryAction.RETRY;
    dataStore.saveCase(recCase);

    const resultCase = await orchestrator.executeAction(recCase.id);

    expect(resultCase.state).toBe(RecoveryCaseState.MERCHANT_REVIEW);
    expect(resultCase.selectedAction).toBe(RecoveryAction.MERCHANT_REVIEW);
    const auditEvents = dataStore.getAuditEventsByCaseId(recCase.id);
    const reviewEvt = auditEvents.find((e) => e.eventType === AuditEventType.MERCHANT_REVIEW_REQUIRED);
    expect(reviewEvt).toBeDefined();
  });

  it('rejects invalid/zero/negative amounts in MockPaymentGateway', async () => {
    const mockGw = new MockPaymentGateway();
    await expect(mockGw.createPaymentLink('txn_invalid', 0, 'desc', {})).rejects.toThrow(
      'Invalid payment amount: must be greater than zero.',
    );
    await expect(mockGw.retryPayment('txn_invalid', -500, 'upi')).rejects.toThrow(
      'Invalid payment amount: must be greater than zero.',
    );
  });

  it('handles idempotency keys cleanly to prevent duplicate executions', async () => {
    const txn: Transaction = {
      id: 'pay_idem_test',
      merchantId: 'merch_101',
      customerId: 'cust_3',
      amount: 49900,
      currency: 'INR',
      status: TransactionStatus.FAILED,
      failureCategory: FailureCategory.INSUFFICIENT_FUNDS,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    const recCase = await orchestrator.createCase(txn);
    await orchestrator.analyzeCase(recCase.id);

    const firstRun = await orchestrator.executeAction(recCase.id, 'idem_key_123');
    const secondRun = await orchestrator.executeAction(recCase.id, 'idem_key_123');

    expect(firstRun.id).toBe(secondRun.id);
    expect(secondRun.attemptCount).toBe(1);
  });

  it('handles zero-state analytics safely without NaN or divide-by-zero errors', () => {
    const summary = dataStore.getAnalyticsSummary();
    expect(summary.totalCases).toBe(0);
    expect(summary.totalRevenueAtRisk).toBe(0);
    expect(summary.totalRecoveredRevenue).toBe(0);
    expect(summary.recoveryRate).toBe(0);
    expect(summary.recoveryEfficiency).toBe(0);
    expect(summary.avgRecoveryTimeMinutes).toBe(0);
  });
});
