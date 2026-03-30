import { useState, useEffect } from "react";
import { Header } from "./components/layout/Header";
import { Sidebar } from "./components/layout/Sidebar";
import { Footer } from "./components/layout/Footer";
import { Panel, SessionMetrics } from "./types";
import { api } from "./api/client";

function PanelContent({ panel }: { panel: Panel }) {
  return (
    <div className="flex-1 p-6 text-sm text-muted-foreground">
      Panel: <strong>{panel}</strong> — coming soon
    </div>
  );
}

export default function App() {
  const [activePanel, setActivePanel] = useState<Panel>("documents");
  const [metrics, setMetrics] = useState<SessionMetrics | null>(null);

  useEffect(() => {
    api.getSessionMetrics().then(setMetrics).catch(() => {});
    const interval = setInterval(() => {
      api.getSessionMetrics().then(setMetrics).catch(() => {});
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <Header metrics={metrics} />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar active={activePanel} onChange={setActivePanel} />
        <main className="flex-1 overflow-auto bg-[#F9FAFB]">
          <PanelContent panel={activePanel} />
        </main>
      </div>
      <Footer />
    </div>
  );
}
