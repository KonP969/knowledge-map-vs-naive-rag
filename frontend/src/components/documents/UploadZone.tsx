import { useState, useRef } from "react";
import { Upload } from "lucide-react";
import { api } from "../../api/client";
import type { DocumentMeta } from "../../types";

interface UploadZoneProps {
  onUploaded: (doc: DocumentMeta) => void;
}

export function UploadZone({ onUploaded }: UploadZoneProps) {
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    setLoading(true);
    setError(null);
    try {
      const doc = await api.uploadDocument(file);
      onUploaded(doc);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        const f = e.dataTransfer.files[0];
        if (f) handleFile(f);
      }}
      className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
        dragging ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx,.txt"
        className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
      />
      <Upload className="w-8 h-8 mx-auto mb-2 text-muted-foreground" />
      {loading ? (
        <p className="text-sm text-muted-foreground">Uploading...</p>
      ) : (
        <>
          <p className="text-sm font-medium">Drop file here or click to upload</p>
          <p className="text-xs text-muted-foreground mt-1">PDF, DOCX, TXT</p>
        </>
      )}
      {error && <p className="text-xs text-red-500 mt-2">{error}</p>}
    </div>
  );
}
