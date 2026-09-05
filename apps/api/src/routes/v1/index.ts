import { Router } from 'express';
import healthRouter from './health.js';
import transactionsRouter from './transactions.js';
import recoveryRouter from './recovery.js';
import decisionsRouter from './decisions.js';
import auditRouter from './audit.js';
import analyticsRouter from './analytics.js';
import experimentsRouter from './experiments.js';
import webhooksRouter from './webhooks.js';

const v1Router = Router();

v1Router.use('/health', healthRouter);
v1Router.use('/transactions', transactionsRouter);
v1Router.use('/recovery', recoveryRouter);
v1Router.use('/decisions', decisionsRouter);
v1Router.use('/audit', auditRouter);
v1Router.use('/analytics', analyticsRouter);
v1Router.use('/experiments', experimentsRouter);
v1Router.use('/webhooks', webhooksRouter);

export default v1Router;
