import { useEffect, type ReactNode } from "react";
import { createPortal } from "react-dom";
import type { RetrievedChunk, HighlightRange } from "../../types";

interface SourcePopoverProps {
  source: RetrievedChunk;
  anchorRect: DOMRect;
  onClose: () => void;
}

const POPOVER_WIDTH = 320;
const POPOVER_HEIGHT_ESTIMATE = 280;
const MARGIN = 8;

function renderWithHighlights(content: string, ranges: HighlightRange[]): ReactNode {
  if (!ranges || ranges.length === 0) return <span>{content}</span>;
  const parts: ReactNode[] = [];
  let cursor = 0;
  for (const range of ranges) {
    if (cursor < range.start) {
      parts.push(<span key={`t-${cursor}`}>{content.slice(cursor, range.start)}</span>);
    }
    parts.push(
      <mark key={`h-${range.start}`} className="bg-primary/25 text-foreground font-medium rounded px-0.5">
        {content.slice(range.start, range.end)}
      </mark>
    );
    cursor = range.end;
  }
  if (cursor < content.length) {
    parts.push(<span key="t-end">{content.slice(cursor)}</span>);
  }
  return <>{parts}</>;
}

export function SourcePopover({ source, anchorRect, onClose }: SourcePopoverProps) {
  const spaceAbove = anchorRect.top;
  const openAbove = spaceAbove > POPOVER_HEIGHT_ESTIMATE + MARGIN;

  const top = openAbove
    ? anchorRect.top - POPOVER_HEIGHT_ESTIMATE - MARGIN
    : anchorRect.bottom + MARGIN;

  const left = Math.min(
    Math.max(anchorRect.left, MARGIN),
    window.innerWidth - POPOVER_WIDTH - MARGIN
  );

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return createPortal(
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-40" onClick={onClose} />
      {/* Popover */}
      <div
        className="fixed z-50 bg-card border border-border rounded-lg shadow-xl overflow-hidden"
        style={{ top, left, width: POPOVER_WIDTH, maxHeight: POPOVER_HEIGHT_ESTIMATE }}
      >
        {/* Header */}
        <div className="flex items-center justify-between gap-2 px-3 py-2 border-b border-border bg-muted/50">
          <span className="text-xs font-semibold text-primary truncate">
            {source.document_name || source.document_id.slice(0, 12)}
          </span>
          <span className="text-[10px] text-muted-foreground shrink-0">
            #{source.rank} · {source.score.toFixed(3)}
          </span>
        </div>
        {/* Content */}
        <div className="px-3 py-2 overflow-y-auto text-xs leading-relaxed text-foreground" style={{ maxHeight: POPOVER_HEIGHT_ESTIMATE - 40 }}>
          {renderWithHighlights(source.content, source.highlighted_ranges ?? [])}
        </div>
      </div>
    </>,
    document.body
  );
}
