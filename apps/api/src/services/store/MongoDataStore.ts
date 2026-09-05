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
import {
  CustomerModel,
  TransactionModel,
  RecoveryCaseModel,
  RecoveryActionModel,
  RecoveryOutcomeModel,
  AuditLogModel,
  NotificationModel,
  IdempotencyModel,
} from '../../models/mongoSchemas.js';
import { isDatabaseConnected } from '../../config/database.js';

export class MongoDataStore implements IDataStore {
  private static instance: MongoDataStore;

  private constructor() {}

  public static getInstance(): MongoDataStore {
    if (!MongoDataStore.instance) {
      MongoDataStore.instance = new MongoDataStore();
    }
    return MongoDataStore.instance;
  }

  public async clear(): Promise<void> {
    await Promise.all([
      CustomerModel.deleteMany({}),
      TransactionModel.deleteMany({}),
      RecoveryCaseModel.deleteMany({}),
      RecoveryActionModel.deleteMany({}),
      RecoveryOutcomeModel.deleteMany({}),
      AuditLogModel.deleteMany({}),
      NotificationModel.deleteMany({}),
      IdempotencyModel.deleteMany({}),
    ]);
  }

  // --- Customer ---
  public async getCustomer(customerId: string): Promise<CustomerRecord | undefined> {
    const doc = await (CustomerModel as any).findOne({ customerId }).lean();
    if (!doc) return undefined;
    return {
      customerId: doc.customerId,
      merchantId: doc.merchantId,
      optedOut: doc.optedOut,
    };
  }

  public async saveCustomer(customer: CustomerRecord): Promise<CustomerRecord> {
    await (CustomerModel as any).findOneAndUpdate(
      { customerId: customer.customerId },
      { $set: customer },
      { upsert: true, new: true },
    );
    return customer;
  }

  // --- Transaction ---
  public async getTransaction(id: string): Promise<Transaction | undefined> {
    const doc = await (TransactionModel as any).findOne({ id }).lean();
    if (!doc) return undefined;
    const { _id, __v, ...txn } = doc;
    return txn as Transaction;
  }

  public async getAllTransactions(): Promise<Transaction[]> {
    const docs = await (TransactionModel as any).find({}).sort({ createdAt: -1 }).lean();
    return docs.map((doc: any) => {
      const { _id, __v, ...txn } = doc;
      return txn as Transaction;
    });
  }

  public async saveTransaction(txn: Transaction): Promise<Transaction> {
    await (TransactionModel as any).findOneAndUpdate(
      { id: txn.id },
      { $set: txn },
      { upsert: true, new: true },
    );
    return txn;
  }

  // --- Recovery Case ---
  public async getCase(id: string): Promise<RecoveryCase | undefined> {
    const doc = await (RecoveryCaseModel as any).findOne({ id }).lean();
    if (!doc) return undefined;
    const { _id, __v, ...c } = doc;
    return c as RecoveryCase;
  }

  public async getCaseByTransactionId(transactionId: string): Promise<RecoveryCase | undefined> {
    const doc = await (RecoveryCaseModel as any).findOne({ transactionId }).lean();
    if (!doc) return undefined;
    const { _id, __v, ...c } = doc;
    return c as RecoveryCase;
  }

  public async getAllCases(): Promise<RecoveryCase[]> {
    const docs = await (RecoveryCaseModel as any).find({}).sort({ createdAt: -1 }).lean();
    return docs.map((doc: any) => {
      const { _id, __v, ...c } = doc;
      return c as RecoveryCase;
    });
  }

  public async saveCase(recCase: RecoveryCase): Promise<RecoveryCase> {
    await (RecoveryCaseModel as any).findOneAndUpdate(
      { id: recCase.id },
      { $set: recCase },
      { upsert: true, new: true },
    );
    return recCase;
  }

  // --- Decision ---
  public async getDecision(id: string): Promise<Decision | undefined> {
    const doc = await (RecoveryOutcomeModel as any).findOne({ id }).lean();
    if (!doc) return undefined;
    const { _id, __v, ...dec } = doc;
    return dec as Decision;
  }

  public async getAllDecisions(): Promise<Decision[]> {
    const docs = await (RecoveryOutcomeModel as any).find({}).sort({ createdAt: -1 }).lean();
    return docs.map((doc: any) => {
      const { _id, __v, ...dec } = doc;
      return dec as Decision;
    });
  }

  public async saveDecision(decision: Decision): Promise<Decision> {
    await (RecoveryOutcomeModel as any).findOneAndUpdate(
      { id: decision.id },
      { $set: decision },
      { upsert: true, new: true },
    );
    return decision;
  }

  // --- Recovery Attempt ---
  public async getAttempt(id: string): Promise<RecoveryAttempt | undefined> {
    const doc = await (RecoveryActionModel as any).findOne({ id }).lean();
    if (!doc) return undefined;
    const { _id, __v, ...att } = doc;
    return att as RecoveryAttempt;
  }

  public async getAttemptsByCaseId(caseId: string): Promise<RecoveryAttempt[]> {
    const docs = await (RecoveryActionModel as any).find({ caseId }).sort({ initiatedAt: -1 }).lean();
    return docs.map((doc: any) => {
      const { _id, __v, ...att } = doc;
      return att as RecoveryAttempt;
    });
  }

  public async saveAttempt(attempt: RecoveryAttempt): Promise<RecoveryAttempt> {
    await (RecoveryActionModel as any).findOneAndUpdate(
      { id: attempt.id },
      { $set: attempt },
      { upsert: true, new: true },
    );
    return attempt;
  }

  // --- Audit Event --- (APPEND-ONLY)
  public async addAuditEvent(event: AuditEvent): Promise<AuditEvent> {
    await (AuditLogModel as any).create(event);
    return event;
  }

  public async getAuditEventsByCaseId(caseId: string): Promise<AuditEvent[]> {
    const docs = await (AuditLogModel as any).find({ caseId }).sort({ timestamp: -1 }).lean();
    return docs.map((doc: any) => {
      const { _id, __v, ...evt } = doc;
      return evt as AuditEvent;
    });
  }

  public async getAllAuditEvents(): Promise<AuditEvent[]> {
    const docs = await (AuditLogModel as any).find({}).sort({ timestamp: -1 }).lean();
    return docs.map((doc: any) => {
      const { _id, __v, ...evt } = doc;
      return evt as AuditEvent;
    });
  }

  // --- Notification ---
  public async saveNotification(notif: NotificationRecord): Promise<NotificationRecord> {
    await (NotificationModel as any).findOneAndUpdate(
      { id: notif.id },
      { $set: notif },
      { upsert: true, new: true },
    );
    return notif;
  }

  public async getNotificationsByCaseId(caseId: string): Promise<NotificationRecord[]> {
    const docs = await (NotificationModel as any).find({ caseId }).sort({ createdAt: -1 }).lean();
    return docs.map((doc: any) => {
      const { _id, __v, ...n } = doc;
      return n as NotificationRecord;
    });
  }

  // --- Idempotency ---
  public async checkAndSetIdempotency(key: string): Promise<boolean> {
    try {
      await (IdempotencyModel as any).create({ key });
      return true;
    } catch (err: any) {
      if (err?.code === 11000) {
        return false;
      }
      throw err;
    }
  }

  // --- Analytics Calculation ---
  public async getAnalyticsSummary(): Promise<AnalyticsSummary> {
    const allCases = await this.getAllCases();
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

    const safetyViolations = await (AuditLogModel as any).countDocuments({ eventType: AuditEventType.POLICY_REJECTED });

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
      persistenceMode: 'mongodb',
      mongoConnected: isDatabaseConnected(),
    };
  }
}
