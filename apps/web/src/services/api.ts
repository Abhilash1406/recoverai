const API_BASE = 'http://localhost:5000/api/v1';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

export async function triggerDemoSuite() {
  const res = await fetch(`${API_BASE}/experiments/demo`, { method: 'POST' });
  return res.json();
}

export async function fetchAnalyticsSummary() {
  const res = await fetch(`${API_BASE}/analytics/summary`);
  return res.json();
}

export async function fetchRecoveryCases() {
  const res = await fetch(`${API_BASE}/recovery/cases`);
  return res.json();
}

export async function fetchCaseDetail(caseId: string) {
  const res = await fetch(`${API_BASE}/recovery/cases/${caseId}`);
  return res.json();
}

export async function analyzeCase(caseId: string) {
  const res = await fetch(`${API_BASE}/recovery/cases/${caseId}/analyze`, { method: 'POST' });
  return res.json();
}

export async function executeCaseAction(caseId: string) {
  const res = await fetch(`${API_BASE}/recovery/cases/${caseId}/execute`, { method: 'POST' });
  return res.json();
}

export async function fetchTransactions() {
  const res = await fetch(`${API_BASE}/transactions`);
  return res.json();
}

export async function fetchAuditLogs() {
  const res = await fetch(`${API_BASE}/audit`);
  return res.json();
}

export async function fetchDecisions() {
  const res = await fetch(`${API_BASE}/decisions`);
  return res.json();
}
