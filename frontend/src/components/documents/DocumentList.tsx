import { Trash2, FileText } from "lucide-react";
import type { DocumentMeta } from "../../types";

interface DocumentListProps {
  documents: DocumentMeta[];
  selectedId: string | null;
  onSelect: (doc: DocumentMeta) => void;
  onDelete: (id: string) => void;
}

function formatBytes(b: number) {
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / 1024 / 1024).toFixed(1)} MB`;
}

export function DocumentList({ documents, selectedId, onSelect, onDelete }: DocumentListProps) {
  if (documents.length === 0) {
    return <p className="text-sm text-muted-foreground py-4">No documents uploaded yet.</p>;
  }

  return (
    <div className="space-y-2">
      {documents.map((doc) => (
        <div
          key={doc.id}
          className={`border rounded-lg p-3 flex items-start gap-3 cursor-pointer transition-colors ${
            selectedId === doc.id
              ? "border-primary bg-primary/10"
              : "border-border bg-card hover:border-primary/40 hover:bg-muted/50"
          }`}
          onClick={() => onSelect(doc)}
        >
          <FileText className="w-4 h-4 mt-0.5 text-muted-foreground shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate text-foreground">{doc.name}</p>
            <p className="text-xs text-muted-foreground">
              {formatBytes(doc.size_bytes)} · {doc.char_count.toLocaleString()} chars
              {doc.page_count != null && ` · ${doc.page_count} pages`}
            </p>
          </div>
          <button
            onClick={(e) => { e.stopPropagation(); onDelete(doc.id); }}
            className="p-1 rounded hover:bg-error/20 hover:text-error text-muted-foreground transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      ))}
    </div>
  );
}
