import mongoose, { Schema, Document } from 'mongoose';
import {
  TransactionStatus,
  FailureCategory,
  RiskLevel,
  RecoveryAction,
  RecoveryStatus,
  DecisionStatus,
  PolicyResult,
  RecoveryCaseState,
  AuditEventType,
  NotificationChannel,
} from '@recoverai/shared-types';

// =============================================================================
// 1. Customer Schema
// =============================================================================
export interface ICustomerDoc extends Document {
  customerId: string;
  merchantId: string;
  optedOut: boolean;
  historicalSuccessRate: number;
  previousTransactionsCount: number;
  accountAgeDays: number;
  createdAt: Date;
  updatedAt: Date;
}

const CustomerSchema = new Schema<ICustomerDoc>(
  {
    customerId: { type: String, required: true, unique: true, index: true },
    merchantId: { type: String, required: true, index: true },
    optedOut: { type: Boolean, default: false, index: true },
    historicalSuccessRate: { type: Number, default: 0.85 },
    previousTransactionsCount: { type: Number, default: 10 },
    accountAgeDays: { type: Number, default: 180 },
  },
  { timestamps: true },
);

// =============================================================================
// 2. Transaction Schema
// =============================================================================
export interface ITransactionDoc extends Document {
  transactionId: string;
  merchantId: string;
  customerId: string;
  amount: number; // paise
  currency: string;
  status: TransactionStatus;
  failureCategory: FailureCategory;
  failureCode?: string;
  paymentMethod: string;
  transactionHour: number;
  deviceChanged: boolean;
  locationChanged: boolean;
  amountDeviation: number;
  transactionVelocity: number;
  metadata?: Record<string, unknown>;
  createdAt: Date;
  updatedAt: Date;
}

const TransactionSchema = new Schema<ITransactionDoc>(
  {
    transactionId: { type: String, required: true, unique: true, index: true },
    merchantId: { type: String, required: true, index: true },
    customerId: { type: String, required: true, index: true },
    amount: { type: Number, required: true },
    currency: { type: String, default: 'INR' },
    status: { type: String, enum: Object.values(TransactionStatus), required: true, index: true },
    failureCategory: { type: String, enum: Object.values(FailureCategory), required: true, index: true },
    failureCode: { type: String },
    paymentMethod: { type: String, default: 'upi' },
    transactionHour: { type: Number, default: 14 },
    deviceChanged: { type: Boolean, default: false },
    locationChanged: { type: Boolean, default: false },
    amountDeviation: { type: Number, default: 0.1 },
    transactionVelocity: { type: Number, default: 1.0 },
    metadata: { type: Schema.Types.Mixed },
  },
  { timestamps: true },
);

// =============================================================================
// 3. RecoveryCase Schema
// =============================================================================
export interface IRecoveryCaseDoc extends Document {
  caseId: string;
  transactionId: string;
  merchantId: string;
  customerId: string;
  amount: number;
  currency: string;
  state: RecoveryCaseState;
  failureCategory: FailureCategory;
  failureCode?: string;
  riskScore: number;
  riskLevel: RiskLevel;
  attemptCount: number;
  currentDecisionId?: string;
  selectedAction?: RecoveryAction;
  explanation?: string;
  customerOptedOut: boolean;
  resolvedAt?: Date;
  createdAt: Date;
  updatedAt: Date;
}

const RecoveryCaseSchema = new Schema<IRecoveryCaseDoc>(
  {
    caseId: { type: String, required: true, unique: true, index: true },
    transactionId: { type: String, required: true, index: true },
    merchantId: { type: String, required: true, index: true },
    customerId: { type: String, required: true, index: true },
    amount: { type: Number, required: true },
    currency: { type: String, default: 'INR' },
    state: { type: String, enum: Object.values(RecoveryCaseState), required: true, index: true },
    failureCategory: { type: String, enum: Object.values(FailureCategory), required: true },
    failureCode: { type: String },
    riskScore: { type: Number, default: 0.1 },
    riskLevel: { type: String, enum: Object.values(RiskLevel), default: RiskLevel.LOW, index: true },
    attemptCount: { type: Number, default: 0 },
    currentDecisionId: { type: String },
    selectedAction: { type: String, enum: Object.values(RecoveryAction) },
    explanation: { type: String },
    customerOptedOut: { type: Boolean, default: false },
    resolvedAt: { type: Date },
  },
  { timestamps: true },
);

// =============================================================================
// 4. Decision Schema
// =============================================================================
export interface IDecisionDoc extends Document {
  decisionId: string;
  caseId: string;
  transactionId: string;
  recommendedAction: RecoveryAction;
  status: DecisionStatus;
  expectedUtility: number;
  policyResult: PolicyResult;
  violatedRules: string[];
  rationale: string;
  candidateScores: Array<{
    action: RecoveryAction;
    expectedUtility: number;
    recoveryProbability: number;
    allowed: boolean;
    rejectionReason?: string;
  }>;
  createdAt: Date;
}

const DecisionSchema = new Schema<IDecisionDoc>(
  {
    decisionId: { type: String, required: true, unique: true, index: true },
    caseId: { type: String, required: true, index: true },
    transactionId: { type: String, required: true, index: true },
    recommendedAction: { type: String, enum: Object.values(RecoveryAction), required: true },
    status: { type: String, enum: Object.values(DecisionStatus), required: true },
    expectedUtility: { type: Number, default: 0 },
    policyResult: { type: String, enum: Object.values(PolicyResult), required: true },
    violatedRules: [{ type: String }],
    rationale: { type: String, required: true },
    candidateScores: [
      {
        action: { type: String, enum: Object.values(RecoveryAction) },
        expectedUtility: { type: Number },
        recoveryProbability: { type: Number },
        allowed: { type: Boolean },
        rejectionReason: { type: String },
      },
    ],
  },
  { timestamps: true },
);

// =============================================================================
// 5. RecoveryAttempt Schema
// =============================================================================
export interface IRecoveryAttemptDoc extends Document {
  attemptId: string;
  caseId: string;
  transactionId: string;
  action: RecoveryAction;
  status: RecoveryStatus;
  gatewayResponseId?: string;
  amountRecovered?: number;
  failureReason?: string;
  initiatedAt: Date;
  resolvedAt?: Date;
}

const RecoveryAttemptSchema = new Schema<IRecoveryAttemptDoc>(
  {
    attemptId: { type: String, required: true, unique: true, index: true },
    caseId: { type: String, required: true, index: true },
    transactionId: { type: String, required: true, index: true },
    action: { type: String, enum: Object.values(RecoveryAction), required: true },
    status: { type: String, enum: Object.values(RecoveryStatus), required: true },
    gatewayResponseId: { type: String },
    amountRecovered: { type: Number, default: 0 },
    failureReason: { type: String },
    initiatedAt: { type: Date, default: Date.now },
    resolvedAt: { type: Date },
  },
  { timestamps: true },
);

// =============================================================================
// 6. AuditEvent Schema
// =============================================================================
export interface IAuditEventDoc extends Document {
  eventId: string;
  caseId: string;
  transactionId: string;
  eventType: AuditEventType;
  actor: string;
  reason?: string;
  details?: Record<string, unknown>;
  timestamp: Date;
}

const AuditEventSchema = new Schema<IAuditEventDoc>(
  {
    eventId: { type: String, required: true, unique: true, index: true },
    caseId: { type: String, required: true, index: true },
    transactionId: { type: String, required: true, index: true },
    eventType: { type: String, enum: Object.values(AuditEventType), required: true, index: true },
    actor: { type: String, required: true },
    reason: { type: String },
    details: { type: Schema.Types.Mixed },
    timestamp: { type: Date, default: Date.now, index: true },
  },
  { timestamps: true },
);

// =============================================================================
// 7. Notification Schema
// =============================================================================
export interface INotificationDoc extends Document {
  notificationId: string;
  caseId: string;
  customerId: string;
  channel: NotificationChannel;
  template: string;
  status: string;
  messageBody?: string;
  failureReason?: string;
  sentAt?: Date;
  createdAt: Date;
}

const NotificationSchema = new Schema<INotificationDoc>(
  {
    notificationId: { type: String, required: true, unique: true, index: true },
    caseId: { type: String, required: true, index: true },
    customerId: { type: String, required: true, index: true },
    channel: { type: String, enum: Object.values(NotificationChannel), required: true },
    template: { type: String, required: true },
    status: { type: String, required: true },
    messageBody: { type: String },
    failureReason: { type: String },
    sentAt: { type: Date },
  },
  { timestamps: true },
);

// Exports
export const CustomerModel = mongoose.model<ICustomerDoc>('Customer', CustomerSchema);
export const TransactionModel = mongoose.model<ITransactionDoc>('Transaction', TransactionSchema);
export const RecoveryCaseModel = mongoose.model<IRecoveryCaseDoc>('RecoveryCase', RecoveryCaseSchema);
export const DecisionModel = mongoose.model<IDecisionDoc>('Decision', DecisionSchema);
export const RecoveryAttemptModel = mongoose.model<IRecoveryAttemptDoc>('RecoveryAttempt', RecoveryAttemptSchema);
export const AuditEventModel = mongoose.model<IAuditEventDoc>('AuditEvent', AuditEventSchema);
export const NotificationModel = mongoose.model<INotificationDoc>('Notification', NotificationSchema);
