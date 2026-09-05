import {
  Transaction,
  RecoveryCase,
  Decision,
  RecoveryAttempt,
  AuditEvent,
  NotificationRecord,
  AnalyticsSummary,
} from '@recoverai/shared-types';

export interface CustomerRecord {
  customerId: string;
  merchantId: string;
  optedOut: boolean;
}

export interface SystemModeInfo {
  gatewayMode: 'MOCK_DEMO' | 'RAZORPAY_SANDBOX';
  geminiAvailable: boolean;
  persistenceMode: 'memory' | 'mongodb';
  mongoConnected: boolean;
}

export interface IDataStore {
  clear(): Promise<void>;

  // Customer
  getCustomer(customerId: string): Promise<CustomerRecord | undefined>;
  saveCustomer(customer: CustomerRecord): Promise<CustomerRecord>;

  // Transaction
  getTransaction(id: string): Promise<Transaction | undefined>;
  getAllTransactions(): Promise<Transaction[]>;
  saveTransaction(txn: Transaction): Promise<Transaction>;

  // Recovery Case
  getCase(id: string): Promise<RecoveryCase | undefined>;
  getCaseByTransactionId(transactionId: string): Promise<RecoveryCase | undefined>;
  getAllCases(): Promise<RecoveryCase[]>;
  saveCase(recCase: RecoveryCase): Promise<RecoveryCase>;

  // Decision
  getDecision(id: string): Promise<Decision | undefined>;
  getAllDecisions(): Promise<Decision[]>;
  saveDecision(decision: Decision): Promise<Decision>;

  // Recovery Attempt
  getAttempt(id: string): Promise<RecoveryAttempt | undefined>;
  getAttemptsByCaseId(caseId: string): Promise<RecoveryAttempt[]>;
  saveAttempt(attempt: RecoveryAttempt): Promise<RecoveryAttempt>;

  // Audit Event
  addAuditEvent(event: AuditEvent): Promise<AuditEvent>;
  getAuditEventsByCaseId(caseId: string): Promise<AuditEvent[]>;
  getAllAuditEvents(): Promise<AuditEvent[]>;

  // Notification
  saveNotification(notif: NotificationRecord): Promise<NotificationRecord>;
  getNotificationsByCaseId(caseId: string): Promise<NotificationRecord[]>;

  // Idempotency
  checkAndSetIdempotency(key: string): Promise<boolean>;

  // Analytics Calculation
  getAnalyticsSummary(): Promise<AnalyticsSummary>;

  // System Mode
  getSystemMode(): Promise<SystemModeInfo>;
}
