import { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { ChevronDown, ChevronUp, Search } from "lucide-react";
import type { DocumentMeta, EmbeddingStatus } from "../../types";

interface DocPickerProps {
  documents: DocumentMeta[];
  chunkCounts: Record<string, number>;
  embeddingStatus: EmbeddingStatus[];
  selectedDocId: string;
  onSelect: (docId: string) => void;
  onDelete: (doc: DocumentMeta) => void;
}

export function DocPicker({
  documents,
  chunkCounts,
  embeddingStatus,
  selectedDocId,
  onSelect,
  onDelete,
}: DocPickerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const triggerRef = useRef<HTMLButtonElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const [overlayTop, setOverlayTop] = useState(0);
  const [overlayLeft, setOverlayLeft] = useState(0);

  const embeddedDocIds = new Set(embeddingStatus.map((s) => s.document_id));
  const selectedDoc = documents.find((d) => d.id === selectedDocId);
  const selectedChunkCount =
    selectedDocId !== "" ? chunkCounts[selectedDocId] : undefined;

  const filtered = documents.filter((d) =>
    d.name.toLowerCase().includes(search.toLowerCase())
  );

  function open() {
    if (triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      setOverlayTop(rect.bottom + 4);
      setOverlayLeft(rect.left);
    }
    setIsOpen(true);
  }

  function close() {
    setIsOpen(false);
    setSearch("");
  }

  useEffect(() => {
    if (isOpen && searchRef.current) {
      searchRef.current.focus();
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setIsOpen(false);
        setSearch("");
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [isOpen]);

  return (
    <div className="relative mt-1">
      <button
        ref={triggerRef}
        onClick={() => (isOpen ? close() : open())}
        className="w-full flex items-center gap-2 px-2.5 py-1.5 text-xs bg-muted border border-border rounded-md hover:border-primary/50 transition-colors text-left"
      >
        <span className="flex-1 truncate text-foreground">
          {selectedDoc ? selectedDoc.name : "Wybierz dokument"}
        </span>
        {selectedChunkCount !== undefined && (
          <span className="text-muted-foreground text-[10px] shrink-0">
            {selectedChunkCount} ch
          </span>
        )}
        {isOpen ? (
          <ChevronUp className="w-3 h-3 text-muted-foreground shrink-0" />
        ) : (
          <ChevronDown className="w-3 h-3 text-muted-foreground shrink-0" />
        )}
      </button>

      {isOpen &&
        createPortal(
          <>
            {/* Invisible backdrop */}
            <div className="fixed inset-0 z-40" onClick={close} />

            {/* Overlay panel */}
            <div
              className="fixed z-50 bg-card border border-border rounded-lg shadow-2xl overflow-hidden"
              style={{ top: overlayTop, left: overlayLeft, right: 16 }}
            >
              {/* Search header */}
              <div className="flex items-center gap-2 px-3 py-2 border-b border-border">
                <Search className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                <input
                  ref={searchRef}
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Szukaj dokumentu…"
                  className="flex-1 text-xs bg-transparent outline-none text-foreground placeholder:text-muted-foreground"
                />
                <span className="text-[10px] text-muted-foreground shrink-0">
                  {filtered.length} doc{filtered.length !== 1 ? "s" : ""}
                </span>
              </div>

              {/* Document grid */}
              <div
                className="p-3 grid gap-2 overflow-y-auto max-h-72"
                style={{
                  gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
                }}
              >
                {filtered.length === 0 && (
                  <p className="col-span-full text-xs text-muted-foreground text-center py-4">
                    Brak dokumentów pasujących do „{search}"
                  </p>
                )}
                {filtered.map((doc) => (
                  <DocTile
                    key={doc.id}
                    doc={doc}
                    chunkCount={chunkCounts[doc.id] ?? null}
                    hasEmbeddings={embeddedDocIds.has(doc.id)}
                    isActive={doc.id === selectedDocId}
                    onSelect={() => {
                      onSelect(doc.id);
                      close();
                    }}
                    onDelete={() => {
                      onDelete(doc);
                      close();
                    }}
                  />
                ))}
              </div>
            </div>
          </>,
          document.body
        )}
    </div>
  );
}

interface DocTileProps {
  doc: DocumentMeta;
  chunkCount: number | null;
  hasEmbeddings: boolean;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
}

function DocTile({
  doc,
  chunkCount,
  hasEmbeddings,
  isActive,
  onSelect,
  onDelete,
}: DocTileProps) {
  return (
    <div
      onClick={onSelect}
      className={`group relative cursor-pointer rounded-md border px-2.5 py-2 transition-colors ${
        isActive
          ? "border-primary bg-primary/10"
          : "border-border bg-muted hover:border-primary/40"
      }`}
    >
      <p
        className={`text-[11px] font-medium truncate pr-4 ${
          isActive ? "text-primary" : "text-foreground"
        }`}
      >
        {doc.name}
      </p>
      <p className="text-[10px] text-muted-foreground mt-0.5">
        {chunkCount !== null ? `${chunkCount} ch` : "—"}
        {hasEmbeddings && (
          <span className="text-success/70 ml-1">· emb</span>
        )}
      </p>
      <button
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        className="absolute top-1 right-1.5 text-[10px] text-muted-foreground opacity-0 group-hover:opacity-100 focus:opacity-100 hover:text-error transition-opacity leading-none"
        title="Usuń dokument"
      >
        ✕
      </button>
    </div>
  );
}
