import { useState, useEffect } from "react";
import { Header } from "./components/layout/Header";
import { Sidebar } from "./components/layout/Sidebar";
import { Footer } from "./components/layout/Footer";
import { MetricsPanel } from "./components/metrics/MetricsPanel";
import { TutorialPanel } from "./components/tutorial/TutorialPanel";
import { SourcesPanel } from "./components/wiki/SourcesPanel";
import { IngestPipelinePanel } from "./components/wiki/IngestPipelinePanel";
import { ChatWithTracePanel } from "./components/chat_with_trace/ChatWithTracePanel";
import { KnowledgeMapPanel } from "./components/wiki/KnowledgeMapPanel";
import { LintPanel } from "./components/lint/LintPanel";
import type { Panel, SessionMetrics } from "./types";
import { api } from "./api/client";
import { startTour, hasSeenTour } from "./components/onboarding/tour";

export default function App() {
  const [activePanel, setActivePanel] = useState<Panel>("ingest");
  const [metrics, setMetrics] = useState<SessionMetrics | null>(null);
  const [focusNode, setFocusNode] = useState<string | null>(null);

  useEffect(() => {
    if (!hasSeenTour()) {
      const t = setTimeout(() => startTour(setActivePanel), 700);
      return () => clearTimeout(t);
    }
  }, []);

  const goToNode = (nodeId: string) => {
    setFocusNode(nodeId);
    setActivePanel("knowledge_map");
  };

  useEffect(() => {
    api.getSessionMetrics().then(setMetrics).catch(() => {});
    const interval = setInterval(() => {
      api.getSessionMetrics().then(setMetrics).catch(() => {});
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <Header metrics={metrics} onStartTour={() => startTour(setActivePanel)} />
      <div className="flex flex-1 flex-col overflow-hidden md:flex-row">
        <Sidebar active={activePanel} onChange={setActivePanel} />
        <main className="flex-1 overflow-auto bg-background">
          {activePanel === "metrics" && <MetricsPanel />}
          {activePanel === "tutorial" && <TutorialPanel />}
          {activePanel === "sources" && <SourcesPanel />}
          {activePanel === "ingest" && <IngestPipelinePanel />}
          {activePanel === "chat_trace" && <ChatWithTracePanel />}
          {activePanel === "knowledge_map" && (
            <KnowledgeMapPanel focusNode={focusNode} onFocusHandled={() => setFocusNode(null)} />
          )}
          {activePanel === "lint" && <LintPanel onLocationClick={goToNode} />}
        </main>
      </div>
      <Footer />
    </div>
  );
}
