import { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import type { DocumentMeta, Folder } from "../../types";

interface FolderAssignModalProps {
  docs: DocumentMeta[];
  folders: Folder[];
  onAssign: (folderId: string | null) => Promise<void>;
  onSkip: () => void;
  onCreateFolder: (name: string) => Promise<Folder>;
}

export function FolderAssignModal({
  docs,
  folders,
  onAssign,
  onSkip,
  onCreateFolder,
}: FolderAssignModalProps) {
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(
    folders[0]?.id ?? null
  );
  const [creatingFolder, setCreatingFolder] = useState(false);
  const [newFolderName, setNewFolderName] = useState("");
  const [loading, setLoading] = useState(false);
  const newFolderRef = useRef<HTMLInputElement>(null);
  const skipRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    skipRef.current?.focus();
  }, []);

  useEffect(() => {
    if (creatingFolder) newFolderRef.current?.focus();
  }, [creatingFolder]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !loading) onSkip();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onSkip, loading]);

  async function handleConfirm() {
    setLoading(true);
    try {
      await onAssign(selectedFolderId);
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateFolder() {
    const name = newFolderName.trim();
    if (!name) return;
    setLoading(true);
    try {
      const folder = await onCreateFolder(name);
      setSelectedFolderId(folder.id);
      setCreatingFolder(false);
      setNewFolderName("");
    } finally {
      setLoading(false);
    }
  }

  const title =
    docs.length === 1
      ? `Przypisz „${docs[0].name}" do folderu?`
      : `Przypisz ${docs.length} dokumentów do folderu?`;

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={!loading ? onSkip : undefined}
    >
      <div
        role="dialog"
        aria-modal="true"
        className="bg-card border border-border rounded-lg p-5 w-80 shadow-2xl space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-sm font-semibold">{title}</h3>

        <div className="space-y-2">
          <select
            value={selectedFolderId ?? ""}
            onChange={(e) => setSelectedFolderId(e.target.value || null)}
            disabled={loading}
            className="w-full text-sm border border-border rounded-md px-3 py-1.5 bg-muted text-foreground outline-none focus:border-primary disabled:opacity-50"
          >
            <option value="">— Bez folderu</option>
            {folders.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}
              </option>
            ))}
          </select>

          {creatingFolder ? (
            <div className="flex gap-2">
              <input
                ref={newFolderRef}
                value={newFolderName}
                onChange={(e) => setNewFolderName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleCreateFolder();
                  if (e.key === "Escape") { setCreatingFolder(false); setNewFolderName(""); }
                }}
                placeholder="Nazwa folderu"
                disabled={loading}
                className="flex-1 text-sm border border-primary/50 rounded-md px-2.5 py-1 bg-muted text-foreground outline-none disabled:opacity-50"
              />
              <button
                onClick={handleCreateFolder}
                disabled={loading || !newFolderName.trim()}
                className="px-3 py-1 text-xs bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors"
              >
                Utwórz
              </button>
            </div>
          ) : (
            <button
              onClick={() => setCreatingFolder(true)}
              disabled={loading}
              className="text-xs text-primary hover:underline disabled:opacity-50"
            >
              + Nowy folder
            </button>
          )}
        </div>

        <div className="flex gap-2 justify-end">
          <button
            ref={skipRef}
            type="button"
            onClick={onSkip}
            disabled={loading}
            className="px-3 py-1.5 text-xs border border-border rounded-md hover:bg-muted transition-colors disabled:opacity-50"
          >
            Pomiń
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={loading}
            className="px-3 py-1.5 text-xs bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {loading ? "Przypisuję…" : "Potwierdź"}
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}
