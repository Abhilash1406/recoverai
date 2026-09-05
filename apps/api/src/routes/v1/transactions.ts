import { Router } from 'express';
import { dataStore } from '../../services/store.js';

const transactionsRouter = Router();

// GET /api/v1/transactions
transactionsRouter.get('/', async (_req, res, next) => {
  try {
    const transactions = await dataStore.getAllTransactions();
    res.json({
      success: true,
      data: transactions,
      meta: { total: transactions.length },
    });
  } catch (err) {
    next(err);
  }
});

// GET /api/v1/transactions/:id
transactionsRouter.get('/:id', async (req, res, next) => {
  try {
    const txn = await dataStore.getTransaction(req.params.id);
    if (!txn) {
      res.status(404).json({
        success: false,
        error: { message: `Transaction ${req.params.id} not found` },
      });
      return;
    }
    res.json({ success: true, data: txn });
  } catch (err) {
    next(err);
  }
});

export default transactionsRouter;
