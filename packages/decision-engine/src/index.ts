import {
  Transaction,
  RiskAssessment,
  RecoveryAction,
  Decision,
  DecisionStatus,
  FailureCategory,
  RiskLevel,
} from '@recoverai/shared-types';
import { MIN_RECOVERY_PROBABILITY, HIGH_RISK_THRESHOLD, MAX_RETRIES } from '@recoverai/policy-engine';

export interface DecisionInput {
  transaction: Transaction;
  riskAssessment: RiskAssessment;
  candidateActions?: RecoveryAction[];
  attemptCount: number;
  customerOptedOut?: boolean;
}

export interface ScoredAction {
  action: RecoveryAction;
  expectedUtility: number;
  recoveryProbability: number;
  estimatedValue: number;
  allowed: boolean;
  rejectionReason?: string;
  costs: {
    risk: number;
    friction: number;
    action: number;
  };
}

export interface DecisionResult {
  decision: Decision;
  scoredActions: ScoredAction[];
  topAction: ScoredAction;
}

const ACTION_COSTS: Record<RecoveryAction, number> = {
  [RecoveryAction.WAIT]: 0,
  [RecoveryAction.RETRY]: 500,
  [RecoveryAction.PAYMENT_LINK]: 1000,
  [RecoveryAction.NOTIFICATION]: 200,
  [RecoveryAction.MERCHANT_REVIEW]: 2000,
  [RecoveryAction.STOP]: 0,
};

const FRICTION_COSTS: Record<RecoveryAction, number> = {
  [RecoveryAction.WAIT]: 0,
  [RecoveryAction.RETRY]: 100,
  [RecoveryAction.PAYMENT_LINK]: 500,
  [RecoveryAction.NOTIFICATION]: 300,
  [RecoveryAction.MERCHANT_REVIEW]: 0,
  [RecoveryAction.STOP]: 0,
};

function getBaseRecoveryProbability(category: FailureCategory, action: RecoveryAction): number {
  if (action === RecoveryAction.STOP) return 0.0;

  switch (category) {
    case FailureCategory.NETWORK_ERROR:
    case FailureCategory.BANK_TIMEOUT:
    case FailureCategory.INSUFFICIENT_FUNDS:
      if (action === RecoveryAction.RETRY) return 0.75;
      if (action === RecoveryAction.PAYMENT_LINK) return 0.65;
      if (action === RecoveryAction.NOTIFICATION) return 0.40;
      break;
    case FailureCategory.CARD_DECLINED:
    case FailureCategory.AUTHENTICATION_FAILED:
    case FailureCategory.INVALID_CVV:
    case FailureCategory.LIMIT_EXCEEDED:
      if (action === RecoveryAction.PAYMENT_LINK) return 0.80;
      if (action === RecoveryAction.NOTIFICATION) return 0.50;
      if (action === RecoveryAction.RETRY) return 0.25;
      break;
    case FailureCategory.FRAUD_SUSPECTED:
      if (action === RecoveryAction.MERCHANT_REVIEW) return 0.90;
      return 0.0;
    default:
      if (action === RecoveryAction.PAYMENT_LINK) return 0.60;
      if (action === RecoveryAction.RETRY) return 0.40;
  }
  return 0.10;
}

export function evaluateActions(input: DecisionInput): DecisionResult {
  const { transaction, riskAssessment, attemptCount, customerOptedOut } = input;
  const candidateActions = input.candidateActions || [
    RecoveryAction.RETRY,
    RecoveryAction.PAYMENT_LINK,
    RecoveryAction.NOTIFICATION,
    RecoveryAction.MERCHANT_REVIEW,
    RecoveryAction.WAIT,
    RecoveryAction.STOP,
  ];

  const scoredActions: ScoredAction[] = candidateActions.map((action) => {
    let allowed = true;
    let rejectionReason: string | undefined = undefined;

    if (customerOptedOut && action !== RecoveryAction.STOP) {
      allowed = false;
      rejectionReason = 'Customer has opted out of recovery.';
    }

    if (
      (riskAssessment.riskScore >= HIGH_RISK_THRESHOLD ||
        riskAssessment.riskLevel === RiskLevel.HIGH ||
        riskAssessment.riskLevel === RiskLevel.CRITICAL) &&
      action !== RecoveryAction.MERCHANT_REVIEW &&
      action !== RecoveryAction.STOP
    ) {
      allowed = false;
      rejectionReason = 'Transaction assessed as high risk — requires merchant review.';
    }

    if (attemptCount >= MAX_RETRIES && action === RecoveryAction.RETRY) {
      allowed = false;
      rejectionReason = `Maximum automatic retries (${MAX_RETRIES}) reached.`;
    }

    let prob = getBaseRecoveryProbability(transaction.failureCategory || FailureCategory.UNKNOWN, action);
    prob = Math.max(0, prob - attemptCount * 0.15);

    if (allowed && action !== RecoveryAction.STOP && action !== RecoveryAction.MERCHANT_REVIEW && prob < MIN_RECOVERY_PROBABILITY) {
      allowed = false;
      rejectionReason = `Predicted recovery probability (${(prob * 100).toFixed(0)}%) is below ${(MIN_RECOVERY_PROBABILITY * 100).toFixed(0)}% threshold.`;
    }

    const riskCost = Math.round(riskAssessment.riskScore * transaction.amount * 0.05);
    const frictionCost = FRICTION_COSTS[action] || 0;
    const actionCost = ACTION_COSTS[action] || 0;

    const estimatedValue = Math.round(prob * transaction.amount);
    const expectedUtility = action === RecoveryAction.STOP ? 0 : estimatedValue - riskCost - frictionCost - actionCost;

    const item: ScoredAction = {
      action,
      expectedUtility,
      recoveryProbability: prob,
      estimatedValue,
      allowed,
      costs: {
        risk: riskCost,
        friction: frictionCost,
        action: actionCost,
      },
    };

    if (rejectionReason !== undefined) {
      item.rejectionReason = rejectionReason;
    }

    return item;
  });

  const allowedActions = scoredActions.filter((s) => s.allowed);
  allowedActions.sort((a, b) => b.expectedUtility - a.expectedUtility);

  const topAction = allowedActions[0] || {
    action: RecoveryAction.STOP,
    expectedUtility: 0,
    recoveryProbability: 0,
    estimatedValue: 0,
    allowed: true,
    costs: { risk: 0, friction: 0, action: 0 },
  };

  const decisionId = `dec_${transaction.id}_${Date.now()}`;
  const decision: Decision = {
    id: decisionId,
    transactionId: transaction.id,
    recommendedAction: topAction.action,
    status: DecisionStatus.APPROVED,
    expectedUtility: topAction.expectedUtility / 100,
    rationale: `Selected ${topAction.action} with Expected Utility ₹${(topAction.expectedUtility / 100).toFixed(2)} (Recovery Prob: ${(topAction.recoveryProbability * 100).toFixed(0)}%).`,
    createdAt: new Date().toISOString(),
  };

  return {
    decision,
    scoredActions,
    topAction,
  };
}

export { RecoveryAction, DecisionStatus } from '@recoverai/shared-types';
