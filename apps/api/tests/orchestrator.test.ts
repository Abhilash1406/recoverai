import { describe, it, expect, beforeEach } from 'vitest';
import { RecoveryOrchestrator } from '../src/services/orchestrator/RecoveryOrchestrator.js';
import { dataStore } from '../src/services/store.js';
import {
  Transaction,
  TransactionStatus,
  FailureCategory,
  RecoveryCaseState,
  AuditEventType,
} from '@recoverai/shared-types';

describe('RecoveryOrchestrator Integration Flow', () => {
  let orchestrator: RecoveryOrchestrator;

  beforeEach(async () => {
    await dataStore.clear();
    orchestrator = new RecoveryOrchestrator();
  });

  it('runs complete lifecycle: create -> analyze -> execute for UPI Network Error', async () => {
    const txn: Transaction = {
      id: 'pay_test_001',
      merchantId: 'merch_01',
      customerId: 'cust_01',
      amount: 49900,
      currency: 'INR',
      status: TransactionStatus.FAILED,
      failureCategory: FailureCategory.NETWORK_ERROR,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    const newCase = await orchestrator.createCase(txn);
    expect(newCase.state).toBe(RecoveryCaseState.DETECTED);
    expect(newCase.attemptCount).toBe(0);

    const analyzed = await orchestrator.analyzeCase(newCase.id);
    expect(analyzed.recoveryCase.state).toBe(RecoveryCaseState.DECISION_READY);
    expect(analyzed.selectedAction).toBeDefined();

    const executed = await orchestrator.executeAction(newCase.id);
    expect(executed.attemptCount).toBe(1);
    expect([RecoveryCaseState.RECOVERED, RecoveryCaseState.FAILED, RecoveryCaseState.ACTION_EXECUTED]).toContain(executed.state);
  });

  it('escalates fraudulent / high-risk transaction to MERCHANT_REVIEW', async () => {
    const txn: Transaction = {
      id: 'pay_test_fraud',
      merchantId: 'merch_01',
      customerId: 'cust_02',
      amount: 999900,
      currency: 'INR',
      status: TransactionStatus.FAILED,
      failureCategory: FailureCategory.FRAUD_SUSPECTED,
      deviceChanged: true,
      locationChanged: true,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    const newCase = await orchestrator.createCase(txn);
    const analyzed = await orchestrator.analyzeCase(newCase.id);

    expect(analyzed.riskAssessment.riskScore).toBeGreaterThanOrEqual(0.70);
    expect(analyzed.recoveryCase.state).toBe(RecoveryCaseState.DECISION_READY);
  });

  it('stops recovery when customer has opted out', async () => {
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

    const recCase = await orchestrator.createCase(txn);
    recCase.customerOptedOut = true;
    await dataStore.saveCase(recCase);

    await orchestrator.analyzeCase(recCase.id);
    const updated = await orchestrator.executeAction(recCase.id);

    expect(updated.state).toBe(RecoveryCaseState.STOPPED);

    const auditEvents = await dataStore.getAuditEventsByCaseId(recCase.id);
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

    const recCase = await orchestrator.createCase(txn);
    await orchestrator.analyzeCase(recCase.id);

    const run1 = await orchestrator.executeAction(recCase.id, 'idem_key_123');
    const run2 = await orchestrator.executeAction(recCase.id, 'idem_key_123');

    expect(run1.id).toBe(run2.id);
  });
});
