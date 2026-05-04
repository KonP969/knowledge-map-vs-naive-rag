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

export type Panel =
  | "documents"
  | "chunks"
  | "embeddings"
  | "chat"
  | "metrics"
  | "tutorial"
  | "sources"
  | "ingest"
  | "chat_trace"
  | "knowledge_map";

// ── Wiki / Ingest types ────────────────────────────────────────────────────

export type WikiSourceStatus = "ok" | "partial" | "error";

export interface WikiSource {
  slug: string;
  id: string;
  title: string;
  type: string;
  ingested_at: string;
  tags: string[];
  questions: string[];
  summary: string;
  key_takeaways: string[];
  source_url?: string | null;
}

export interface WikiEntity {
  slug: string;
  id: string;
  type: "Person" | "Org" | "Product" | "Place" | "Event";
  aliases: string[];
  description: string;
  mentions_count: number;
  tags: string[];
  questions: string[];
}

export interface WikiConcept {
  slug: string;
  id: string;
  parent_concept?: string | null;
  definition: string;
  examples: string[];
  related: string[];
  tags: string[];
  questions: string[];
}

export interface ConflictReport {
  new_claim_id: string;
  existing_claim_id: string;
  description: string;
}

export interface IngestResult {
  source_id: string;
  slug: string;
  status: WikiSourceStatus;
  entities_created: number;
  entities_merged: number;
  concepts_created: number;
  concepts_merged: number;
  claims_added: number;
  edges_added: number;
  conflicts: ConflictReport[];
  duration_ms: number;
  llm_calls: number;
  error?: string | null;
}

// ── Retrieval types ────────────────────────────────────────────────────────

export interface TimePeriod {
  start?: string | null;
  end?: string | null;
}

export interface ParsedIntent {
  original_question: string;
  entity_mentions: string[];
  concept_mentions: string[];
  time_period?: TimePeriod | null;
  intent_type: "fact_lookup" | "comparison" | "synthesis" | "definition" | "how_to" | "temporal_trend";
  expected_answer_form: "short" | "list" | "table" | "analysis" | "citation";
}

export interface RetrievalCandidate {
  artifact_id: string;
  artifact_type: "source" | "entity" | "concept";
  slug: string;
  title: string;
  score: number;
  score_breakdown: Record<string, number>;
  questions: string[];
  tags: string[];
  description_preview: string;
}

export interface SelectedArtifact {
  artifact_id: string;
  relevance_score: number;
  reasoning: string;
}

export interface RetrievalSelection {
  selected: SelectedArtifact[];
  confidence: number;
  reasoning: string;
}

export interface AnswerSource {
  source_id: string;
  claim_ids: string[];
  relevance: string;
}

export interface RetrievalAnswer {
  final_answer: string;
  sources: AnswerSource[];
  confidence: number;
  reasoning_steps: string[];
  related_questions: string[];
}

export interface RetrievalStageTrace {
  stage: number;
  name: string;
  duration_ms: number;
  llm_called: boolean;
  input_summary: string;
  output_summary: string;
}

export interface QueryTrace {
  query_id: string;
  question: string;
  intent: ParsedIntent;
  candidates_count: number;
  selected_count: number;
  context_chars: number;
  answer: RetrievalAnswer;
  stages: RetrievalStageTrace[];
  total_duration_ms: number;
  total_llm_calls: number;
}
