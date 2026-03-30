import { useState, useEffect } from "react";
import type { DocumentMeta, DocumentDetail } from "../../types";
import { api } from "../../api/client";
import { UploadZone } from "./UploadZone";
import { DocumentList } from "./DocumentList";

export function DocumentManager() {
  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [selected, setSelected] = useState<DocumentDetail | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);

  useEffect(() => {
    api.listDocuments().then(setDocuments).catch(console.error);
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

  return (
    <div className="p-6 h-full flex gap-6">
      <div className="w-80 shrink-0 space-y-4">
        <h2 className="font-semibold text-sm">Upload Document</h2>
        <UploadZone onUploaded={(doc) => setDocuments((prev) => [doc, ...prev])} />
        <h2 className="font-semibold text-sm">Documents ({documents.length})</h2>
        <DocumentList
          documents={documents}
          selectedId={selected?.id ?? null}
          onSelect={handleSelect}
          onDelete={handleDelete}
        />
      </div>
      <div className="flex-1 border rounded-lg bg-white p-4 overflow-auto">
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
    </div>
  );
}
