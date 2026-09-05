import {
  Transaction,
  FailureCategory,
  RiskLevel,
  RiskAssessment,
  RecoveryCase,
  RecoveryCaseState,
  RecoveryAction,
  Decision,
  PolicyResult,
  AuditEventType,
  AuditEvent,
  NotificationChannel,
} from '@recoverai/shared-types';
import { evaluateActions, ScoredAction } from '@recoverai/decision-engine';
import { evaluatePolicy, HIGH_RISK_THRESHOLD, MAX_AUTOMATIC_ACTIONS } from '@recoverai/policy-engine';
import { dataStore } from '../store.js';
import { RazorpaySandboxAdapter } from '../payment/RazorpaySandboxAdapter.js';
import { notificationService } from '../notification/NotificationService.js';
import { geminiAgentService } from '../ai/GeminiAgent.js';

export interface ProcessCaseResult {
  recoveryCase: RecoveryCase;
  riskAssessment: RiskAssessment;
  decision: Decision;
  candidateScores: ScoredAction[];
  selectedAction: RecoveryAction;
  policyResult: PolicyResult;
  violatedRules: string[];
  explanation: any;
  auditEvents: AuditEvent[];
}

export class RecoveryOrchestrator {
  private paymentGateway: RazorpaySandboxAdapter;

  constructor() {
    this.paymentGateway = new RazorpaySandboxAdapter();
  }

  public async createCase(txn: Transaction): Promise<RecoveryCase> {
    dataStore.saveTransaction(txn);

    const customer = dataStore.getCustomer(txn.customerId) || {
      customerId: txn.customerId,
      merchantId: txn.merchantId,
      optedOut: false,
    };
    dataStore.saveCustomer(customer);

    const caseId = `case_${txn.id}`;
    const newCase: RecoveryCase = {
      id: caseId,
      transactionId: txn.id,
      merchantId: txn.merchantId,
      customerId: txn.customerId,
      amount: txn.amount,
      currency: txn.currency || 'INR',
      state: RecoveryCaseState.DETECTED,
      failureCategory: txn.failureCategory || FailureCategory.UNKNOWN,
      failureCode: txn.failureCode,
      riskScore: 0.1,
      riskLevel: RiskLevel.LOW,
      attemptCount: 0,
      customerOptedOut: customer.optedOut,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    dataStore.saveCase(newCase);

    dataStore.addAuditEvent({
      id: `evt_create_${caseId}_${Date.now()}`,
      caseId,
      transactionId: txn.id,
      eventType: AuditEventType.CASE_CREATED,
      actor: 'SYSTEM',
      timestamp: new Date().toISOString(),
      reason: 'Failed transaction detected by RecoverAI monitor.',
      details: { amount: txn.amount, failureCategory: txn.failureCategory },
    });

    return newCase;
  }

  public async analyzeCase(caseId: string): Promise<ProcessCaseResult> {
    const recCase = dataStore.getCase(caseId);
    if (!recCase) {
      throw new Error(`RecoveryCase ${caseId} not found.`);
    }

    const txn = dataStore.getTransaction(recCase.transactionId);
    if (!txn) {
      throw new Error(`Transaction ${recCase.transactionId} not found.`);
    }

    recCase.state = RecoveryCaseState.ANALYZING;
    recCase.updatedAt = new Date().toISOString();
    dataStore.saveCase(recCase);

    let riskScore = 0.15;
    if (txn.failureCategory === FailureCategory.FRAUD_SUSPECTED) riskScore = 0.85;
    else if (txn.failureCategory === FailureCategory.CARD_DECLINED) riskScore = 0.40;
    if (txn.deviceChanged) riskScore += 0.20;
    if (txn.locationChanged) riskScore += 0.15;
    riskScore = Math.min(1.0, Math.max(0.0, riskScore));

    let riskLevel = RiskLevel.LOW;
    if (riskScore >= HIGH_RISK_THRESHOLD) riskLevel = RiskLevel.CRITICAL;
    else if (riskScore >= 0.50) riskLevel = RiskLevel.HIGH;
    else if (riskScore >= 0.30) riskLevel = RiskLevel.MEDIUM;

    recCase.riskScore = riskScore;
    recCase.riskLevel = riskLevel;

    const riskAssessment: RiskAssessment = {
      transactionId: txn.id,
      riskLevel,
      riskScore,
      confidence: 0.92,
      factors: [
        `Failure Category: ${txn.failureCategory}`,
        txn.deviceChanged ? 'Device change detected' : 'Known customer device',
        txn.locationChanged ? 'Location change detected' : 'Standard location',
      ],
      assessedAt: new Date().toISOString(),
    };

    dataStore.addAuditEvent({
      id: `evt_risk_${caseId}_${Date.now()}`,
      caseId,
      transactionId: txn.id,
      eventType: AuditEventType.RISK_ASSESSED,
      actor: 'ML_ENGINE',
      timestamp: new Date().toISOString(),
      reason: `Assessed risk score ${riskScore.toFixed(2)} (${riskLevel}).`,
      details: { riskScore, riskLevel },
    });

    const decisionResult = evaluateActions({
      transaction: txn,
      riskAssessment,
      attemptCount: recCase.attemptCount,
      customerOptedOut: recCase.customerOptedOut,
    });

    const policyEval = evaluatePolicy({
      transaction: txn,
      riskAssessment,
      proposedAction: decisionResult.topAction.action,
      attemptCount: recCase.attemptCount,
      customerOptedOut: recCase.customerOptedOut,
      recoveryProbability: decisionResult.topAction.recoveryProbability,
    });

    const finalDecision = decisionResult.decision;
    dataStore.saveDecision(finalDecision);

    dataStore.addAuditEvent({
      id: `evt_rank_${caseId}_${Date.now()}`,
      caseId,
      transactionId: txn.id,
      eventType: AuditEventType.ACTION_RANKED,
      actor: 'ML_ENGINE',
      timestamp: new Date().toISOString(),
      reason: `Ranked candidate actions by Expected Utility. Top action: ${decisionResult.topAction.action}.`,
      details: { topAction: decisionResult.topAction.action, expectedUtility: decisionResult.topAction.expectedUtility },
    });

    if (policyEval.result === PolicyResult.BLOCK) {
      dataStore.addAuditEvent({
        id: `evt_pol_${caseId}_${Date.now()}`,
        caseId,
        transactionId: txn.id,
        eventType: AuditEventType.POLICY_REJECTED,
        actor: 'POLICY_GATE',
        timestamp: new Date().toISOString(),
        reason: `Policy Gate blocked action: ${policyEval.violatedRules.join(', ')}.`,
        details: { violatedRules: policyEval.violatedRules },
      });
    }

    const explanation = await geminiAgentService.explainDecision({
      transaction: txn,
      riskAssessment,
      decision: finalDecision,
      candidateScores: decisionResult.scoredActions,
      selectedAction: decisionResult.topAction.action,
    });

    recCase.state = RecoveryCaseState.DECISION_READY;
    recCase.currentDecisionId = finalDecision.id;
    recCase.selectedAction = decisionResult.topAction.action;
    recCase.explanation = explanation.summary;
    recCase.updatedAt = new Date().toISOString();
    dataStore.saveCase(recCase);

    const auditEvents = dataStore.getAuditEventsByCaseId(caseId);

    return {
      recoveryCase: recCase,
      riskAssessment,
      decision: finalDecision,
      candidateScores: decisionResult.scoredActions,
      selectedAction: decisionResult.topAction.action,
      policyResult: policyEval.result,
      violatedRules: policyEval.violatedRules,
      explanation,
      auditEvents,
    };
  }

  public async executeAction(caseId: string, idempotencyKey?: string): Promise<RecoveryCase> {
    if (idempotencyKey) {
      const isFresh = dataStore.checkAndSetIdempotency(idempotencyKey);
      if (!isFresh) {
        const existing = dataStore.getCase(caseId);
        if (existing) return existing;
      }
    }

    const recCase = dataStore.getCase(caseId);
    if (!recCase) {
      throw new Error(`RecoveryCase ${caseId} not found.`);
    }

    const action = recCase.selectedAction || RecoveryAction.RETRY;

    // --- SERVER-SIDE SAFETY BOUNDARY CHECKS ---
    // Rule 1: Customer Opt-out Check
    if (recCase.customerOptedOut) {
      recCase.state = RecoveryCaseState.STOPPED;
      recCase.updatedAt = new Date().toISOString();
      dataStore.saveCase(recCase);

      dataStore.addAuditEvent({
        id: `evt_optout_${caseId}_${Date.now()}`,
        caseId,
        transactionId: recCase.transactionId,
        eventType: AuditEventType.CUSTOMER_OPTED_OUT,
        actor: 'POLICY_GATE',
        timestamp: new Date().toISOString(),
        reason: 'Recovery action cancelled at boundary: Customer opted out of communications.',
      });
      dataStore.addAuditEvent({
        id: `evt_stop_opt_${caseId}_${Date.now()}`,
        caseId,
        transactionId: recCase.transactionId,
        eventType: AuditEventType.RECOVERY_STOPPED,
        actor: 'POLICY_GATE',
        timestamp: new Date().toISOString(),
        reason: 'Recovery stopped automatically by safety policy rules (Customer opted out).',
      });

      return recCase;
    }

    // Rule 2: High/Critical Risk Escalation Check
    if (
      (recCase.riskScore >= HIGH_RISK_THRESHOLD ||
        recCase.riskLevel === RiskLevel.HIGH ||
        recCase.riskLevel === RiskLevel.CRITICAL) &&
      action !== RecoveryAction.MERCHANT_REVIEW &&
      action !== RecoveryAction.STOP
    ) {
      recCase.state = RecoveryCaseState.MERCHANT_REVIEW;
      recCase.selectedAction = RecoveryAction.MERCHANT_REVIEW;
      recCase.updatedAt = new Date().toISOString();
      dataStore.saveCase(recCase);

      dataStore.addAuditEvent({
        id: `evt_mreview_gate_${caseId}_${Date.now()}`,
        caseId,
        transactionId: recCase.transactionId,
        eventType: AuditEventType.MERCHANT_REVIEW_REQUIRED,
        actor: 'POLICY_GATE',
        timestamp: new Date().toISOString(),
        reason: `Case escalated at boundary to merchant review due to high risk (${recCase.riskScore.toFixed(2)}).`,
      });

      return recCase;
    }

    // Rule 3: Amount Validation
    if (recCase.amount <= 0) {
      recCase.state = RecoveryCaseState.STOPPED;
      recCase.updatedAt = new Date().toISOString();
      dataStore.saveCase(recCase);

      dataStore.addAuditEvent({
        id: `evt_stop_invalid_amt_${caseId}_${Date.now()}`,
        caseId,
        transactionId: recCase.transactionId,
        eventType: AuditEventType.RECOVERY_STOPPED,
        actor: 'POLICY_GATE',
        timestamp: new Date().toISOString(),
        reason: 'Recovery stopped: Invalid transaction amount (<= 0).',
      });

      return recCase;
    }

    // Rule 4: STOP Action Safety Guarantee
    if (action === RecoveryAction.STOP) {
      recCase.state = RecoveryCaseState.STOPPED;
      recCase.updatedAt = new Date().toISOString();
      dataStore.saveCase(recCase);

      dataStore.addAuditEvent({
        id: `evt_stop_${caseId}_${Date.now()}`,
        caseId,
        transactionId: recCase.transactionId,
        eventType: AuditEventType.RECOVERY_STOPPED,
        actor: 'POLICY_GATE',
        timestamp: new Date().toISOString(),
        reason: 'Recovery stopped automatically by safety policy rules.',
      });

      return recCase;
    }

    // Rule 5: Maximum Automatic Actions Boundary Check
    if (recCase.attemptCount >= MAX_AUTOMATIC_ACTIONS && action !== RecoveryAction.MERCHANT_REVIEW) {
      recCase.state = RecoveryCaseState.STOPPED;
      recCase.updatedAt = new Date().toISOString();
      dataStore.saveCase(recCase);

      dataStore.addAuditEvent({
        id: `evt_stop_maxauto_${caseId}_${Date.now()}`,
        caseId,
        transactionId: recCase.transactionId,
        eventType: AuditEventType.RECOVERY_STOPPED,
        actor: 'POLICY_GATE',
        timestamp: new Date().toISOString(),
        reason: `Recovery stopped: Maximum automatic actions threshold (${MAX_AUTOMATIC_ACTIONS}) reached.`,
      });

      return recCase;
    }

    recCase.state = RecoveryCaseState.ACTION_PENDING;
    recCase.attemptCount += 1;
    recCase.updatedAt = new Date().toISOString();
    dataStore.saveCase(recCase);

    dataStore.addAuditEvent({
      id: `evt_sel_${caseId}_${Date.now()}`,
      caseId,
      transactionId: recCase.transactionId,
      eventType: AuditEventType.ACTION_SELECTED,
      actor: 'SYSTEM',
      timestamp: new Date().toISOString(),
      reason: `Executing bounded action ${action}.`,
      details: { action, attemptCount: recCase.attemptCount },
    });

    if (action === RecoveryAction.RETRY) {
      const result = await this.paymentGateway.retryPayment(recCase.transactionId, recCase.amount, 'upi');
      if (result.status === 'captured') {
        recCase.state = RecoveryCaseState.RECOVERED;
        recCase.resolvedAt = new Date().toISOString();
        dataStore.saveCase(recCase);

        dataStore.addAuditEvent({
          id: `evt_exec_${caseId}_${Date.now()}`,
          caseId,
          transactionId: recCase.transactionId,
          eventType: AuditEventType.PAYMENT_RECOVERED,
          actor: 'SYSTEM',
          timestamp: new Date().toISOString(),
          reason: `Payment successfully recovered via RETRY attempt. Amount: ₹${(recCase.amount / 100).toFixed(2)}.`,
          details: { retryId: result.retryId, amountRecovered: result.amountRecovered },
        });
      } else {
        recCase.state = RecoveryCaseState.FAILED;
        dataStore.saveCase(recCase);

        dataStore.addAuditEvent({
          id: `evt_exec_fail_${caseId}_${Date.now()}`,
          caseId,
          transactionId: recCase.transactionId,
          eventType: AuditEventType.PAYMENT_FAILED,
          actor: 'SYSTEM',
          timestamp: new Date().toISOString(),
          reason: `RETRY attempt declined by gateway.`,
        });
      }
    } else if (action === RecoveryAction.PAYMENT_LINK) {
      const linkResult = await this.paymentGateway.createPaymentLink(
        recCase.transactionId,
        recCase.amount,
        `Payment Recovery for ${recCase.transactionId}`,
        { email: 'customer@example.com' },
      );

      const notif = await notificationService.sendNotification({
        caseId,
        customerId: recCase.customerId,
        channel: NotificationChannel.SMS,
        template: 'RECOVERY_PAYMENT_LINK',
        messageBody: `Payment required: ${linkResult.shortUrl}`,
        customerOptedOut: recCase.customerOptedOut,
      });

      if (notif.status === 'BLOCKED') {
        recCase.state = RecoveryCaseState.STOPPED;
        dataStore.saveCase(recCase);

        dataStore.addAuditEvent({
          id: `evt_optout_${caseId}_${Date.now()}`,
          caseId,
          transactionId: recCase.transactionId,
          eventType: AuditEventType.CUSTOMER_OPTED_OUT,
          actor: 'POLICY_GATE',
          timestamp: new Date().toISOString(),
          reason: 'Recovery action cancelled: Customer opted out of communications.',
        });
      } else {
        recCase.state = RecoveryCaseState.ACTION_EXECUTED;
        dataStore.saveCase(recCase);

        dataStore.addAuditEvent({
          id: `evt_exec_link_${caseId}_${Date.now()}`,
          caseId,
          transactionId: recCase.transactionId,
          eventType: AuditEventType.ACTION_EXECUTED,
          actor: 'SYSTEM',
          timestamp: new Date().toISOString(),
          reason: `Payment link created (${linkResult.shortUrl}) and dispatched to customer.`,
          details: { linkId: linkResult.paymentLinkId, url: linkResult.shortUrl },
        });
      }
    } else if (action === RecoveryAction.MERCHANT_REVIEW) {
      recCase.state = RecoveryCaseState.MERCHANT_REVIEW;
      dataStore.saveCase(recCase);

      dataStore.addAuditEvent({
        id: `evt_mreview_${caseId}_${Date.now()}`,
        caseId,
        transactionId: recCase.transactionId,
        eventType: AuditEventType.MERCHANT_REVIEW_REQUIRED,
        actor: 'POLICY_GATE',
        timestamp: new Date().toISOString(),
        reason: 'Case escalated to merchant review due to high risk assessment.',
      });
    }

    recCase.updatedAt = new Date().toISOString();
    return dataStore.saveCase(recCase);
  }

  public async stopCase(caseId: string, reason: string): Promise<RecoveryCase> {
    const recCase = dataStore.getCase(caseId);
    if (!recCase) throw new Error(`RecoveryCase ${caseId} not found.`);

    recCase.state = RecoveryCaseState.STOPPED;
    recCase.updatedAt = new Date().toISOString();
    dataStore.saveCase(recCase);

    dataStore.addAuditEvent({
      id: `evt_stop_man_${caseId}_${Date.now()}`,
      caseId,
      transactionId: recCase.transactionId,
      eventType: AuditEventType.RECOVERY_STOPPED,
      actor: 'MERCHANT',
      timestamp: new Date().toISOString(),
      reason,
    });

    return recCase;
  }
}

export const recoveryOrchestrator = new RecoveryOrchestrator();
