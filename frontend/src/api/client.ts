const BASE = "http://localhost:8000/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  // Documents
  uploadDocument: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<import("../types").DocumentMeta>("/documents/upload", {
      method: "POST",
      body: form,
    });
  },
  listDocuments: () => request<import("../types").DocumentMeta[]>("/documents/"),
  getDocument: (id: string) => request<import("../types").DocumentDetail>(`/documents/${id}`),
  deleteDocument: (id: string) => request<{ deleted: string }>(`/documents/${id}`, { method: "DELETE" }),

  // Chunks
  generateChunks: (body: import("../types").ChunkRequest) =>
    request<import("../types").ChunkResponse>("/chunks/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  getChunks: (documentId: string) =>
    request<import("../types").ChunkResponse>(`/chunks/${documentId}`),

  // Embeddings
  generateEmbeddings: (documentId: string) =>
    request<{ embedded_count: number; elapsed_ms: number }>("/embeddings/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ document_id: documentId }),
    }),
  getVisualization: () =>
    request<import("../types").EmbeddingPoint[]>("/embeddings/visualize"),
  getSimilarity: (a: string, b: string) =>
    request<{ cosine_similarity: number }>(`/embeddings/similarity?chunk_id_a=${a}&chunk_id_b=${b}`),

  // Chat
  getRetrieval: () => request<import("../types").RetrievedChunk[]>("/chat/retrieval"),
  getPrompt: () => request<import("../types").PromptData>("/chat/prompt"),
  updateSystemPrompt: (system_prompt: string) =>
    request<{ updated: boolean }>("/chat/system-prompt", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ system_prompt }),
    }),

  // Metrics
  getSessionMetrics: () => request<import("../types").SessionMetrics>("/metrics/session"),
  resetAll: () => request<{ reset: boolean }>("/data/reset", { method: "DELETE" }),
};

export function streamChat(
  query: string,
  topK: number,
  onToken: (token: string) => void,
  onDone: () => void,
  systemPrompt?: string,
): () => void {
  const ctrl = new AbortController();
  fetch(`${BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, top_k: topK, system_prompt: systemPrompt }),
    signal: ctrl.signal,
  }).then(async (res) => {
    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const lines = decoder.decode(value).split("\n");
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const token = line.slice(6);
          if (token === "[DONE]") {
            onDone();
            return;
          }
          onToken(token);
        }
      }
    }
    onDone();
  }).catch((e) => {
    if (e.name !== "AbortError") onDone();
  });
  return () => ctrl.abort();
}
