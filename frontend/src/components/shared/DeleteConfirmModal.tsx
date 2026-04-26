import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import type { DocumentMeta } from "../../types";

interface DeleteConfirmModalProps {
  doc: DocumentMeta;
  chunkCount: number | null;
  isLoading: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function DeleteConfirmModal({
  doc,
  chunkCount,
  isLoading,
  onConfirm,
  onCancel,
}: DeleteConfirmModalProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    cancelRef.current?.focus();
  }, []);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !isLoading) onCancel();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onCancel, isLoading]);

  const chunksText =
    chunkCount !== null && chunkCount > 0 ? `, ${chunkCount} chunków` : "";

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={!isLoading ? onCancel : undefined}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-modal-title"
        className="bg-card border border-border rounded-lg p-5 w-80 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 id="delete-modal-title" className="text-sm font-semibold mb-2">Usuń dokument</h3>
        <p className="text-xs text-muted-foreground mb-4 leading-relaxed">
          Czy na pewno chcesz usunąć{" "}
          <span className="text-foreground font-medium">„{doc.name}"</span>?
          Zostanie usunięty dokument{chunksText} i embeddingi.
        </p>
        <div className="flex gap-2 justify-end">
          <button
            ref={cancelRef}
            type="button"
            onClick={onCancel}
            disabled={isLoading}
            className="px-3 py-1.5 text-xs border border-border rounded-md hover:bg-muted transition-colors disabled:opacity-50"
          >
            Anuluj
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isLoading}
            className="px-3 py-1.5 text-xs bg-error text-white rounded-md hover:bg-error/90 transition-colors disabled:opacity-50"
          >
            {isLoading ? "Usuwam…" : "Usuń"}
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}
