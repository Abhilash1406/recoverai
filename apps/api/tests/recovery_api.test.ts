import { describe, it, expect } from 'vitest';
import request from 'supertest';
import { createApp } from '../src/app.js';

const app = createApp();

describe('Phase 4 REST API Endpoints', () => {
  it('GET /api/v1/health returns 200', async () => {
    const res = await request(app).get('/api/v1/health');
    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
  });

  it('POST /api/v1/experiments/demo executes deterministic demo suite', async () => {
    const res = await request(app).post('/api/v1/experiments/demo');
    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(res.body.data.casesCount).toBe(10);
    expect(res.body.data.analytics.totalCases).toBe(10);
  });

  it('GET /api/v1/transactions returns transaction list after demo run', async () => {
    const res = await request(app).get('/api/v1/transactions');
    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(res.body.data.length).toBeGreaterThanOrEqual(10);
  });

  it('GET /api/v1/recovery/cases returns recovery cases', async () => {
    const res = await request(app).get('/api/v1/recovery/cases');
    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(res.body.data.length).toBeGreaterThanOrEqual(10);
  });

  it('GET /api/v1/analytics/summary returns dashboard metrics', async () => {
    const res = await request(app).get('/api/v1/analytics/summary');
    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(res.body.data.totalRevenueAtRisk).toBeGreaterThan(0);
    expect(res.body.data.recoveryRate).toBeDefined();
  });

  it('GET /api/v1/audit returns immutable audit log', async () => {
    const res = await request(app).get('/api/v1/audit');
    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(res.body.data.length).toBeGreaterThan(0);
  });
});
