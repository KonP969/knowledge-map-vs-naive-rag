import { useState, useEffect, useCallback } from "react";
import type { DocumentMeta, DocumentDetail, EmbeddingStatus, Folder } from "../../types";
import { api } from "../../api/client";
import { UploadZone } from "./UploadZone";
import { DocumentList } from "./DocumentList";
import { CrawlPanel } from "./CrawlPanel";
import { KnowledgeBaseHealth } from "./KnowledgeBaseHealth";
import { DeleteConfirmModal } from "../shared/DeleteConfirmModal";
import { FolderAssignModal } from "./FolderAssignModal";

type Tab = "upload" | "crawl";

export function DocumentManager() {
  const [tab, setTab] = useState<Tab>("upload");
  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [selected, setSelected] = useState<DocumentDetail | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [embeddingStatus, setEmbeddingStatus] = useState<EmbeddingStatus[]>([]);

  // Delete state
  const [docToDelete, setDocToDelete] = useState<DocumentMeta | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  // Folder assign state
  const [docsToAssign, setDocsToAssign] = useState<DocumentMeta[]>([]);
  const [showFolderModal, setShowFolderModal] = useState(false);

  // Folders and filter state
  const [folders, setFolders] = useState<Folder[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeFolderId, setActiveFolderId] = useState<string | null>("all");

  useEffect(() => {
    api.listDocuments().then(setDocuments).catch(console.error);
    api.getEmbeddingStatus().then(setEmbeddingStatus).catch(() => {});
    api.getFolders().then(setFolders).catch(() => {});
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

  const handleDeleteRequest = useCallback((doc: DocumentMeta) => {
    setDocToDelete(doc);
  }, []);

  const handleDeleteCancel = useCallback(() => {
    setDocToDelete(null);
  }, []);

  const handleDeleteConfirm = useCallback(async () => {
    if (!docToDelete) return;
    setDeleteLoading(true);
    const id = docToDelete.id;
    try {
      await api.deleteChunks(id).catch(() => {});
      await api.deleteEmbeddingsByDocument(id).catch(() => {});
      await api.deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
      if (selected?.id === id) setSelected(null);
    } finally {
      setDeleteLoading(false);
      setDocToDelete(null);
    }
  }, [docToDelete, selected]);

  const handleFolderAssign = useCallback(async (folderId: string | null) => {
    await Promise.all(
      docsToAssign.map((doc) => api.assignDocumentToFolder(doc.id, folderId))
    );
    setDocuments((prev) =>
      prev.map((d) =>
        docsToAssign.some((da) => da.id === d.id) ? { ...d, folder_id: folderId } : d
      )
    );
    setShowFolderModal(false);
    setDocsToAssign([]);
  }, [docsToAssign]);

  const handleFolderSkip = useCallback(() => {
    setShowFolderModal(false);
    setDocsToAssign([]);
  }, []);

  const handleCreateFolder = useCallback(async (name: string): Promise<Folder> => {
    const folder = await api.createFolder(name);
    setFolders((prev) => [...prev, folder]);
    return folder;
  }, []);

  function handleCrawled(added: DocumentMeta[]) {
    if (added.length > 0) {
      setDocuments((prev) => [...added, ...prev]);
      setDocsToAssign(added);
      setShowFolderModal(true);
    }
  }

  const embeddedDocs = embeddingStatus.length;
  const totalChunks = embeddingStatus.reduce((sum, s) => sum + s.chunk_count, 0);
  const totalChars = documents.reduce((sum, d) => sum + d.char_count, 0);

  const filteredDocuments = documents
    .filter((d) => {
      if (activeFolderId === "all") return true;
      if (activeFolderId === null) return !d.folder_id;
      return d.folder_id === activeFolderId;
    })
    .filter((d) =>
      searchQuery === "" || d.name.toLowerCase().includes(searchQuery.toLowerCase())
    );

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
          <UploadZone
            onUploaded={(doc) => {
              setDocuments((prev) => [doc, ...prev]);
              setDocsToAssign([doc]);
              setShowFolderModal(true);
            }}
          />
        )}
        {tab === "crawl" && (
          <CrawlPanel onDocumentsAdded={handleCrawled} />
        )}

        {/* Folder filter chips */}
        {folders.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {[
              { id: "all", label: "Wszystkie", count: documents.length },
              ...folders.map((f) => ({
                id: f.id,
                label: f.name,
                count: documents.filter((d) => d.folder_id === f.id).length,
              })),
              {
                id: null as null,
                label: "Bez folderu",
                count: documents.filter((d) => !d.folder_id).length,
              },
            ].map(({ id, label, count }) => (
              <button
                key={id ?? "__none"}
                onClick={() => setActiveFolderId(id)}
                className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${
                  activeFolderId === id
                    ? "bg-primary/15 border-primary/60 text-primary"
                    : "border-border text-muted-foreground hover:border-primary/40 hover:text-foreground"
                }`}
              >
                {label} <span className="opacity-60">{count}</span>
              </button>
            ))}
          </div>
        )}

        {/* Search */}
        <div className="relative">
          <input
            type="text"
            placeholder="Szukaj dokumentów…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full text-sm border border-border rounded-md px-3 py-1.5 bg-muted text-foreground outline-none focus:border-primary placeholder:text-muted-foreground"
          />
        </div>

        <h2 className="font-semibold text-sm">Documents ({filteredDocuments.length})</h2>
        <DocumentList
          documents={filteredDocuments}
          selectedId={selected?.id ?? null}
          onSelect={handleSelect}
          onDeleteRequest={handleDeleteRequest}
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

      <div className="w-52 shrink-0">
        <KnowledgeBaseHealth
          totalDocs={documents.length}
          embeddedDocs={embeddedDocs}
          totalChunks={totalChunks}
          totalChars={totalChars}
        />
      </div>

      {docToDelete && (
        <DeleteConfirmModal
          doc={docToDelete}
          chunkCount={null}
          isLoading={deleteLoading}
          onConfirm={handleDeleteConfirm}
          onCancel={handleDeleteCancel}
        />
      )}

      {showFolderModal && docsToAssign.length > 0 && (
        <FolderAssignModal
          docs={docsToAssign}
          folders={folders}
          onAssign={handleFolderAssign}
          onSkip={handleFolderSkip}
          onCreateFolder={handleCreateFolder}
        />
      )}
    </div>
  );
}
