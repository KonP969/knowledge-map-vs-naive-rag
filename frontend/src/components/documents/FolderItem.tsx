import { useState, useRef, useEffect } from "react";
import { Folder, FolderOpen, Pencil, Trash2, Check, X } from "lucide-react";
import { useDroppable } from "@dnd-kit/core";

interface FolderItemProps {
  id: string | null; // null = "Bez folderu"
  name: string;
  isActive: boolean;
  isEmpty: boolean;
  onSelect: () => void;
  onRename?: (name: string) => void;
  onDelete?: () => void;
}

export default function FolderItem({
  id,
  name,
  isActive,
  isEmpty,
  onSelect,
  onRename,
  onDelete,
}: FolderItemProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(name);
  const inputRef = useRef<HTMLInputElement>(null);

  const { setNodeRef, isOver } = useDroppable({ id: id ?? "__unassigned__" });

  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  function commitRename() {
    const trimmed = draft.trim();
    if (trimmed && trimmed !== name) onRename?.(trimmed);
    setEditing(false);
  }

  function cancelRename() {
    setDraft(name);
    setEditing(false);
  }

  const isVirtual = id === null;

  const baseClass = [
    "group flex items-center gap-2 px-2 py-1.5 rounded-md cursor-pointer text-sm transition-colors",
    isActive ? "bg-indigo-50 text-indigo-700 font-medium" : "text-gray-700 hover:bg-gray-100",
    isOver ? "ring-2 ring-indigo-400 bg-indigo-50" : "",
  ].join(" ");

  return (
    <div ref={setNodeRef} className={baseClass} onClick={() => { if (!editing) onSelect(); }}>
      {isActive
        ? <FolderOpen size={15} className="shrink-0 text-indigo-500" />
        : <Folder size={15} className="shrink-0 text-gray-400" />}

      {editing ? (
        <input
          ref={inputRef}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") commitRename();
            if (e.key === "Escape") cancelRename();
          }}
          onBlur={commitRename}
          onClick={(e) => e.stopPropagation()}
          className="flex-1 min-w-0 text-sm bg-white border border-indigo-300 rounded px-1 outline-none"
        />
      ) : (
        <span className="flex-1 min-w-0 truncate">{name}</span>
      )}

      {!isVirtual && !editing && (
        <span className="hidden group-hover:flex items-center gap-1 shrink-0" onClick={(e) => e.stopPropagation()}>
          <button
            className="p-0.5 rounded hover:bg-gray-200 text-gray-400 hover:text-gray-600"
            onClick={() => { setDraft(name); setEditing(true); }}
            title="Zmień nazwę"
          >
            <Pencil size={12} />
          </button>
          <button
            className={[
              "p-0.5 rounded text-gray-400",
              isEmpty ? "hover:bg-red-100 hover:text-red-500 cursor-pointer" : "opacity-30 cursor-not-allowed",
            ].join(" ")}
            onClick={() => { if (isEmpty) onDelete?.(); }}
            title={isEmpty ? "Usuń folder" : "Folder nie jest pusty"}
          >
            <Trash2 size={12} />
          </button>
        </span>
      )}
    </div>
  );
}
