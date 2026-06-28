const BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  // Metrics
  getSessionMetrics: () => request<import("../types").SessionMetrics>("/metrics/session"),
  resetAll: () => request<{ reset: boolean }>("/data/reset", { method: "DELETE" }),

  // Wiki
  listWikiSources: () => request<import("../types").WikiSource[]>("/wiki/sources"),
  listWikiEntities: () => request<import("../types").WikiEntity[]>("/wiki/entities"),
  listWikiConcepts: () => request<import("../types").WikiConcept[]>("/wiki/concepts"),

  // Ingest
  ingestSource: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<import("../types").IngestResult>("/ingest/source", {
      method: "POST",
      body: form,
    });
  },

  // Retrieval
  queryWiki: (question: string) =>
    request<import("../types").QueryTrace>("/retrieval/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    }),

  // Graph
  listWikiEdges: () => request<import("../types").WikiEdge[]>("/wiki/edges"),
  getWikiNodeDetail: (id: string) =>
    request<import("../types").NodeDetail>(`/wiki/node-detail?id=${encodeURIComponent(id)}`),
  getClaimsByIds: (ids: string[]) =>
    request<import("../types").NodeDetailClaim[]>(
      `/wiki/claims-by-id?ids=${encodeURIComponent(ids.join(","))}`
    ),

  // Lint
  runLint: (includeSemantic = false) =>
    request<import("../types").LintReport>("/lint/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ include_semantic: includeSemantic }),
    }),
  listLintReports: () =>
    request<import("../types").LintReportSummary[]>("/lint/reports"),
  getLintReport: (id: string) =>
    request<import("../types").LintReport>(`/lint/report/${encodeURIComponent(id)}`),
  applyLintFix: (body: import("../types").LintFixRequest) =>
    request<{ id: string; status: import("../types").IssueStatus }>("/lint/fix", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),

  // Source raw text
  getSourceRaw: (slug: string) =>
    request<{ slug: string; title: string; raw_text: string }>(
      `/wiki/source-raw?slug=${encodeURIComponent(slug)}`
    ),

  // Source folders (view-only organization)
  setSourcesFolder: (slugs: string[], folder: string | null) =>
    request<{ updated: number; folder: string | null }>("/wiki/sources/folder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ slugs, folder }),
    }),

  // Source deletion
  deleteSource: (slug: string) =>
    request<{ slug: string; source_id: string; deleted: boolean }>(
      `/wiki/source/${encodeURIComponent(slug)}`,
      { method: "DELETE" }
    ),

  // Crawl (SSE streaming)
  crawlAndIngestStream: async (
    url: string,
    maxArticles: number,
    onEvent: (event: import("../types").CrawlSSEEvent) => void,
    folder?: string | null,
  ): Promise<void> => {
    const res = await fetch(`${BASE}/crawl/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, max_articles: maxArticles, folder: folder || null }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split("\n");
      buf = lines.pop() ?? "";
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            onEvent(JSON.parse(line.slice(6)));
          } catch {
            // ignore malformed SSE lines
          }
        }
      }
    }
  },
};
