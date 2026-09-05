import {
  Transaction,
  RiskAssessment,
  RecoveryAction,
  PolicyResult,
  PolicyEvaluation,
  RiskLevel,
  TransactionStatus,
} from '@recoverai/shared-types';

export const MIN_RECOVERY_PROBABILITY = 0.60;
export const HIGH_RISK_THRESHOLD = 0.70;
export const MAX_AUTOMATIC_ACTIONS = 2;
export const MAX_RETRIES = 2;

export interface PolicyContext {
  transaction: Transaction;
  riskAssessment: RiskAssessment;
  proposedAction: RecoveryAction;
  attemptCount: number;
  customerOptedOut: boolean;
  recoveryProbability?: number;
  merchantOverride?: boolean;
}

export interface PolicyRuleResult {
  ruleName: string;
  passed: boolean;
  reason?: string;
}

export enum PolicyRuleName {
  MAX_RETRIES = 'MAX_RETRIES',
  MAX_AUTO_ACTIONS = 'MAX_AUTO_ACTIONS',
  HIGH_RISK_BLOCK = 'HIGH_RISK_BLOCK',
  PAYMENT_STATE_VALID = 'PAYMENT_STATE_VALID',
  CUSTOMER_OPT_OUT = 'CUSTOMER_OPT_OUT',
  MIN_RECOVERY_PROBABILITY = 'MIN_RECOVERY_PROBABILITY',
  HIGH_VALUE_ESCALATION = 'HIGH_VALUE_ESCALATION',
  STOPPING_RULE = 'STOPPING_RULE',
}

export function evaluatePolicy(context: PolicyContext): PolicyEvaluation {
  const {
    transaction,
    riskAssessment,
    proposedAction,
    attemptCount,
    customerOptedOut,
    recoveryProbability = 0.60,
  } = context;

  const violatedRules: string[] = [];

  // Rule 1: Customer Opt-Out Rule
  if (customerOptedOut && proposedAction !== RecoveryAction.STOP) {
    violatedRules.push(PolicyRuleName.CUSTOMER_OPT_OUT);
  }

  // Rule 2: High Risk Block Rule
  if (
    (riskAssessment.riskScore >= HIGH_RISK_THRESHOLD ||
      riskAssessment.riskLevel === RiskLevel.HIGH ||
      riskAssessment.riskLevel === RiskLevel.CRITICAL) &&
    proposedAction !== RecoveryAction.MERCHANT_REVIEW &&
    proposedAction !== RecoveryAction.STOP
  ) {
    violatedRules.push(PolicyRuleName.HIGH_RISK_BLOCK);
  }

  // Rule 3: Max Retries Rule
  if (attemptCount >= MAX_RETRIES && proposedAction === RecoveryAction.RETRY) {
    violatedRules.push(PolicyRuleName.MAX_RETRIES);
  }

  // Rule 4: Max Automatic Actions Rule
  if (attemptCount >= MAX_AUTOMATIC_ACTIONS && proposedAction !== RecoveryAction.STOP && proposedAction !== RecoveryAction.MERCHANT_REVIEW) {
    violatedRules.push(PolicyRuleName.MAX_AUTO_ACTIONS);
  }

  // Rule 5: Payment State Validity
  if (transaction.status === TransactionStatus.CAPTURED || transaction.status === TransactionStatus.REFUNDED) {
    violatedRules.push(PolicyRuleName.PAYMENT_STATE_VALID);
  }

  // Rule 6: Minimum Recovery Probability Rule
  if (recoveryProbability < MIN_RECOVERY_PROBABILITY && proposedAction !== RecoveryAction.STOP) {
    violatedRules.push(PolicyRuleName.MIN_RECOVERY_PROBABILITY);
  }

  let result = PolicyResult.ALLOW;
  if (violatedRules.length > 0) {
    if (violatedRules.includes(PolicyRuleName.HIGH_RISK_BLOCK)) {
      result = PolicyResult.REQUIRE_REVIEW;
    } else {
      result = PolicyResult.BLOCK;
    }
  }

  return {
    transactionId: transaction.id,
    decisionId: `dec_pol_${transaction.id}_${Date.now()}`,
    result,
    violatedRules,
    evaluatedAt: new Date().toISOString(),
  };
}

export { PolicyResult } from '@recoverai/shared-types';
