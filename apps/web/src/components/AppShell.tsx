import { Outlet } from "react-router-dom";

import { AppNav } from "./AppNav";

export function AppShell() {
  return (
    <div className="app-shell">
      <AppNav />
      <main className="app-shell-main">
        <Outlet />
      </main>
    </div>
  );
}
