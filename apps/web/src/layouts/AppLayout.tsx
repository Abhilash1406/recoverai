import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from '../components/layout/Sidebar';

/**
 * AppLayout — persistent shell for authenticated/dashboard pages
 *
 * Contains the sidebar navigation and a content area.
 * Will include a topbar in Phase 2+.
 */
export function AppLayout(): React.JSX.Element {
  return (
    <div className="flex h-screen overflow-hidden bg-surface">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
