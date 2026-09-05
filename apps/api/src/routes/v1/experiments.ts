import { Router } from 'express';
import { Transaction, TransactionStatus, FailureCategory } from '@recoverai/shared-types';
import { recoveryOrchestrator } from '../../services/orchestrator/RecoveryOrchestrator.js';
import { dataStore } from '../../services/store.js';

const experimentsRouter = Router();

// POST /api/v1/experiments/demo
experimentsRouter.post('/demo', async (_req, res, next) => {
  try {
    await dataStore.clear();

    const sampleFailures = [
      { cat: FailureCategory.INSUFFICIENT_FUNDS, code: 'insufficient_funds', amount: 49900, method: 'upi', dev: false, loc: false },
      { cat: FailureCategory.CARD_DECLINED, code: 'do_not_honor', amount: 125000, method: 'card', dev: false, loc: false },
      { cat: FailureCategory.AUTHENTICATION_FAILED, code: '3ds_auth_failed', amount: 89000, method: 'card', dev: true, loc: false },
      { cat: FailureCategory.NETWORK_ERROR, code: 'network_timeout', amount: 349900, method: 'upi', dev: false, loc: false },
      { cat: FailureCategory.FRAUD_SUSPECTED, code: 'suspicious_pattern', amount: 999900, method: 'card', dev: true, loc: true },
      { cat: FailureCategory.BANK_TIMEOUT, code: 'bank_timeout', amount: 159900, method: 'netbanking', dev: false, loc: false },
      { cat: FailureCategory.CARD_EXPIRED, code: 'expired_card', amount: 24900, method: 'card', dev: false, loc: false },
      { cat: FailureCategory.LIMIT_EXCEEDED, code: 'limit_exceeded', amount: 450000, method: 'card', dev: false, loc: false },
      { cat: FailureCategory.INSUFFICIENT_FUNDS, code: 'insufficient_funds', amount: 79900, method: 'upi', dev: false, loc: false },
      { cat: FailureCategory.AUTHENTICATION_FAILED, code: 'otp_expired', amount: 199900, method: 'upi', dev: false, loc: false },
    ];

    const processedCases = [];

    for (let i = 0; i < sampleFailures.length; i++) {
      const f = sampleFailures[i]!;
      const txnId = `pay_demo_${1000 + i}`;
      const custId = `cust_${(i % 4) + 1}`;

      const txn: Transaction = {
        id: txnId,
        merchantId: 'merch_demo_101',
        customerId: custId,
        amount: f.amount,
        currency: 'INR',
        status: TransactionStatus.FAILED,
        failureCategory: f.cat,
        failureCode: f.code,
        deviceChanged: f.dev,
        locationChanged: f.loc,
        createdAt: new Date(Date.now() - (10 - i) * 3600000).toISOString(),
        updatedAt: new Date().toISOString(),
        metadata: {
          paymentMethod: f.method,
        },
      };

      const newCase = await recoveryOrchestrator.createCase(txn);
      
      if (custId === 'cust_4') {
        newCase.customerOptedOut = true;
        await dataStore.saveCase(newCase);
      }

      await recoveryOrchestrator.analyzeCase(newCase.id);
      await recoveryOrchestrator.executeAction(newCase.id, `idem_demo_${newCase.id}`);

      const savedCase = await dataStore.getCase(newCase.id);
      if (savedCase) {
        processedCases.push(savedCase);
      }
    }

    const summary = await dataStore.getAnalyticsSummary();

    res.json({
      success: true,
      data: {
        message: 'Deterministic seed=42 demo suite executed successfully.',
        casesCount: processedCases.length,
        analytics: summary,
      },
    });
  } catch (err) {
    next(err);
  }
});

export default experimentsRouter;
