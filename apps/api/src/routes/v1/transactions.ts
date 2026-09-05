import { Router } from 'express';
import { dataStore } from '../../services/store.js';

const transactionsRouter = Router();

// GET /api/v1/transactions
transactionsRouter.get('/', (_req, res) => {
  const transactions = dataStore.getAllTransactions();
  res.json({
    success: true,
    data: transactions,
    meta: { total: transactions.length },
  });
  return;
});

// GET /api/v1/transactions/:id
transactionsRouter.get('/:id', (req, res) => {
  const txn = dataStore.getTransaction(req.params.id);
  if (!txn) {
    res.status(404).json({
      success: false,
      error: { message: `Transaction ${req.params.id} not found` },
    });
    return;
  }
  res.json({ success: true, data: txn });
  return;
});

export default transactionsRouter;
