export interface DocumentMeta {
  id: string;
  name: string;
  size_bytes: number;
  page_count: number | null;
  upload_date: string;
  char_count: number;
  source_type: "upload" | "crawl";
  source_url?: string | null;
  folder_id?: string | null;
}

export interface Folder {
  id: string;
  name: string;
  created_at: string;
}

export interface DocumentDetail extends DocumentMeta {
  raw_text: string;
}

export interface Chunk {
  id: string;
  document_id: string;
  content: string;
  index: number;
  char_count: number;
  token_count: number;
  start_char: number;
  end_char: number;
}

export interface ChunkRequest {
  document_id: string;
  strategy: "fixed" | "recursive" | "semantic";
  chunk_size?: number;
  overlap?: number;
  separators?: string[];
}

export interface ChunkStats {
  count: number;
  avg_length: number;
  min_length: number;
  max_length: number;
  overlap_pct: number;
}

export interface ChunkResponse {
  chunks: Chunk[];
  stats: ChunkStats;
}

export interface EmbeddingPoint {
  chunk_id: string;
  document_id: string;
  document_name: string;
  x: number;
  y: number;
  content_preview: string;
}

export interface EmbeddingStatus {
  document_id: string;
  chunk_count: number;
}

export interface HighlightRange {
  start: number;
  end: number;
  text: string;
}

export interface RetrievedChunk {
  chunk_id: string;
  document_id: string;
  document_name: string;
  content: string;
  score: number;
  rank: number;
  highlighted_ranges?: HighlightRange[];
}

export interface PromptData {
  system_message: string;
  context_block: string;
  user_query: string;
  full_prompt: string;
  token_counts: {
    system: number;
    context: number;
    query: number;
    total: number;
  };
}

export interface QueryMetrics {
  query_id: string;
  timestamp: string;
  query: string;
  chunking_ms: number;
  embedding_ms: number;
  retrieval_ms: number;
  llm_ms: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
}

export interface SessionMetrics {
  total_queries: number;
  total_tokens: number;
  total_cost_usd: number;
  queries: QueryMetrics[];
}

export type Panel = "documents" | "chunks" | "embeddings" | "chat" | "metrics" | "tutorial";
