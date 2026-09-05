import { describe, it, expect, beforeEach } from 'vitest';
import { recoveryOrchestrator } from '../src/services/orchestrator/RecoveryOrchestrator.js';
import { dataStore } from '../src/services/store.js';
import {
  Transaction,
  TransactionStatus,
  FailureCategory,
  RecoveryAction,
  RecoveryCaseState,
  AuditEventType,
} from '@recoverai/shared-types';

describe('RecoveryOrchestrator Lifecycle Tests', () => {
  beforeEach(() => {
    dataStore.clear();
  });

  it('creates a new recovery case and audit record', async () => {
    const txn: Transaction = {
      id: 'pay_test_01',
      merchantId: 'merch_01',
      customerId: 'cust_01',
      amount: 500000,
      currency: 'INR',
      status: TransactionStatus.FAILED,
      failureCategory: FailureCategory.INSUFFICIENT_FUNDS,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    const recCase = await recoveryOrchestrator.createCase(txn);
    expect(recCase.id).toBe('case_pay_test_01');
    expect(recCase.state).toBe(RecoveryCaseState.DETECTED);

    const auditEvents = dataStore.getAuditEventsByCaseId(recCase.id);
    expect(auditEvents.length).toBeGreaterThanOrEqual(1);
    expect(auditEvents[0]!.eventType).toBe(AuditEventType.CASE_CREATED);
  });

  it('analyzes a case, calculates Expected Utility, and applies Policy Gate', async () => {
    const txn: Transaction = {
      id: 'pay_test_02',
      merchantId: 'merch_01',
      customerId: 'cust_02',
      amount: 250000,
      currency: 'INR',
      status: TransactionStatus.FAILED,
      failureCategory: FailureCategory.CARD_DECLINED,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    const recCase = await recoveryOrchestrator.createCase(txn);
    const result = await recoveryOrchestrator.analyzeCase(recCase.id);

    expect(result.recoveryCase.state).toBe(RecoveryCaseState.DECISION_READY);
    expect(result.selectedAction).toBe(RecoveryAction.PAYMENT_LINK);
    expect(result.candidateScores.length).toBe(6);
    expect(result.explanation.summary).toBeDefined();
  });

  it('blocks communications if customer has opted out', async () => {
    const txn: Transaction = {
      id: 'pay_test_optout',
      merchantId: 'merch_01',
      customerId: 'cust_optout',
      amount: 100000,
      currency: 'INR',
      status: TransactionStatus.FAILED,
      failureCategory: FailureCategory.CARD_DECLINED,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    const recCase = await recoveryOrchestrator.createCase(txn);
    recCase.customerOptedOut = true;
    dataStore.saveCase(recCase);

    await recoveryOrchestrator.analyzeCase(recCase.id);
    const updated = await recoveryOrchestrator.executeAction(recCase.id);

    expect(updated.state).toBe(RecoveryCaseState.STOPPED);

    const auditEvents = dataStore.getAuditEventsByCaseId(recCase.id);
    const stoppedEvent = auditEvents.find((e) => e.eventType === AuditEventType.RECOVERY_STOPPED);
    expect(stoppedEvent).toBeDefined();
    expect(stoppedEvent?.reason).toContain('safety policy rules');
  });

  it('enforces idempotency on repeated action executions', async () => {
    const txn: Transaction = {
      id: 'pay_test_idem',
      merchantId: 'merch_01',
      customerId: 'cust_03',
      amount: 150000,
      currency: 'INR',
      status: TransactionStatus.FAILED,
      failureCategory: FailureCategory.NETWORK_ERROR,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    const recCase = await recoveryOrchestrator.createCase(txn);
    await recoveryOrchestrator.analyzeCase(recCase.id);

    const run1 = await recoveryOrchestrator.executeAction(recCase.id, 'idem_key_123');
    const run2 = await recoveryOrchestrator.executeAction(recCase.id, 'idem_key_123');

    expect(run1.id).toBe(run2.id);
  });
});
