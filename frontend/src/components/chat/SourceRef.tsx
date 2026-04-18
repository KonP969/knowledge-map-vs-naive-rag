import { useRef } from "react";
import type { RetrievedChunk } from "../../types";

interface SourceRefProps {
  num: number;
  source: RetrievedChunk | undefined;
  onActivate: (rect: DOMRect, num: number, source: RetrievedChunk) => void;
  isActive: boolean;
}

export function SourceRef({ num, source, onActivate, isActive }: SourceRefProps) {
  const spanRef = useRef<HTMLSpanElement>(null);

  if (!source) {
    return (
      <span className="inline-flex items-center justify-center bg-primary/20 text-primary text-[10px] font-bold w-4 h-4 rounded align-super relative -top-0.5 mx-0.5">
        {num}
      </span>
    );
  }

  return (
    <span
      ref={spanRef}
      onClick={() => {
        if (spanRef.current) {
          onActivate(spanRef.current.getBoundingClientRect(), num, source);
        }
      }}
      className={`inline-flex items-center justify-center text-[10px] font-bold w-4 h-4 rounded align-super relative -top-0.5 mx-0.5 cursor-pointer transition-colors select-none ${
        isActive
          ? "bg-primary/50 text-primary border border-primary/70"
          : "bg-primary/20 text-primary border border-primary/30 hover:bg-primary/35"
      }`}
    >
      {num}
    </span>
  );
}
