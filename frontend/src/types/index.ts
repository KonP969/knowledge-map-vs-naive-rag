export interface QueryMetrics {
  query_id: string;
  timestamp: string;
  query: string;
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
  | "metrics"
  | "tutorial"
  | "sources"
  | "ingest"
  | "chat_trace"
  | "knowledge_map"
  | "lint";

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
  folder?: string | null;
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

// ── Graph / Node Detail types ──────────────────────────────────────────────────

export interface WikiEdge {
  id: string;
  from: string;
  to: string;
  relation: string;
  source_id: string;
  confidence: number;
}

export interface ClaimSpan {
  start: number;
  end: number;
  text: string;
}

export interface NodeDetailClaim {
  id: string;
  text: string;
  confidence: number;
  polarity: "asserts" | "denies";
  source_id: string;
  span?: ClaimSpan;
}

export interface NodeDetailEdge {
  id: string;
  from: string;
  to: string;
  relation: string;
  source_id: string;
}

export interface NodeDetail {
  id: string;
  node_type: "entity" | "concept" | "source";
  entity_type?: string;
  slug?: string;
  title?: string;
  description?: string;
  aliases?: string[];
  tags?: string[];
  questions?: string[];
  claims: NodeDetailClaim[];
  edges: NodeDetailEdge[];
}

// ── Lint types ─────────────────────────────────────────────────────────────

export type IssueSeverity = "error" | "warning" | "info";

export type IssueType =
  | "provenance_missing"
  | "dangling_source_ref"
  | "dangling_node_ref"
  | "corrupted_jsonl"
  | "orphan_entity"
  | "orphan_concept"
  | "empty_questions"
  | "empty_description"
  | "unmarked_contradiction"
  | "entity_alias_collision"
  | "missing_concept"
  | "stale_summary";

export type IssueStatus = "open" | "fixed" | "rejected" | "wontfix";

export interface LintIssue {
  id: string;
  type: IssueType;
  severity: IssueSeverity;
  location: string;
  description: string;
  suggested_fix: string | null;
  auto_fixable: boolean;
  payload: Record<string, unknown>;
  status: IssueStatus;
}

export interface LintReport {
  id: string;
  created_at: string;
  issues: LintIssue[];
  counts_by_severity: Record<string, number>;
  counts_by_type: Record<string, number>;
}

export interface LintReportSummary {
  id: string;
  created_at: string;
  counts_by_severity: Record<string, number>;
  total: number;
}

export interface LintFixRequest {
  report_id: string;
  issue_id: string;
  action: "apply" | "reject" | "wontfix";
  edit_payload?: { description?: string };
}

// ── Crawl SSE types ────────────────────────────────────────────────────────

export type CrawlSSEEvent =
  | { event: "articles_found"; count: number; discovered?: number }
  | { event: "article_start"; index: number; title: string; url: string }
  | { event: "article_done"; index: number; title: string; status: "ok" | "error"; slug?: string; error?: string }
  | { event: "done"; ingested: number; failed: number }
  | { event: "fatal_error"; error: string };
