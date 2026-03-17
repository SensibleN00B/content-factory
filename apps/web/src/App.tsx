import { Navigate, Route, Routes } from "react-router-dom";

import { HomePage } from "./pages/HomePage";
import { RunConsolePage } from "./pages/RunConsolePage";
import { SettingsPage } from "./pages/SettingsPage";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/runs" element={<RunConsolePage />} />
      <Route path="/settings" element={<SettingsPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
