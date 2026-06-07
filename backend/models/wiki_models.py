from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict


EntityType = Literal["Person", "Org", "Product", "Place", "Event"]

RelationType = Literal[
    "mentions", "defines", "contradicts", "supports", "derives_from",
    "instance_of", "part_of", "associated_with", "causes", "precedes",
]

Polarity = Literal["asserts", "denies"]


class Span(BaseModel):
    start: int = Field(..., ge=0)
    end: int = Field(..., ge=0)
    text: str


class Source(BaseModel):
    id: str
    title: str
    type: str
    raw_path: str
    ingested_at: datetime
    source_url: Optional[str] = None
    summary: str
    key_takeaways: List[str]
    questions: List[str]
    tags: List[str]
    folder: Optional[str] = None


class Entity(BaseModel):
    id: str
    type: EntityType
    aliases: List[str] = Field(default_factory=list)
    description: str
    mentions_count: int = 0
    questions: List[str]
    tags: List[str]


class Concept(BaseModel):
    id: str
    parent_concept: Optional[str] = None
    definition: str
    examples: List[str]
    related: List[str]
    questions: List[str]
    tags: List[str]


class Claim(BaseModel):
    id: str
    text: str
    subject_id: str
    source_id: str
    span: Span
    confidence: float = Field(..., ge=0.0, le=1.0)
    polarity: Polarity
    related_claim_ids: List[str] = Field(default_factory=list)


class Edge(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    from_: str = Field(..., alias="from")
    to: str
    relation: RelationType
    source_id: str
    span: Span
    confidence: float = Field(..., ge=0.0, le=1.0)
