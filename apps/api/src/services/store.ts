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

export class DataStore {
  private static instance: DataStore;

  private customers: Map<string, { customerId: string; merchantId: string; optedOut: boolean }> = new Map();
  private transactions: Map<string, Transaction> = new Map();
  private cases: Map<string, RecoveryCase> = new Map();
  private decisions: Map<string, Decision> = new Map();
  private attempts: Map<string, RecoveryAttempt> = new Map();
  private auditEvents: AuditEvent[] = [];
  private notifications: Map<string, NotificationRecord> = new Map();
  private idempotencyKeys: Set<string> = new Set();

  private constructor() {}

  public static getInstance(): DataStore {
    if (!DataStore.instance) {
      DataStore.instance = new DataStore();
    }
    return DataStore.instance;
  }

  public clear(): void {
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
  public getCustomer(customerId: string) {
    return this.customers.get(customerId);
  }

  public saveCustomer(customer: { customerId: string; merchantId: string; optedOut: boolean }) {
    this.customers.set(customer.customerId, customer);
    return customer;
  }

  // --- Transaction ---
  public getTransaction(id: string): Transaction | undefined {
    return this.transactions.get(id);
  }

  public getAllTransactions(): Transaction[] {
    return Array.from(this.transactions.values()).sort(
      (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
    );
  }

  public saveTransaction(txn: Transaction): Transaction {
    this.transactions.set(txn.id, txn);
    return txn;
  }

  // --- Recovery Case ---
  public getCase(id: string): RecoveryCase | undefined {
    return this.cases.get(id);
  }

  public getCaseByTransactionId(transactionId: string): RecoveryCase | undefined {
    return Array.from(this.cases.values()).find((c) => c.transactionId === transactionId);
  }

  public getAllCases(): RecoveryCase[] {
    return Array.from(this.cases.values()).sort(
      (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
    );
  }

  public saveCase(recCase: RecoveryCase): RecoveryCase {
    this.cases.set(recCase.id, recCase);
    return recCase;
  }

  // --- Decision ---
  public getDecision(id: string): Decision | undefined {
    return this.decisions.get(id);
  }

  public getAllDecisions(): Decision[] {
    return Array.from(this.decisions.values()).sort(
      (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
    );
  }

  public saveDecision(decision: Decision): Decision {
    this.decisions.set(decision.id, decision);
    return decision;
  }

  // --- Recovery Attempt ---
  public getAttempt(id: string): RecoveryAttempt | undefined {
    return this.attempts.get(id);
  }

  public getAttemptsByCaseId(caseId: string): RecoveryAttempt[] {
    return Array.from(this.attempts.values()).filter((a) => (a as any).caseId === caseId);
  }

  public saveAttempt(attempt: RecoveryAttempt): RecoveryAttempt {
    this.attempts.set(attempt.id, attempt);
    return attempt;
  }

  // --- Audit Event ---
  public addAuditEvent(event: AuditEvent): AuditEvent {
    this.auditEvents.push(event);
    return event;
  }

  public getAuditEventsByCaseId(caseId: string): AuditEvent[] {
    return this.auditEvents
      .filter((e) => e.caseId === caseId)
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
  }

  public getAllAuditEvents(): AuditEvent[] {
    return [...this.auditEvents].sort(
      (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
    );
  }

  // --- Notification ---
  public saveNotification(notif: NotificationRecord): NotificationRecord {
    this.notifications.set(notif.id, notif);
    return notif;
  }

  public getNotificationsByCaseId(caseId: string): NotificationRecord[] {
    return Array.from(this.notifications.values()).filter((n) => n.caseId === caseId);
  }

  // --- Idempotency ---
  public checkAndSetIdempotency(key: string): boolean {
    if (this.idempotencyKeys.has(key)) {
      return false;
    }
    this.idempotencyKeys.add(key);
    return true;
  }

  // --- Analytics Calculation ---
  public getAnalyticsSummary(): AnalyticsSummary {
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

  public getSystemMode(): { gatewayMode: 'MOCK_DEMO' | 'RAZORPAY_SANDBOX'; geminiAvailable: boolean } {
    const hasRazorpay = Boolean(process.env['RAZORPAY_KEY_ID'] && process.env['RAZORPAY_KEY_SECRET']);
    const hasGemini = Boolean(process.env['GEMINI_API_KEY']);
    return {
      gatewayMode: hasRazorpay ? 'RAZORPAY_SANDBOX' : 'MOCK_DEMO',
      geminiAvailable: hasGemini,
    };
  }
}

export const dataStore = DataStore.getInstance();
