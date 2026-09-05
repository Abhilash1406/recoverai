import { describe, it, expect, beforeEach, afterAll } from 'vitest';
import { InMemoryDataStore } from '../src/services/store/InMemoryDataStore.js';
import { MongoDataStore } from '../src/services/store/MongoDataStore.js';
import { connectDatabase, disconnectDatabase } from '../src/config/database.js';
import {
  Transaction,
  TransactionStatus,
  FailureCategory,
  RecoveryCase,
  RecoveryCaseState,
  RiskLevel,
} from '@recoverai/shared-types';

describe('Phase 5A Persistence Layer Abstraction Tests', () => {
  describe('InMemoryDataStore Compatibility', () => {
    const store = InMemoryDataStore.getInstance();

    beforeEach(async () => {
      await store.clear();
    });

    it('saves and retrieves transactions asynchronously', async () => {
      const txn: Transaction = {
        id: 'txn_mem_1',
        merchantId: 'm1',
        customerId: 'c1',
        amount: 10000,
        currency: 'INR',
        status: TransactionStatus.FAILED,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      await store.saveTransaction(txn);
      const fetched = await store.getTransaction('txn_mem_1');
      expect(fetched).toBeDefined();
      expect(fetched?.id).toBe('txn_mem_1');
      expect(fetched?.amount).toBe(10000);
    });

    it('saves and retrieves recovery cases asynchronously', async () => {
      const recCase: RecoveryCase = {
        id: 'case_mem_1',
        transactionId: 'txn_mem_1',
        merchantId: 'm1',
        customerId: 'c1',
        amount: 10000,
        currency: 'INR',
        state: RecoveryCaseState.DETECTED,
        failureCategory: FailureCategory.INSUFFICIENT_FUNDS,
        riskScore: 0.1,
        riskLevel: RiskLevel.LOW,
        attemptCount: 0,
        customerOptedOut: false,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      await store.saveCase(recCase);
      const fetched = await store.getCase('case_mem_1');
      expect(fetched).toBeDefined();
      expect(fetched?.id).toBe('case_mem_1');

      const byTxn = await store.getCaseByTransactionId('txn_mem_1');
      expect(byTxn?.id).toBe('case_mem_1');
    });

    it('enforces idempotency key setting', async () => {
      const first = await store.checkAndSetIdempotency('key_mem_123');
      expect(first).toBe(true);
      const second = await store.checkAndSetIdempotency('key_mem_123');
      expect(second).toBe(false);
    });

    it('returns system mode information with persistenceMode memory', async () => {
      const mode = await store.getSystemMode();
      expect(mode.persistenceMode).toBe('memory');
      expect(mode.mongoConnected).toBe(false);
    });
  });

  // Opt-in MongoDB integration tests (only run if RUN_MONGODB_TESTS=true or TEST_MONGODB_URI is set)
  const shouldRunMongo = Boolean(process.env['RUN_MONGODB_TESTS'] || process.env['TEST_MONGODB_URI']);
  const mongoUri = process.env['TEST_MONGODB_URI'] || 'mongodb://localhost:27017/recoverai_test';

  describe.runIf(shouldRunMongo)('MongoDataStore Integration Tests (Opt-In)', () => {

    beforeEach(async () => {
      await connectDatabase(mongoUri);
      const store = MongoDataStore.getInstance();
      await store.clear();
    });

    afterAll(async () => {
      await disconnectDatabase();
    });

    it('saves and retrieves transactions from MongoDB', async () => {
      const store = MongoDataStore.getInstance();
      const txn: Transaction = {
        id: 'txn_mongo_1',
        merchantId: 'm1',
        customerId: 'c1',
        amount: 25000,
        currency: 'INR',
        status: TransactionStatus.FAILED,
        failureCategory: FailureCategory.CARD_DECLINED,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      await store.saveTransaction(txn);
      const fetched = await store.getTransaction('txn_mongo_1');
      expect(fetched).toBeDefined();
      expect(fetched?.id).toBe('txn_mongo_1');
      expect(fetched?.amount).toBe(25000);
    });

    it('enforces append-only audit log behavior in MongoDB', async () => {
      const store = MongoDataStore.getInstance();
      await store.addAuditEvent({
        id: 'evt_m1',
        caseId: 'c1',
        transactionId: 't1',
        eventType: 'CASE_CREATED' as any,
        actor: 'SYSTEM',
        timestamp: new Date().toISOString(),
        reason: 'First event',
      });
      await store.addAuditEvent({
        id: 'evt_m2',
        caseId: 'c1',
        transactionId: 't1',
        eventType: 'RISK_ASSESSED' as any,
        actor: 'ML_ENGINE',
        timestamp: new Date().toISOString(),
        reason: 'Second event',
      });

      const events = await store.getAuditEventsByCaseId('c1');
      expect(events.length).toBe(2);
    });

    it('enforces atomic idempotency in MongoDB', async () => {
      const store = MongoDataStore.getInstance();
      const first = await store.checkAndSetIdempotency('key_mongo_456');
      expect(first).toBe(true);

      const second = await store.checkAndSetIdempotency('key_mongo_456');
      expect(second).toBe(false);
    });
  });
});
