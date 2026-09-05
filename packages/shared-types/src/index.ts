/**
 * @recoverai/shared-types
 *
 * Shared TypeScript types, enums, and interfaces used across the RecoverAI
 * monorepo (frontend, backend, and packages).
 *
 * IMPORTANT: This package contains ONLY type definitions — no business logic,
 * no runtime code, no side effects.
 */

// =============================================================================
// Transaction Types
// =============================================================================

/** Lifecycle status of a payment transaction */
export enum TransactionStatus {
  PENDING = 'PENDING',
  AUTHORIZED = 'AUTHORIZED',
  CAPTURED = 'CAPTURED',
  FAILED = 'FAILED',
  REFUNDED = 'REFUNDED',
  PARTIALLY_REFUNDED = 'PARTIALLY_REFUNDED',
  EXPIRED = 'EXPIRED',
}

/** Root cause category of a payment failure */
export enum FailureCategory {
  INSUFFICIENT_FUNDS = 'INSUFFICIENT_FUNDS',
  CARD_DECLINED = 'CARD_DECLINED',
  AUTHENTICATION_FAILED = 'AUTHENTICATION_FAILED',
  NETWORK_ERROR = 'NETWORK_ERROR',
  BANK_TIMEOUT = 'BANK_TIMEOUT',
  FRAUD_SUSPECTED = 'FRAUD_SUSPECTED',
  CARD_EXPIRED = 'CARD_EXPIRED',
  INVALID_CVV = 'INVALID_CVV',
  LIMIT_EXCEEDED = 'LIMIT_EXCEEDED',
  UNKNOWN = 'UNKNOWN',
}

/** Core transaction data shape — will be backed by Mongoose model in Phase 2 */
export interface Transaction {
  id: string;
  merchantId: string;
  customerId: string;
  amount: number; // in paise (smallest INR unit)
  currency: string;
  status: TransactionStatus;
  failureCategory?: FailureCategory;
  failureCode?: string;
  deviceChanged?: boolean;
  locationChanged?: boolean;
  createdAt: string; // ISO 8601
  updatedAt: string; // ISO 8601
  metadata?: Record<string, unknown>;
}

// =============================================================================
// Risk Types
// =============================================================================

/** Categorical risk level assigned to a transaction */
export enum RiskLevel {
  LOW = 'LOW',
  MEDIUM = 'MEDIUM',
  HIGH = 'HIGH',
  CRITICAL = 'CRITICAL',
}

/** Risk assessment result — produced by the ML risk model (Phase 3+) */
export interface RiskAssessment {
  transactionId: string;
  riskLevel: RiskLevel;
  riskScore: number; // 0.0 – 1.0
  confidence: number; // 0.0 – 1.0
  factors: string[]; // human-readable risk factors
  assessedAt: string; // ISO 8601
}

// =============================================================================
// Recovery Types
// =============================================================================

/** Actions the RecoverAI decision engine may recommend */
export enum RecoveryAction {
  WAIT = 'WAIT',
  RETRY = 'RETRY',
  PAYMENT_LINK = 'PAYMENT_LINK',
  NOTIFICATION = 'NOTIFICATION',
  MERCHANT_REVIEW = 'MERCHANT_REVIEW',
  STOP = 'STOP',
}

/** Status of a recovery attempt */
export enum RecoveryStatus {
  PENDING = 'PENDING',
  IN_PROGRESS = 'IN_PROGRESS',
  SUCCEEDED = 'SUCCEEDED',
  FAILED = 'FAILED',
  CANCELLED = 'CANCELLED',
  STOPPED = 'STOPPED',
}

/** A single recovery attempt record */
export interface RecoveryAttempt {
  id: string;
  transactionId: string;
  action: RecoveryAction;
  status: RecoveryStatus;
  initiatedAt: string; // ISO 8601
  resolvedAt?: string; // ISO 8601
  amountRecovered?: number; // in paise
  metadata?: Record<string, unknown>;
}

// =============================================================================
// Decision Engine Types
// =============================================================================

/** Status of a decision made by the decision engine */
export enum DecisionStatus {
  PENDING = 'PENDING',
  APPROVED = 'APPROVED',
  REJECTED = 'REJECTED',
  BLOCKED_BY_POLICY = 'BLOCKED_BY_POLICY',
  EXECUTED = 'EXECUTED',
  EXPIRED = 'EXPIRED',
}

/** A decision record produced by the decision engine */
export interface Decision {
  id: string;
  transactionId: string;
  recommendedAction: RecoveryAction;
  status: DecisionStatus;
  expectedUtility?: number; // Phase 3+ — EU calculation result
  rationale: string;
  createdAt: string; // ISO 8601
  executedAt?: string; // ISO 8601
}

// =============================================================================
// Policy Engine Types
// =============================================================================

/** Result of a policy gate evaluation */
export enum PolicyResult {
  ALLOW = 'ALLOW',
  BLOCK = 'BLOCK',
  ESCALATE = 'ESCALATE',
  REQUIRE_REVIEW = 'REQUIRE_REVIEW',
}

/** A policy evaluation result record */
export interface PolicyEvaluation {
  transactionId: string;
  decisionId: string;
  result: PolicyResult;
  violatedRules: string[];
  evaluatedAt: string; // ISO 8601
}

// =============================================================================
// Phase 4 Recovery Case & Audit Types
// =============================================================================

/** Lifecycle states of a Recovery Case */
export enum RecoveryCaseState {
  DETECTED = 'DETECTED',
  ANALYZING = 'ANALYZING',
  DECISION_READY = 'DECISION_READY',
  ACTION_PENDING = 'ACTION_PENDING',
  ACTION_EXECUTED = 'ACTION_EXECUTED',
  RECOVERED = 'RECOVERED',
  FAILED = 'FAILED',
  STOPPED = 'STOPPED',
  MERCHANT_REVIEW = 'MERCHANT_REVIEW',
}

/** Full Recovery Case entity */
export interface RecoveryCase {
  id: string;
  transactionId: string;
  merchantId: string;
  customerId: string;
  amount: number; // in paise
  currency: string;
  state: RecoveryCaseState;
  failureCategory: FailureCategory;
  failureCode?: string | undefined;
  riskScore: number;
  riskLevel: RiskLevel;
  attemptCount: number;
  currentDecisionId?: string | undefined;
  selectedAction?: RecoveryAction | undefined;
  explanation?: string | undefined;
  customerOptedOut: boolean;
  createdAt: string; // ISO 8601
  updatedAt: string; // ISO 8601
  resolvedAt?: string | undefined;
}

/** Audit event types */
export enum AuditEventType {
  CASE_CREATED = 'CASE_CREATED',
  RISK_ASSESSED = 'RISK_ASSESSED',
  ACTION_RANKED = 'ACTION_RANKED',
  POLICY_REJECTED = 'POLICY_REJECTED',
  ACTION_SELECTED = 'ACTION_SELECTED',
  ACTION_EXECUTED = 'ACTION_EXECUTED',
  PAYMENT_RECOVERED = 'PAYMENT_RECOVERED',
  PAYMENT_FAILED = 'PAYMENT_FAILED',
  CUSTOMER_OPTED_OUT = 'CUSTOMER_OPTED_OUT',
  MERCHANT_REVIEW_REQUIRED = 'MERCHANT_REVIEW_REQUIRED',
  RECOVERY_STOPPED = 'RECOVERY_STOPPED',
  NOTIFICATION_CREATED = 'NOTIFICATION_CREATED',
}

/** Immutable Audit Trail record */
export interface AuditEvent {
  id: string;
  caseId: string;
  transactionId: string;
  eventType: AuditEventType;
  actor: 'SYSTEM' | 'MERCHANT' | 'POLICY_GATE' | 'ML_ENGINE' | 'AI_AGENT';
  timestamp: string; // ISO 8601
  reason?: string;
  details?: Record<string, unknown>;
}

/** Notification channel types */
export enum NotificationChannel {
  EMAIL = 'EMAIL',
  SMS = 'SMS',
  WHATSAPP = 'WHATSAPP',
}

/** Notification record */
export interface NotificationRecord {
  id: string;
  caseId: string;
  customerId: string;
  channel: NotificationChannel;
  template: string;
  status: 'PENDING' | 'SENT' | 'FAILED' | 'BLOCKED';
  messageBody?: string;
  failureReason?: string;
  createdAt: string; // ISO 8601
  sentAt?: string; // ISO 8601
}

/** Dashboard analytics summary */
export interface AnalyticsSummary {
  totalRevenueAtRisk: number; // in paise
  totalRecoveredRevenue: number; // in paise
  recoveryRate: number; // 0.0 - 1.0
  recoveryEfficiency: number; // 0.0 - 1.0
  netRecoveryValue: number; // in paise
  totalCases: number;
  activeCases: number;
  recoveredCases: number;
  stoppedCases: number;
  merchantReviewCases: number;
  safetyViolations: number;
  avgRecoveryTimeMinutes: number;
}

// =============================================================================
// API Response Envelope
// =============================================================================

/** Standardized API success envelope */
export interface ApiSuccessResponse<T = unknown> {
  success: true;
  data: T;
  meta?: {
    page?: number;
    limit?: number;
    total?: number;
  };
}

/** Standardized API error envelope */
export interface ApiErrorResponse {
  success: false;
  error: {
    message: string;
    code?: string;
  };
}

export type ApiResponse<T = unknown> = ApiSuccessResponse<T> | ApiErrorResponse;
