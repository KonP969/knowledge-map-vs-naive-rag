import { useState } from "react";
import { SectionIntro } from "./sections/SectionIntro";
import { SectionNaiveRag } from "./sections/SectionNaiveRag";
import { SectionIngest } from "./sections/SectionIngest";
import { SectionRetrieval } from "./sections/SectionRetrieval";
import { SectionQuerying } from "./sections/SectionQuerying";
import { SectionWalkthroughs } from "./sections/SectionWalkthroughs";

type TabId = "intro" | "naive-rag" | "ingest" | "retrieval" | "querying" | "walkthroughs";

const TABS: { id: TabId; label: string }[] = [
  { id: "intro", label: "Knowledge Map RAG" },
  { id: "naive-rag", label: "Dlaczego nie naive RAG" },
  { id: "ingest", label: "Jak działa ingest" },
  { id: "retrieval", label: "Jak działa retrieval" },
  { id: "querying", label: "Jak pytać" },
  { id: "walkthroughs", label: "Przewodniki" },
];

export function TutorialPanel() {
  const [activeTab, setActiveTab] = useState<TabId>("intro");

  return (
    <div className="max-w-3xl mx-auto p-6">
      <div className="mb-5">
        <h1 className="text-2xl font-bold text-foreground mb-1">RAG 2.0 — Knowledge Map</h1>
        <p className="text-muted-foreground text-sm">Kompletny przewodnik systemu opartego na wiedzy strukturalnej.</p>
      </div>

      <div className="flex gap-0.5 flex-wrap border-b border-border mb-6">
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-3 py-2 text-sm rounded-t transition-colors border-b-2 -mb-px ${
              activeTab === tab.id
                ? "border-primary text-primary font-medium bg-primary/5"
                : "border-transparent text-muted-foreground hover:text-foreground hover:bg-muted/40"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "intro" && <SectionIntro />}
      {activeTab === "naive-rag" && <SectionNaiveRag />}
      {activeTab === "ingest" && <SectionIngest />}
      {activeTab === "retrieval" && <SectionRetrieval />}
      {activeTab === "querying" && <SectionQuerying />}
      {activeTab === "walkthroughs" && <SectionWalkthroughs />}
    </div>
  );
}
