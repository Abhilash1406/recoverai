import {
  Transaction,
  RecoveryCase,
  RecoveryCaseState,
  Decision,
  RecoveryAttempt,
  AuditEvent,
  AuditEventType,
  NotificationRecord,
  AnalyticsSummary,
} from '@recoverai/shared-types';
import { IDataStore, CustomerRecord, SystemModeInfo } from './IDataStore.js';
import { isDatabaseConnected } from '../../config/database.js';

export class InMemoryDataStore implements IDataStore {
  private static instance: InMemoryDataStore;

  private customers: Map<string, CustomerRecord> = new Map();
  private transactions: Map<string, Transaction> = new Map();
  private cases: Map<string, RecoveryCase> = new Map();
  private decisions: Map<string, Decision> = new Map();
  private attempts: Map<string, RecoveryAttempt> = new Map();
  private auditEvents: AuditEvent[] = [];
  private notifications: Map<string, NotificationRecord> = new Map();
  private idempotencyKeys: Set<string> = new Set();

  private constructor() {}

  public static getInstance(): InMemoryDataStore {
    if (!InMemoryDataStore.instance) {
      InMemoryDataStore.instance = new InMemoryDataStore();
    }
    return InMemoryDataStore.instance;
  }

  public async clear(): Promise<void> {
    this.customers.clear();
    this.transactions.clear();
    this.cases.clear();
    this.decisions.clear();
    this.attempts.clear();
    this.auditEvents = [];
    this.notifications.clear();
    this.idempotencyKeys.clear();
  }

  // --- Customer ---
  public async getCustomer(customerId: string): Promise<CustomerRecord | undefined> {
    return this.customers.get(customerId);
  }

  public async saveCustomer(customer: CustomerRecord): Promise<CustomerRecord> {
    this.customers.set(customer.customerId, customer);
    return customer;
  }

  // --- Transaction ---
  public async getTransaction(id: string): Promise<Transaction | undefined> {
    return this.transactions.get(id);
  }

  public async getAllTransactions(): Promise<Transaction[]> {
    return Array.from(this.transactions.values()).sort(
      (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
    );
  }

  public async saveTransaction(txn: Transaction): Promise<Transaction> {
    this.transactions.set(txn.id, txn);
    return txn;
  }

  // --- Recovery Case ---
  public async getCase(id: string): Promise<RecoveryCase | undefined> {
    return this.cases.get(id);
  }

  public async getCaseByTransactionId(transactionId: string): Promise<RecoveryCase | undefined> {
    return Array.from(this.cases.values()).find((c) => c.transactionId === transactionId);
  }

  public async getAllCases(): Promise<RecoveryCase[]> {
    return Array.from(this.cases.values()).sort(
      (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
    );
  }

  public async saveCase(recCase: RecoveryCase): Promise<RecoveryCase> {
    this.cases.set(recCase.id, recCase);
    return recCase;
  }

  // --- Decision ---
  public async getDecision(id: string): Promise<Decision | undefined> {
    return this.decisions.get(id);
  }

  public async getAllDecisions(): Promise<Decision[]> {
    return Array.from(this.decisions.values()).sort(
      (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
    );
  }

  public async saveDecision(decision: Decision): Promise<Decision> {
    this.decisions.set(decision.id, decision);
    return decision;
  }

  // --- Recovery Attempt ---
  public async getAttempt(id: string): Promise<RecoveryAttempt | undefined> {
    return this.attempts.get(id);
  }

  public async getAttemptsByCaseId(caseId: string): Promise<RecoveryAttempt[]> {
    return Array.from(this.attempts.values()).filter((a) => (a as any).caseId === caseId);
  }

  public async saveAttempt(attempt: RecoveryAttempt): Promise<RecoveryAttempt> {
    this.attempts.set(attempt.id, attempt);
    return attempt;
  }

  // --- Audit Event ---
  public async addAuditEvent(event: AuditEvent): Promise<AuditEvent> {
    this.auditEvents.push(event);
    return event;
  }

  public async getAuditEventsByCaseId(caseId: string): Promise<AuditEvent[]> {
    return this.auditEvents
      .filter((e) => e.caseId === caseId)
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
  }

  public async getAllAuditEvents(): Promise<AuditEvent[]> {
    return [...this.auditEvents].sort(
      (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
    );
  }

  // --- Notification ---
  public async saveNotification(notif: NotificationRecord): Promise<NotificationRecord> {
    this.notifications.set(notif.id, notif);
    return notif;
  }

  public async getNotificationsByCaseId(caseId: string): Promise<NotificationRecord[]> {
    return Array.from(this.notifications.values()).filter((n) => n.caseId === caseId);
  }

  // --- Idempotency ---
  public async checkAndSetIdempotency(key: string): Promise<boolean> {
    if (this.idempotencyKeys.has(key)) {
      return false;
    }
    this.idempotencyKeys.add(key);
    return true;
  }

  // --- Analytics Calculation ---
  public async getAnalyticsSummary(): Promise<AnalyticsSummary> {
    const allCases = Array.from(this.cases.values());
    const totalCases = allCases.length;

    let totalRevenueAtRisk = 0;
    let totalRecoveredRevenue = 0;
    let activeCases = 0;
    let recoveredCases = 0;
    let stoppedCases = 0;
    let merchantReviewCases = 0;
    let totalRecoveryDurationMs = 0;
    let resolvedCount = 0;

    for (const c of allCases) {
      totalRevenueAtRisk += c.amount;

      if (c.state === RecoveryCaseState.RECOVERED) {
        recoveredCases++;
        totalRecoveredRevenue += c.amount;
        if (c.resolvedAt) {
          totalRecoveryDurationMs += new Date(c.resolvedAt).getTime() - new Date(c.createdAt).getTime();
          resolvedCount++;
        }
      } else if (c.state === RecoveryCaseState.STOPPED || c.state === RecoveryCaseState.FAILED) {
        stoppedCases++;
      } else if (c.state === RecoveryCaseState.MERCHANT_REVIEW) {
        merchantReviewCases++;
      } else {
        activeCases++;
      }
    }

    const safetyViolations = this.auditEvents.filter((e) => e.eventType === AuditEventType.POLICY_REJECTED).length;

    const recoveryRate = totalCases > 0 ? recoveredCases / totalCases : 0;
    const recoveryEfficiency = totalRevenueAtRisk > 0 ? totalRecoveredRevenue / totalRevenueAtRisk : 0;
    const netRecoveryValue = Math.max(0, totalRecoveredRevenue - Math.round(totalRecoveredRevenue * 0.01));
    const avgRecoveryTimeMinutes = resolvedCount > 0 ? Math.round(totalRecoveryDurationMs / (resolvedCount * 60000)) : 0;

    return {
      totalRevenueAtRisk,
      totalRecoveredRevenue,
      recoveryRate,
      recoveryEfficiency,
      netRecoveryValue,
      totalCases,
      activeCases,
      recoveredCases,
      stoppedCases,
      merchantReviewCases,
      safetyViolations,
      avgRecoveryTimeMinutes,
    };
  }

  public async getSystemMode(): Promise<SystemModeInfo> {
    const hasRazorpay = Boolean(process.env['RAZORPAY_KEY_ID'] && process.env['RAZORPAY_KEY_SECRET']);
    const hasGemini = Boolean(process.env['GEMINI_API_KEY']);
    return {
      gatewayMode: hasRazorpay ? 'RAZORPAY_SANDBOX' : 'MOCK_DEMO',
      geminiAvailable: hasGemini,
      persistenceMode: 'memory',
      mongoConnected: isDatabaseConnected(),
    };
  }
}
