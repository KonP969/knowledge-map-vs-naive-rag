import { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import {
  ChevronDown, ChevronUp, Search, FolderPlus, Folder,
  Check, X, CheckSquare,
} from "lucide-react";
import type { DocumentMeta, EmbeddingStatus, Folder as FolderType } from "../../types";

type FolderFilter = "all" | "unassigned" | string;
type ChunkFilter = "pending" | "ready";

interface DocPickerProps {
  documents: DocumentMeta[];
  chunkCounts: Record<string, number>;
  embeddingStatus: EmbeddingStatus[];
  selectedDocId: string;
  onSelect: (docId: string) => void;
  onDelete: (doc: DocumentMeta) => void;
  folders: FolderType[];
  onCreateFolder: (name: string) => Promise<void>;
  onAssignFolder: (docId: string, folderId: string | null) => Promise<void>;
  lockedChunkFilter?: ChunkFilter;
}

export function DocPicker({
  documents,
  chunkCounts,
  embeddingStatus,
  selectedDocId,
  onSelect,
  onDelete,
  folders,
  onCreateFolder,
  onAssignFolder,
  lockedChunkFilter,
}: DocPickerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [activeFolder, setActiveFolder] = useState<FolderFilter>("all");
  const [chunkFilter, setChunkFilter] = useState<ChunkFilter>(lockedChunkFilter ?? "pending");
  const [creatingFolder, setCreatingFolder] = useState(false);
  const [newFolderName, setNewFolderName] = useState("");
  const [checkedDocs, setCheckedDocs] = useState<Set<string>>(new Set());
  const [bulkFolderMenuOpen, setBulkFolderMenuOpen] = useState(false);

  const triggerRef = useRef<HTMLButtonElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const newFolderRef = useRef<HTMLInputElement>(null);
  const [overlayTop, setOverlayTop] = useState(0);
  const [overlayLeft, setOverlayLeft] = useState(0);

  const embeddedDocIds = new Set(embeddingStatus.map((s) => s.document_id));
  const selectedDoc = documents.find((d) => d.id === selectedDocId);
  const selectedChunkCount = selectedDocId !== "" ? chunkCounts[selectedDocId] : undefined;

  const readyCount = documents.filter((d) => (chunkCounts[d.id] ?? 0) > 0).length;
  const pendingCount = documents.filter((d) => !(chunkCounts[d.id] > 0)).length;

  // When filter is locked, chip counts should reflect only visible docs
  const baseForCounts = lockedChunkFilter
    ? documents.filter((d) =>
        lockedChunkFilter === "ready"
          ? (chunkCounts[d.id] ?? 0) > 0
          : !(chunkCounts[d.id] > 0)
      )
    : documents;

  const byFolder = documents.filter((d) => {
    if (activeFolder === "all") return true;
    if (activeFolder === "unassigned") return !d.folder_id;
    return d.folder_id === activeFolder;
  });

  const byChunk = byFolder.filter((d) =>
    chunkFilter === "ready" ? (chunkCounts[d.id] ?? 0) > 0 : !(chunkCounts[d.id] > 0)
  );

  const filtered = byChunk.filter((d) =>
    d.name.toLowerCase().includes(search.toLowerCase())
  );

  const allVisibleChecked =
    filtered.length > 0 && filtered.every((d) => checkedDocs.has(d.id));

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
    setCreatingFolder(false);
    setNewFolderName("");
    setChunkFilter(lockedChunkFilter ?? "pending");
    setCheckedDocs(new Set());
    setBulkFolderMenuOpen(false);
  }

  function toggleCheck(docId: string) {
    setCheckedDocs((prev) => {
      const next = new Set(prev);
      next.has(docId) ? next.delete(docId) : next.add(docId);
      return next;
    });
  }

  function toggleAllVisible() {
    if (allVisibleChecked) {
      setCheckedDocs((prev) => {
        const next = new Set(prev);
        filtered.forEach((d) => next.delete(d.id));
        return next;
      });
    } else {
      setCheckedDocs((prev) => {
        const next = new Set(prev);
        filtered.forEach((d) => next.add(d.id));
        return next;
      });
    }
  }

  async function bulkAssign(folderId: string | null) {
    setBulkFolderMenuOpen(false);
    await Promise.all([...checkedDocs].map((id) => onAssignFolder(id, folderId)));
    setCheckedDocs(new Set());
  }

  useEffect(() => {
    if (isOpen && searchRef.current) searchRef.current.focus();
  }, [isOpen]);

  useEffect(() => {
    if (creatingFolder && newFolderRef.current) newFolderRef.current.focus();
  }, [creatingFolder]);

  useEffect(() => {
    if (!isOpen) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        if (bulkFolderMenuOpen) { setBulkFolderMenuOpen(false); return; }
        close();
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [isOpen, bulkFolderMenuOpen]);

  async function commitCreateFolder() {
    const name = newFolderName.trim();
    if (name) await onCreateFolder(name);
    setCreatingFolder(false);
    setNewFolderName("");
  }

  const unassignedCount = baseForCounts.filter((d) => !d.folder_id).length;

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
          <span className="text-muted-foreground text-[10px] shrink-0">{selectedChunkCount} ch</span>
        )}
        {isOpen
          ? <ChevronUp className="w-3 h-3 text-muted-foreground shrink-0" />
          : <ChevronDown className="w-3 h-3 text-muted-foreground shrink-0" />}
      </button>

      {isOpen &&
        createPortal(
          <>
            <div className="fixed inset-0 z-40" onClick={close} />

            <div
              className="fixed z-50 bg-card border border-border rounded-lg shadow-2xl flex flex-col"
              style={{ top: overlayTop, left: overlayLeft, right: 16, maxHeight: 460 }}
            >
              {/* Search header */}
              <div className="flex items-center gap-2 px-3 py-2 border-b border-border shrink-0">
                <Search className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                <input
                  ref={searchRef}
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Szukaj dokumentu…"
                  className="flex-1 text-xs bg-transparent outline-none text-foreground placeholder:text-muted-foreground"
                />
                {/* Select-all toggle */}
                <button
                  onClick={(e) => { e.stopPropagation(); toggleAllVisible(); }}
                  className={`flex items-center gap-1 text-[10px] transition-colors shrink-0 ${
                    allVisibleChecked
                      ? "text-primary"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                  title={allVisibleChecked ? "Odznacz wszystkie" : "Zaznacz wszystkie widoczne"}
                >
                  <CheckSquare className="w-3.5 h-3.5" />
                </button>
                <span className="text-[10px] text-muted-foreground shrink-0">
                  {filtered.length} doc{filtered.length !== 1 ? "s" : ""}
                </span>
              </div>

              {/* Chunk status toggle */}
              {!lockedChunkFilter && <div className="flex shrink-0 border-b border-border">
                <button
                  onClick={(e) => { e.stopPropagation(); setChunkFilter("pending"); setCheckedDocs(new Set()); }}
                  className={`flex-1 py-2 text-[11px] font-medium transition-colors border-b-2 -mb-px ${
                    chunkFilter === "pending"
                      ? "border-primary text-foreground"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  }`}
                >
                  Dokumenty do chunków
                  <span className={`ml-1.5 text-[10px] ${chunkFilter === "pending" ? "text-muted-foreground" : "text-muted-foreground/50"}`}>
                    {pendingCount}
                  </span>
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); setChunkFilter("ready"); setCheckedDocs(new Set()); }}
                  className={`flex-1 py-2 text-[11px] font-medium transition-colors border-b-2 -mb-px ${
                    chunkFilter === "ready"
                      ? "border-primary text-foreground"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  }`}
                >
                  Gotowe chunki
                  <span className={`ml-1.5 text-[10px] ${chunkFilter === "ready" ? "text-muted-foreground" : "text-muted-foreground/50"}`}>
                    {readyCount}
                  </span>
                </button>
              </div>}

              {/* Folder chips */}
              <div className="flex items-center gap-1.5 px-3 py-2 border-b border-border shrink-0 flex-wrap">
                <FolderChip label="Wszystkie" count={baseForCounts.length} active={activeFolder === "all"} onClick={() => setActiveFolder("all")} />
                {folders.map((f) => (
                  <FolderChip
                    key={f.id}
                    label={f.name}
                    count={baseForCounts.filter((d) => d.folder_id === f.id).length}
                    active={activeFolder === f.id}
                    onClick={() => setActiveFolder(f.id)}
                  />
                ))}
                {unassignedCount > 0 && (
                  <FolderChip label="Bez folderu" count={unassignedCount} active={activeFolder === "unassigned"} muted onClick={() => setActiveFolder("unassigned")} />
                )}
                {creatingFolder ? (
                  <span className="flex items-center gap-1">
                    <input
                      ref={newFolderRef}
                      value={newFolderName}
                      onChange={(e) => setNewFolderName(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") { e.stopPropagation(); commitCreateFolder(); }
                        if (e.key === "Escape") { e.stopPropagation(); setCreatingFolder(false); setNewFolderName(""); }
                      }}
                      placeholder="Nazwa…"
                      className="text-[11px] bg-muted border border-primary/50 rounded px-1.5 py-0.5 outline-none text-foreground w-24"
                    />
                    <button onClick={(e) => { e.stopPropagation(); commitCreateFolder(); }} className="text-primary hover:text-primary/80"><Check className="w-3 h-3" /></button>
                    <button onClick={(e) => { e.stopPropagation(); setCreatingFolder(false); setNewFolderName(""); }} className="text-muted-foreground hover:text-foreground"><X className="w-3 h-3" /></button>
                  </span>
                ) : (
                  <button
                    onClick={(e) => { e.stopPropagation(); setCreatingFolder(true); }}
                    className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] text-muted-foreground border border-dashed border-border hover:border-primary/50 hover:text-primary transition-colors"
                  >
                    <FolderPlus className="w-3 h-3" />
                    Nowy
                  </button>
                )}
              </div>

              {/* Document grid */}
              <div
                className="p-3 grid gap-2 overflow-y-auto"
                style={{ gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))" }}
              >
                {filtered.length === 0 && (
                  <p className="col-span-full text-xs text-muted-foreground text-center py-4">
                    {search ? `Brak dokumentów pasujących do „${search}"` : "Brak dokumentów w tej grupie"}
                  </p>
                )}
                {filtered.map((doc) => (
                  <DocTile
                    key={doc.id}
                    doc={doc}
                    chunkCount={chunkCounts[doc.id] ?? null}
                    hasEmbeddings={embeddedDocIds.has(doc.id)}
                    isActive={doc.id === selectedDocId}
                    isChecked={checkedDocs.has(doc.id)}
                    folders={folders}
                    onSelect={() => { onSelect(doc.id); close(); }}
                    onDelete={() => onDelete(doc)}
                    onAssignFolder={(folderId) => onAssignFolder(doc.id, folderId)}
                    onToggleCheck={() => toggleCheck(doc.id)}
                  />
                ))}
              </div>

              {/* Bulk assign footer */}
              {checkedDocs.size > 0 && (
                <div className="flex items-center gap-2 px-3 py-2 border-t border-border bg-muted/50 shrink-0">
                  <span className="text-[11px] text-foreground font-medium">
                    {checkedDocs.size} {checkedDocs.size === 1 ? "zaznaczony" : "zaznaczone"}
                  </span>

                  <div className="relative ml-auto">
                    <button
                      onClick={(e) => { e.stopPropagation(); setBulkFolderMenuOpen((v) => !v); }}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-primary text-primary-foreground text-[11px] font-medium hover:bg-primary/90 transition-colors"
                    >
                      <Folder className="w-3 h-3" />
                      Przypisz do folderu
                      <ChevronDown className="w-3 h-3" />
                    </button>

                    {bulkFolderMenuOpen && (
                      <div
                        className="absolute bottom-full right-0 mb-1 z-[60] bg-card border border-border rounded-md shadow-xl py-1 min-w-[160px]"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <div className="px-3 py-1.5 text-[10px] text-muted-foreground font-medium uppercase tracking-wide border-b border-border">
                          Wybierz folder
                        </div>
                        <button
                          className="w-full text-left px-3 py-1.5 text-[11px] text-muted-foreground hover:bg-muted transition-colors"
                          onClick={() => bulkAssign(null)}
                        >
                          — Bez folderu
                        </button>
                        {folders.map((f) => (
                          <button
                            key={f.id}
                            className="w-full text-left px-3 py-1.5 text-[11px] text-foreground hover:bg-muted transition-colors flex items-center gap-2"
                            onClick={() => bulkAssign(f.id)}
                          >
                            <Folder className="w-3 h-3 text-muted-foreground shrink-0" />
                            {f.name}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  <button
                    onClick={(e) => { e.stopPropagation(); setCheckedDocs(new Set()); setBulkFolderMenuOpen(false); }}
                    className="p-1 text-muted-foreground hover:text-foreground transition-colors"
                    title="Odznacz wszystkie"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}
            </div>
          </>,
          document.body
        )}
    </div>
  );
}

/* ── Folder chip ── */
function FolderChip({ label, count, active, muted, onClick }: {
  label: string; count: number; active: boolean; muted?: boolean; onClick: () => void;
}) {
  return (
    <button
      onClick={(e) => { e.stopPropagation(); onClick(); }}
      className={[
        "flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] border transition-colors whitespace-nowrap",
        active
          ? "bg-primary/15 border-primary/60 text-primary"
          : muted
          ? "border-border text-muted-foreground/60 hover:border-border hover:text-muted-foreground"
          : "border-border text-muted-foreground hover:border-primary/40 hover:text-foreground",
      ].join(" ")}
    >
      <Folder className="w-2.5 h-2.5" />
      {label}
      <span className={active ? "text-primary/70" : "text-muted-foreground/50"}>{count}</span>
    </button>
  );
}

/* ── Doc tile ── */
interface DocTileProps {
  doc: DocumentMeta;
  chunkCount: number | null;
  hasEmbeddings: boolean;
  isActive: boolean;
  isChecked: boolean;
  folders: FolderType[];
  onSelect: () => void;
  onDelete: () => void;
  onAssignFolder: (folderId: string | null) => void;
  onToggleCheck: () => void;
}

function DocTile({ doc, chunkCount, hasEmbeddings, isActive, isChecked, folders, onSelect, onDelete, onAssignFolder, onToggleCheck }: DocTileProps) {
  const [showFolderMenu, setShowFolderMenu] = useState(false);
  const [menuPos, setMenuPos] = useState({ top: 0, right: 0 });
  const folderBtnRef = useRef<HTMLButtonElement>(null);

  function openFolderMenu() {
    if (folderBtnRef.current) {
      const rect = folderBtnRef.current.getBoundingClientRect();
      setMenuPos({ top: rect.bottom + 4, right: window.innerWidth - rect.right });
    }
    setShowFolderMenu((v) => !v);
  }

  useEffect(() => {
    if (!showFolderMenu) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") { e.stopPropagation(); setShowFolderMenu(false); }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [showFolderMenu]);

  return (
    <div
      onClick={onSelect}
      className={`group relative cursor-pointer rounded-md border px-2.5 py-2 transition-colors ${
        isChecked
          ? "border-primary/60 bg-primary/10 ring-1 ring-primary/30"
          : isActive
          ? "border-primary bg-primary/10"
          : "border-border bg-muted hover:border-primary/40"
      }`}
    >
      {/* Checkbox — top-left, visible on hover or when checked */}
      <button
        onClick={(e) => { e.stopPropagation(); onToggleCheck(); }}
        className={`absolute top-1.5 left-1.5 w-3.5 h-3.5 rounded border flex items-center justify-center transition-all ${
          isChecked
            ? "bg-primary border-primary text-primary-foreground opacity-100"
            : "border-border bg-transparent opacity-0 group-hover:opacity-100"
        }`}
        title="Zaznacz"
      >
        {isChecked && <Check className="w-2.5 h-2.5" />}
      </button>

      <p className={`text-[11px] font-medium truncate pr-4 ${isChecked || isActive ? "pl-4" : "group-hover:pl-4"} transition-all ${
        isActive && !isChecked ? "text-primary" : isChecked ? "text-primary" : "text-foreground"
      }`}>
        {doc.name}
      </p>
      <p className="text-[10px] text-muted-foreground mt-0.5">
        {chunkCount !== null ? `${chunkCount} ch` : "—"}
        {hasEmbeddings && <span className="text-success/70 ml-1">· emb</span>}
      </p>
      {doc.folder_id && (
        <p className="text-[9px] text-primary/50 mt-0.5 truncate">
          {folders.find((f) => f.id === doc.folder_id)?.name ?? ""}
        </p>
      )}

      {/* Hover actions */}
      <div
        className="absolute top-1 right-1.5 hidden group-hover:flex items-center gap-1"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="relative">
          <button
            ref={folderBtnRef}
            onClick={openFolderMenu}
            className="text-[10px] text-muted-foreground hover:text-primary transition-colors"
            title="Przypisz folder"
          >
            <Folder className="w-3 h-3" />
          </button>
          {showFolderMenu && createPortal(
            <>
              <div className="fixed inset-0 z-[59]" onClick={() => setShowFolderMenu(false)} />
              <div
                className="fixed z-[60] bg-card border border-border rounded-md shadow-xl py-1 min-w-[140px]"
                style={{ top: menuPos.top, right: menuPos.right }}
                onClick={(e) => e.stopPropagation()}
              >
                <button className="w-full text-left px-3 py-1 text-[11px] text-muted-foreground hover:bg-muted transition-colors" onClick={() => { onAssignFolder(null); setShowFolderMenu(false); }}>
                  — Bez folderu
                </button>
                {folders.map((f) => (
                  <button
                    key={f.id}
                    className={`w-full text-left px-3 py-1 text-[11px] transition-colors hover:bg-muted ${doc.folder_id === f.id ? "text-primary" : "text-foreground"}`}
                    onClick={() => { onAssignFolder(f.id); setShowFolderMenu(false); }}
                  >
                    {f.name}
                  </button>
                ))}
              </div>
            </>,
            document.body
          )}
        </div>
        <button onClick={onDelete} className="text-[10px] text-muted-foreground hover:text-error transition-colors" title="Usuń dokument">✕</button>
      </div>
    </div>
  );
}
