from typing import List, Literal, Optional
from pydantic import BaseModel
from models.wiki_models import EntityType, Polarity, Span


class EntityMention(BaseModel):
    name: str
    type: EntityType
    aliases: List[str]
    description: str
    span: Span


class ConceptMention(BaseModel):
    name: str
    definition: str
    span: Span


class ClaimExtraction(BaseModel):
    text: str
    subject_name: str
    subject_type: Literal["entity", "concept"]
    span: Span
    confidence: float
    polarity: Polarity


class SourceClassification(BaseModel):
    title: str
    description: str
    tags: List[str]
    questions: List[str]
    key_takeaways: List[str]
    entity_mentions: List[EntityMention]
    concept_mentions: List[ConceptMention]
    claims: List[ClaimExtraction]


class ConflictReport(BaseModel):
    new_claim_id: str
    existing_claim_id: str
    description: str


class IngestResult(BaseModel):
    source_id: str
    slug: str
    status: Literal["ok", "partial", "error"]
    entities_created: int
    entities_merged: int
    concepts_created: int
    concepts_merged: int
    claims_added: int
    edges_added: int
    conflicts: List[ConflictReport]
    duration_ms: float
    llm_calls: int
    error: Optional[str] = None
