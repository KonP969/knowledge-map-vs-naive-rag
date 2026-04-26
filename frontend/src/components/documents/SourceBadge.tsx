import { Globe, FileText, File } from "lucide-react";

interface SourceBadgeProps {
  sourceType: "upload" | "crawl";
  fileName?: string;
}

function getExtension(name: string): string {
  const parts = name.split(".");
  return parts.length > 1 ? parts[parts.length - 1].toUpperCase() : "FILE";
}

export default function SourceBadge({ sourceType, fileName = "" }: SourceBadgeProps) {
  if (sourceType === "crawl") {
    return (
      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700">
        <Globe size={11} />
        Web
      </span>
    );
  }

  const ext = getExtension(fileName);
  const isPdf = ext === "PDF";

  return (
    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
      {isPdf ? <FileText size={11} /> : <File size={11} />}
      {ext}
    </span>
  );
}
