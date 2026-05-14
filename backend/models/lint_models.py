from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


IssueSeverity = Literal["error", "warning", "info"]

IssueType = Literal[
    # Tier 1 (error)
    "provenance_missing",
    "dangling_source_ref",
    "dangling_node_ref",
    "corrupted_jsonl",
    # Tier 2 (warning)
    "orphan_entity",
    "orphan_concept",
    "empty_questions",
    "empty_description",
    # Tier 3 (info)
    "unmarked_contradiction",
    "entity_alias_collision",
    "missing_concept",
    "stale_summary",
]

IssueStatus = Literal["open", "fixed", "rejected", "wontfix"]


class LintIssue(BaseModel):
    id: str
    type: IssueType
    severity: IssueSeverity
    location: str
    description: str
    suggested_fix: Optional[str] = None
    auto_fixable: bool = False
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: IssueStatus = "open"


class LintReport(BaseModel):
    id: str
    created_at: datetime
    issues: List[LintIssue]
    counts_by_severity: Dict[str, int]
    counts_by_type: Dict[str, int]


# ── LLM response models for Tier 3 checks ────────────────────────────────────

class ContradictionJudgement(BaseModel):
    is_contradiction: bool
    explanation: str


class AliasMergeJudgement(BaseModel):
    should_merge: bool
    explanation: str
    suggested_canonical: str


class MissingConceptJudgement(BaseModel):
    has_missing_concept: bool
    concept_name: str
    explanation: str


class StaleSummaryJudgement(BaseModel):
    is_stale: bool
    proposed_summary: str
    explanation: str


class LlmQuestionsResult(BaseModel):
    questions: List[str]
