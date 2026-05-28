const BASE = "http://127.0.0.1:8000/api";

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

  // Source deletion
  deleteSource: (slug: string) =>
    request<{ slug: string; source_id: string; deleted: boolean }>(
      `/wiki/source/${encodeURIComponent(slug)}`,
      { method: "DELETE" }
    ),

  // Crawl
  crawlAndIngest: (url: string, maxArticles: number = 5) =>
    request<{
      articles_found: number;
      ingested: number;
      failed: number;
      results: Array<{ url: string; title: string; status: string; error?: string; slug?: string }>;
      fatal_error?: string | null;
    }>("/crawl/ingest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, max_articles: maxArticles }),
    }),
};
