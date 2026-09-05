import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppLayout } from './layouts/AppLayout';
import { LandingPage } from './pages/Landing/LandingPage';
import { DashboardPage } from './pages/Dashboard/DashboardPage';
import { RecoveryCasesPage } from './pages/Recovery/RecoveryCasesPage';
import { CaseDetailPage } from './pages/Recovery/CaseDetailPage';
import { TransactionsPage } from './pages/Transactions/TransactionsPage';
import { DecisionsPage } from './pages/Decisions/DecisionsPage';
import { AnalyticsPage } from './pages/Analytics/AnalyticsPage';
import { AuditPage } from './pages/Audit/AuditPage';
import { ExperimentsPage } from './pages/Experiments/ExperimentsPage';

export default function App(): React.JSX.Element {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />

        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/recovery" element={<RecoveryCasesPage />} />
          <Route path="/recovery/:id" element={<CaseDetailPage />} />
          <Route path="/transactions" element={<TransactionsPage />} />
          <Route path="/decisions" element={<DecisionsPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/audit" element={<AuditPage />} />
          <Route path="/experiments" element={<ExperimentsPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
