import { useState, useEffect } from "react";
import type { DocumentMeta, DocumentDetail, EmbeddingStatus } from "../../types";
import { api } from "../../api/client";
import { UploadZone } from "./UploadZone";
import { DocumentList } from "./DocumentList";
import { CrawlPanel } from "./CrawlPanel";
import { KnowledgeBaseHealth } from "./KnowledgeBaseHealth";

type Tab = "upload" | "crawl";

export function DocumentManager() {
  const [tab, setTab] = useState<Tab>("upload");
  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [selected, setSelected] = useState<DocumentDetail | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [embeddingStatus, setEmbeddingStatus] = useState<EmbeddingStatus[]>([]);

  useEffect(() => {
    api.listDocuments().then(setDocuments).catch(console.error);
    api.getEmbeddingStatus().then(setEmbeddingStatus).catch(() => {});
  }, []);

  async function handleSelect(doc: DocumentMeta) {
    setLoadingPreview(true);
    try {
      const detail = await api.getDocument(doc.id);
      setSelected(detail);
    } finally {
      setLoadingPreview(false);
    }
  }

  async function handleDelete(id: string) {
    await api.deleteDocument(id);
    setDocuments((prev) => prev.filter((d) => d.id !== id));
    if (selected?.id === id) setSelected(null);
  }

  function handleCrawled(added: DocumentMeta[]) {
    if (added.length > 0) {
      setDocuments((prev) => [...added, ...prev]);
    }
  }

  const embeddedDocs = embeddingStatus.length;
  const totalChunks = embeddingStatus.reduce((sum, s) => sum + s.chunk_count, 0);
  const totalChars = documents.reduce((sum, d) => sum + d.char_count, 0);

  return (
    <div className="p-6 h-full flex gap-6">
      <div className="w-80 shrink-0 space-y-4">
        {/* Tabs */}
        <div className="flex border-b">
          {(["upload", "crawl"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
                tab === t
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {t === "upload" ? "Upload File" : "From URL"}
            </button>
          ))}
        </div>

        {tab === "upload" && (
          <UploadZone onUploaded={(doc) => setDocuments((prev) => [doc, ...prev])} />
        )}
        {tab === "crawl" && (
          <CrawlPanel onDocumentsAdded={handleCrawled} />
        )}

        <h2 className="font-semibold text-sm">Documents ({documents.length})</h2>
        <DocumentList
          documents={documents}
          selectedId={selected?.id ?? null}
          onSelect={handleSelect}
          onDelete={handleDelete}
        />
      </div>

      <div className="flex-1 border rounded-lg bg-card border-border p-4 overflow-auto">
        {loadingPreview && <p className="text-sm text-muted-foreground">Loading...</p>}
        {!loadingPreview && selected && (
          <>
            <h3 className="font-semibold text-sm mb-3">{selected.name} — Raw Text</h3>
            <pre className="text-xs whitespace-pre-wrap font-mono text-muted-foreground leading-relaxed">
              {selected.raw_text}
            </pre>
          </>
        )}
        {!loadingPreview && !selected && (
          <p className="text-sm text-muted-foreground">Select a document to preview its extracted text.</p>
        )}
      </div>

      {/* Right — KB Health */}
      <div className="w-52 shrink-0">
        <KnowledgeBaseHealth
          totalDocs={documents.length}
          embeddedDocs={embeddedDocs}
          totalChunks={totalChunks}
          totalChars={totalChars}
        />
      </div>
    </div>
  );
}
