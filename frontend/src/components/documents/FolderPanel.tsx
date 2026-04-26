import { useState, useRef, useEffect } from "react";
import { Plus, Check, X } from "lucide-react";
import FolderItem from "./FolderItem";
import type { Folder, DocumentMeta } from "../../types";

interface FolderPanelProps {
  folders: Folder[];
  documents: DocumentMeta[];
  activeFolderId: string | null;
  onSelect: (id: string | null) => void;
  onCreate: (name: string) => void;
  onRename: (id: string, name: string) => void;
  onDelete: (id: string) => void;
}

export default function FolderPanel({
  folders,
  documents,
  activeFolderId,
  onSelect,
  onCreate,
  onRename,
  onDelete,
}: FolderPanelProps) {
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (creating) inputRef.current?.focus();
  }, [creating]);

  function commitCreate() {
    const name = newName.trim();
    if (name) onCreate(name);
    setCreating(false);
    setNewName("");
  }

  function cancelCreate() {
    setCreating(false);
    setNewName("");
  }

  function isFolderEmpty(folderId: string) {
    return !documents.some((d) => d.folder_id === folderId);
  }

  const unassignedCount = documents.filter((d) => !d.folder_id).length;

  return (
    <div className="flex flex-col h-full border-r border-gray-200 bg-gray-50 w-52 shrink-0">
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-200">
        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Projekty</span>
        <button
          className="p-0.5 rounded hover:bg-gray-200 text-gray-400 hover:text-gray-600 transition-colors"
          onClick={() => setCreating(true)}
          title="Nowy folder"
        >
          <Plus size={15} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-1.5 space-y-0.5">
        <FolderItem
          id={null}
          name={`Bez folderu${unassignedCount ? ` (${unassignedCount})` : ""}`}
          isActive={activeFolderId === null}
          isEmpty={true}
          onSelect={() => onSelect(null)}
        />

        {folders.map((f) => (
          <FolderItem
            key={f.id}
            id={f.id}
            name={f.name}
            isActive={activeFolderId === f.id}
            isEmpty={isFolderEmpty(f.id)}
            onSelect={() => onSelect(f.id)}
            onRename={(name) => onRename(f.id, name)}
            onDelete={() => onDelete(f.id)}
          />
        ))}

        {creating && (
          <div className="flex items-center gap-1 px-2 py-1">
            <input
              ref={inputRef}
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") commitCreate();
                if (e.key === "Escape") cancelCreate();
              }}
              placeholder="Nazwa folderu"
              className="flex-1 min-w-0 text-sm border border-indigo-300 rounded px-1.5 py-0.5 outline-none"
            />
            <button onClick={commitCreate} className="p-0.5 text-indigo-600 hover:text-indigo-800">
              <Check size={14} />
            </button>
            <button onClick={cancelCreate} className="p-0.5 text-gray-400 hover:text-gray-600">
              <X size={14} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
