import { useEffect, useState } from "react";

import { getHealthStatus, type HealthStatus } from "../lib/api";

type HealthState =
  | { status: "loading" }
  | { status: "ready"; payload: HealthStatus }
  | { status: "error"; message: string };

export function HomePage() {
  const [healthState, setHealthState] = useState<HealthState>({ status: "loading" });

  useEffect(() => {
    let isMounted = true;

    getHealthStatus()
      .then((payload) => {
        if (!isMounted) {
          return;
        }
        setHealthState({ status: "ready", payload });
      })
      .catch((error: unknown) => {
        if (!isMounted) {
          return;
        }
        const message =
          error instanceof Error ? error.message : "Unexpected error while loading health status";
        setHealthState({ status: "error", message });
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <main className="page">
      <section className="panel">
        <p className="eyebrow">Trend Discovery MVP</p>
        <h1>Content Factory Control Room</h1>
        <p className="subtitle">
          Frontend scaffold is live. Next steps: settings form, run console, shortlist.
        </p>
        <div className="health-card">
          <h2>API Health</h2>
          {healthState.status === "loading" && <p className="muted">Checking backend...</p>}
          {healthState.status === "ready" && (
            <ul className="kv">
              <li>
                <span>Service</span>
                <strong>{healthState.payload.service}</strong>
              </li>
              <li>
                <span>Status</span>
                <strong className="ok">{healthState.payload.status}</strong>
              </li>
              <li>
                <span>Version</span>
                <strong>{healthState.payload.version}</strong>
              </li>
            </ul>
          )}
          {healthState.status === "error" && (
            <p className="error">Cannot reach backend: {healthState.message}</p>
          )}
        </div>
      </section>
    </main>
  );
}
