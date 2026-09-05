import mongoose, { Schema } from 'mongoose';
import {
  TransactionStatus,
  FailureCategory,
  RiskLevel,
  RecoveryAction,
  RecoveryStatus,
  DecisionStatus,
  RecoveryCaseState,
  AuditEventType,
  NotificationChannel,
} from '@recoverai/shared-types';

// =============================================================================
// 1. Customer Schema & Model
// =============================================================================
export interface ICustomer {
  customerId: string;
  merchantId: string;
  optedOut: boolean;
}

const CustomerSchema = new Schema<ICustomer>(
  {
    customerId: { type: String, required: true, unique: true, index: true },
    merchantId: { type: String, required: true, index: true },
    optedOut: { type: Boolean, required: true, default: false },
  },
  { timestamps: true, collection: 'customers' },
);

export const CustomerModel = mongoose.models.Customer || mongoose.model<ICustomer>('Customer', CustomerSchema);

// =============================================================================
// 2. Transaction Schema & Model
// =============================================================================
export interface ITransaction {
  id: string;
  merchantId: string;
  customerId: string;
  amount: number;
  currency: string;
  status: TransactionStatus;
  failureCategory?: FailureCategory;
  failureCode?: string;
  deviceChanged?: boolean;
  locationChanged?: boolean;
  createdAt: string;
  updatedAt: string;
  metadata?: Record<string, unknown>;
}

const TransactionSchema = new Schema<ITransaction>(
  {
    id: { type: String, required: true, unique: true, index: true },
    merchantId: { type: String, required: true, index: true },
    customerId: { type: String, required: true, index: true },
    amount: { type: Number, required: true },
    currency: { type: String, required: true, default: 'INR' },
    status: { type: String, required: true, enum: Object.values(TransactionStatus), index: true },
    failureCategory: { type: String, enum: Object.values(FailureCategory) },
    failureCode: { type: String },
    deviceChanged: { type: Boolean, default: false },
    locationChanged: { type: Boolean, default: false },
    createdAt: { type: String, required: true, index: true },
    updatedAt: { type: String, required: true },
    metadata: { type: Schema.Types.Mixed },
  },
  { collection: 'transactions' },
);

TransactionSchema.index({ merchantId: 1, createdAt: -1 });

export const TransactionModel = mongoose.models.Transaction || mongoose.model<ITransaction>('Transaction', TransactionSchema);

// =============================================================================
// 3. Recovery Case Schema & Model
// =============================================================================
export interface IRecoveryCase {
  id: string;
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
  createdAt: string;
  updatedAt: string;
  resolvedAt?: string;
}

const RecoveryCaseSchema = new Schema<IRecoveryCase>(
  {
    id: { type: String, required: true, unique: true, index: true },
    transactionId: { type: String, required: true, unique: true, index: true },
    merchantId: { type: String, required: true, index: true },
    customerId: { type: String, required: true, index: true },
    amount: { type: Number, required: true },
    currency: { type: String, required: true, default: 'INR' },
    state: { type: String, required: true, enum: Object.values(RecoveryCaseState), index: true },
    failureCategory: { type: String, required: true, enum: Object.values(FailureCategory) },
    failureCode: { type: String },
    riskScore: { type: Number, required: true },
    riskLevel: { type: String, required: true, enum: Object.values(RiskLevel) },
    attemptCount: { type: Number, required: true, default: 0 },
    currentDecisionId: { type: String },
    selectedAction: { type: String, enum: Object.values(RecoveryAction) },
    explanation: { type: String },
    customerOptedOut: { type: Boolean, required: true, default: false },
    createdAt: { type: String, required: true, index: true },
    updatedAt: { type: String, required: true },
    resolvedAt: { type: String },
  },
  { collection: 'recovery_cases' },
);

RecoveryCaseSchema.index({ merchantId: 1, state: 1 });
RecoveryCaseSchema.index({ createdAt: -1 });

export const RecoveryCaseModel = mongoose.models.RecoveryCase || mongoose.model<IRecoveryCase>('RecoveryCase', RecoveryCaseSchema);

// =============================================================================
// 4. Recovery Action Schema & Model (RecoveryAttempt)
// =============================================================================
export interface IRecoveryAction {
  id: string;
  caseId: string;
  transactionId: string;
  action: RecoveryAction;
  status: RecoveryStatus;
  initiatedAt: string;
  resolvedAt?: string;
  amountRecovered?: number;
  metadata?: Record<string, unknown>;
}

const RecoveryActionSchema = new Schema<IRecoveryAction>(
  {
    id: { type: String, required: true, unique: true, index: true },
    caseId: { type: String, required: true, index: true },
    transactionId: { type: String, required: true, index: true },
    action: { type: String, required: true, enum: Object.values(RecoveryAction) },
    status: { type: String, required: true, enum: Object.values(RecoveryStatus) },
    initiatedAt: { type: String, required: true, index: true },
    resolvedAt: { type: String },
    amountRecovered: { type: Number },
    metadata: { type: Schema.Types.Mixed },
  },
  { collection: 'recovery_actions' },
);

export const RecoveryActionModel = mongoose.models.RecoveryAction || mongoose.model<IRecoveryAction>('RecoveryAction', RecoveryActionSchema);

// =============================================================================
// 5. Recovery Outcome Schema & Model (Decision)
// =============================================================================
export interface IRecoveryOutcome {
  id: string;
  transactionId: string;
  recommendedAction: RecoveryAction;
  status: DecisionStatus;
  expectedUtility?: number;
  rationale: string;
  createdAt: string;
  executedAt?: string;
}

const RecoveryOutcomeSchema = new Schema<IRecoveryOutcome>(
  {
    id: { type: String, required: true, unique: true, index: true },
    transactionId: { type: String, required: true, index: true },
    recommendedAction: { type: String, required: true, enum: Object.values(RecoveryAction) },
    status: { type: String, required: true, enum: Object.values(DecisionStatus) },
    expectedUtility: { type: Number },
    rationale: { type: String, required: true },
    createdAt: { type: String, required: true, index: true },
    executedAt: { type: String },
  },
  { collection: 'recovery_outcomes' },
);

export const RecoveryOutcomeModel = mongoose.models.RecoveryOutcome || mongoose.model<IRecoveryOutcome>('RecoveryOutcome', RecoveryOutcomeSchema);

// =============================================================================
// 6. Audit Log Schema & Model
// =============================================================================
export interface IAuditLog {
  id: string;
  caseId: string;
  transactionId: string;
  eventType: AuditEventType;
  actor: 'SYSTEM' | 'MERCHANT' | 'POLICY_GATE' | 'ML_ENGINE' | 'AI_AGENT';
  timestamp: string;
  reason?: string;
  details?: Record<string, unknown>;
}

const AuditLogSchema = new Schema<IAuditLog>(
  {
    id: { type: String, required: true, unique: true, index: true },
    caseId: { type: String, required: true, index: true },
    transactionId: { type: String, required: true, index: true },
    eventType: { type: String, required: true, enum: Object.values(AuditEventType), index: true },
    actor: { type: String, required: true },
    timestamp: { type: String, required: true, index: true },
    reason: { type: String },
    details: { type: Schema.Types.Mixed },
  },
  { collection: 'audit_logs' },
);

AuditLogSchema.index({ caseId: 1, timestamp: -1 });

export const AuditLogModel = mongoose.models.AuditLog || mongoose.model<IAuditLog>('AuditLog', AuditLogSchema);

// =============================================================================
// 7. Notification Record Schema & Model
// =============================================================================
export interface INotification {
  id: string;
  caseId: string;
  customerId: string;
  channel: NotificationChannel;
  template: string;
  status: 'PENDING' | 'SENT' | 'FAILED' | 'BLOCKED';
  messageBody?: string;
  failureReason?: string;
  createdAt: string;
  sentAt?: string;
}

const NotificationSchema = new Schema<INotification>(
  {
    id: { type: String, required: true, unique: true, index: true },
    caseId: { type: String, required: true, index: true },
    customerId: { type: String, required: true, index: true },
    channel: { type: String, required: true, enum: Object.values(NotificationChannel) },
    template: { type: String, required: true },
    status: { type: String, required: true },
    messageBody: { type: String },
    failureReason: { type: String },
    createdAt: { type: String, required: true, index: true },
    sentAt: { type: String },
  },
  { collection: 'notifications' },
);

export const NotificationModel = mongoose.models.Notification || mongoose.model<INotification>('Notification', NotificationSchema);

// =============================================================================
// 8. Experiment Run Schema & Model
// =============================================================================
export interface IExperimentRun {
  runId: string;
  casesCount: number;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

const ExperimentRunSchema = new Schema<IExperimentRun>(
  {
    runId: { type: String, required: true, unique: true, index: true },
    casesCount: { type: Number, required: true },
    timestamp: { type: String, required: true, index: true },
    metadata: { type: Schema.Types.Mixed },
  },
  { collection: 'experiment_runs' },
);

export const ExperimentRunModel = mongoose.models.ExperimentRun || mongoose.model<IExperimentRun>('ExperimentRun', ExperimentRunSchema);

// =============================================================================
// 9. Idempotency Key Schema & Model
// =============================================================================
export interface IIdempotency {
  key: string;
  createdAt: Date;
}

const IdempotencySchema = new Schema<IIdempotency>(
  {
    key: { type: String, required: true, unique: true, index: true },
    createdAt: { type: Date, default: Date.now, expires: 86400 }, // TTL 24 hours
  },
  { collection: 'idempotency_keys' },
);

export const IdempotencyModel = mongoose.models.Idempotency || mongoose.model<IIdempotency>('Idempotency', IdempotencySchema);
