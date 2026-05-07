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
