import { useState, useEffect } from "react";
import { Header } from "./components/layout/Header";
import { Sidebar } from "./components/layout/Sidebar";
import { Footer } from "./components/layout/Footer";
import { DocumentManager } from "./components/documents/DocumentManager";
import { ChunkingLab } from "./components/chunks/ChunkingLab";
import { EmbeddingExplorer } from "./components/embeddings/EmbeddingExplorer";
import { ChatInterface } from "./components/chat/ChatInterface";
import { MetricsPanel } from "./components/metrics/MetricsPanel";
import { TutorialPanel } from "./components/tutorial/TutorialPanel";
import { SourcesPanel } from "./components/wiki/SourcesPanel";
import { IngestPipelinePanel } from "./components/wiki/IngestPipelinePanel";
import { ChatWithTracePanel } from "./components/chat_with_trace/ChatWithTracePanel";
import { KnowledgeMapPanel } from "./components/wiki/KnowledgeMapPanel";
import type { Panel, SessionMetrics } from "./types";
import { api } from "./api/client";

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
        <main className="flex-1 overflow-auto bg-background">
          {activePanel === "documents" && <DocumentManager />}
          {activePanel === "chunks" && <ChunkingLab />}
          {activePanel === "embeddings" && <EmbeddingExplorer />}
          {activePanel === "chat" && <ChatInterface />}
          {activePanel === "metrics" && <MetricsPanel />}
          {activePanel === "tutorial" && <TutorialPanel />}
          {activePanel === "sources" && <SourcesPanel />}
          {activePanel === "ingest" && <IngestPipelinePanel />}
          {activePanel === "chat_trace" && <ChatWithTracePanel />}
          {activePanel === "knowledge_map" && <KnowledgeMapPanel />}
        </main>
      </div>
      <Footer />
    </div>
  );
}
