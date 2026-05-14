import hashlib
import json
from pathlib import Path
from typing import List, Optional

import frontmatter

from models.wiki_models import Source, Entity, Concept, Claim, Edge


SOURCES_DIR = "30-Sources"
ENTITIES_DIR = "20-Entities"
CONCEPTS_DIR = "10-Concepts"
INDEX_DIR = "00-Index"


class WikiStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        (self.root / "wiki" / SOURCES_DIR).mkdir(parents=True, exist_ok=True)
        (self.root / "wiki" / ENTITIES_DIR).mkdir(parents=True, exist_ok=True)
        (self.root / "wiki" / CONCEPTS_DIR).mkdir(parents=True, exist_ok=True)
        (self.root / "wiki" / INDEX_DIR).mkdir(parents=True, exist_ok=True)
        (self.root / "raw").mkdir(parents=True, exist_ok=True)

    # ── atomic write ─────────────────────────────────────────────────────────

    def _atomic_write(self, path: Path, content: str) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)

    # ── source ───────────────────────────────────────────────────────────────

    def _source_path(self, slug: str) -> Path:
        return self.root / "wiki" / SOURCES_DIR / f"{slug}.md"

    def _source_frontmatter(self, source: Source) -> dict:
        return {
            "id": source.id,
            "title": source.title,
            "type": source.type,
            "raw_path": source.raw_path,
            "ingested_at": source.ingested_at.isoformat(),
            "source_url": source.source_url,
            "key_takeaways": source.key_takeaways,
            "questions": source.questions,
            "tags": source.tags,
        }

    def write_source(self, source: Source, slug: str) -> None:
        path = self._source_path(slug)
        post = frontmatter.Post(content=source.summary, **self._source_frontmatter(source))
        self._atomic_write(path, frontmatter.dumps(post))

    def read_source(self, slug: str) -> Optional[Source]:
        path = self._source_path(slug)
        if not path.exists():
            return None
        post = frontmatter.load(path)
        return Source(
            id=post["id"],
            title=post["title"],
            type=post["type"],
            raw_path=post["raw_path"],
            ingested_at=post["ingested_at"],
            source_url=post.get("source_url"),
            summary=post.content.strip(),
            key_takeaways=post.get("key_takeaways", []),
            questions=post.get("questions", []),
            tags=post.get("tags", []),
        )

    def list_sources(self) -> List[str]:
        d = self.root / "wiki" / SOURCES_DIR
        return [p.stem for p in d.glob("*.md")]

    # ── entity ────────────────────────────────────────────────────────────────

    def _entity_path(self, slug: str, entity_type: str) -> Path:
        return self.root / "wiki" / ENTITIES_DIR / entity_type / f"{slug}.md"

    def write_entity(self, entity: Entity, slug: str) -> None:
        path = self._entity_path(slug, entity.type)
        path.parent.mkdir(parents=True, exist_ok=True)
        post = frontmatter.Post(content=entity.description, **{
            "id": entity.id, "type": entity.type, "aliases": entity.aliases,
            "mentions_count": entity.mentions_count,
            "questions": entity.questions, "tags": entity.tags,
        })
        self._atomic_write(path, frontmatter.dumps(post))

    def read_entity(self, slug: str, entity_type: str) -> Optional[Entity]:
        path = self._entity_path(slug, entity_type)
        if not path.exists():
            return None
        post = frontmatter.load(path)
        return Entity(
            id=post["id"], type=post["type"],
            aliases=post.get("aliases", []),
            description=post.content.strip(),
            mentions_count=post.get("mentions_count", 0),
            questions=post.get("questions", []),
            tags=post.get("tags", []),
        )

    def entity_exists(self, slug: str, entity_type: str) -> bool:
        return self._entity_path(slug, entity_type).exists()

    def merge_entity(self, new: Entity, slug: str) -> None:
        existing = self.read_entity(slug, new.type)
        if existing is None:
            self.write_entity(new, slug)
            return
        merged = existing.model_copy(update={
            "aliases": sorted(set(existing.aliases) | set(new.aliases)),
            "description": new.description if new.description.strip() else existing.description,
            "mentions_count": max(existing.mentions_count, new.mentions_count),
            "questions": sorted(set(existing.questions) | set(new.questions)),
            "tags": sorted(set(existing.tags) | set(new.tags)),
        })
        self.write_entity(merged, slug)

    # ── concept ───────────────────────────────────────────────────────────────

    def _concept_path(self, slug: str) -> Path:
        return self.root / "wiki" / CONCEPTS_DIR / f"{slug}.md"

    def write_concept(self, concept: Concept, slug: str) -> None:
        path = self._concept_path(slug)
        post = frontmatter.Post(content=concept.definition, **{
            "id": concept.id, "parent_concept": concept.parent_concept,
            "examples": concept.examples, "related": concept.related,
            "questions": concept.questions, "tags": concept.tags,
        })
        self._atomic_write(path, frontmatter.dumps(post))

    def read_concept(self, slug: str) -> Optional[Concept]:
        path = self._concept_path(slug)
        if not path.exists():
            return None
        post = frontmatter.load(path)
        return Concept(
            id=post["id"],
            parent_concept=post.get("parent_concept"),
            definition=post.content.strip(),
            examples=post.get("examples", []),
            related=post.get("related", []),
            questions=post.get("questions", []),
            tags=post.get("tags", []),
        )

    def concept_exists(self, slug: str) -> bool:
        return self._concept_path(slug).exists()

    def merge_concept(self, new: Concept, slug: str) -> None:
        existing = self.read_concept(slug)
        if existing is None:
            self.write_concept(new, slug)
            return
        merged = existing.model_copy(update={
            "examples": sorted(set(existing.examples) | set(new.examples)),
            "related": sorted(set(existing.related) | set(new.related)),
            "questions": sorted(set(existing.questions) | set(new.questions)),
            "tags": sorted(set(existing.tags) | set(new.tags)),
            "definition": new.definition if new.definition.strip() else existing.definition,
        })
        self.write_concept(merged, slug)

    # ── claims ────────────────────────────────────────────────────────────────

    def _claims_path(self) -> Path:
        return self.root / "wiki" / "claims.jsonl"

    def _claim_dedup_key(self, claim: Claim) -> str:
        # Phase 1: dedup by id only (identical objects). Phase 2 adds semantic dedup.
        raw = f"{claim.id}|{claim.subject_id}|{claim.text.strip().lower()}|{claim.polarity}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def append_claim(self, claim: Claim) -> bool:
        existing_keys = {self._claim_dedup_key(c) for c in self.read_all_claims()}
        if self._claim_dedup_key(claim) in existing_keys:
            return False
        with self._claims_path().open("a", encoding="utf-8") as f:
            f.write(claim.model_dump_json() + "\n")
        return True

    def read_all_claims(self) -> List[Claim]:
        path = self._claims_path()
        if not path.exists():
            return []
        return [
            Claim.model_validate_json(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    # ── edges ─────────────────────────────────────────────────────────────────

    def _edges_path(self) -> Path:
        return self.root / "wiki" / "edges.jsonl"

    def _edge_dedup_key(self, edge: Edge) -> str:
        return f"{edge.from_}|{edge.to}|{edge.relation}|{edge.source_id}"

    def append_edge(self, edge: Edge) -> bool:
        existing_keys = {self._edge_dedup_key(e) for e in self.read_all_edges()}
        if self._edge_dedup_key(edge) in existing_keys:
            return False
        with self._edges_path().open("a", encoding="utf-8") as f:
            f.write(edge.model_dump_json(by_alias=True) + "\n")
        return True

    def read_all_edges(self) -> List[Edge]:
        path = self._edges_path()
        if not path.exists():
            return []
        return [
            Edge.model_validate_json(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    # ── deletes / updates (Phase 6 lint fixers) ───────────────────────────

    def _rewrite_jsonl_skipping(self, path: Path, predicate) -> int:
        """Rewrite path keeping only lines where predicate(parsed_dict) is True. Returns count removed.

        Malformed (non-JSON) lines are preserved untouched; use delete_jsonl_line
        to remove a specific corrupt line by 1-indexed line number.
        """
        if not path.exists():
            return 0
        kept: List[str] = []
        removed = 0
        for raw in path.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                kept.append(raw)
                continue
            if predicate(parsed):
                kept.append(raw)
            else:
                removed += 1
        new_content = "\n".join(kept) + ("\n" if kept else "")
        self._atomic_write(path, new_content)
        return removed

    def delete_claim(self, claim_id: str) -> bool:
        path = self._claims_path()
        removed = self._rewrite_jsonl_skipping(path, lambda d: d.get("id") != claim_id)
        return removed > 0

    def delete_edge(self, edge_id: str) -> bool:
        path = self._edges_path()
        removed = self._rewrite_jsonl_skipping(path, lambda d: d.get("id") != edge_id)
        return removed > 0

    def delete_jsonl_line(self, path: Path, line_no: int) -> None:
        """Remove the 1-indexed line, preserve a `.bak` copy of the original file.

        Raises FileNotFoundError if path does not exist, ValueError if line_no
        is out of range. Backup is written before the rewrite so a mid-operation
        crash leaves the original recoverable from `.bak`.
        """
        if not path.exists():
            raise FileNotFoundError(f"Cannot delete line: {path} does not exist")
        original = path.read_text(encoding="utf-8")
        lines = original.splitlines()
        if not (1 <= line_no <= len(lines)):
            raise ValueError(f"line_no {line_no} out of range (1..{len(lines)}) for {path}")
        backup = path.with_suffix(path.suffix + ".bak")
        backup.write_text(original, encoding="utf-8")
        del lines[line_no - 1]
        new_content = "\n".join(lines) + ("\n" if lines else "")
        self._atomic_write(path, new_content)

    def delete_entity(self, slug: str, entity_type: str) -> bool:
        path = self._entity_path(slug, entity_type)
        if not path.exists():
            return False
        path.unlink()
        return True

    def delete_concept(self, slug: str) -> bool:
        path = self._concept_path(slug)
        if not path.exists():
            return False
        path.unlink()
        return True

    def update_entity_description(self, slug: str, entity_type: str, new_description: str) -> None:
        ent = self.read_entity(slug, entity_type)
        if ent is None:
            raise FileNotFoundError(f"Entity not found: {entity_type}/{slug}")
        updated = ent.model_copy(update={"description": new_description})
        self.write_entity(updated, slug)

    def update_concept_description(self, slug: str, new_definition: str) -> None:
        c = self.read_concept(slug)
        if c is None:
            raise FileNotFoundError(f"Concept not found: {slug}")
        updated = c.model_copy(update={"definition": new_definition})
        self.write_concept(updated, slug)

    def update_source_summary(self, slug: str, summary: str) -> None:
        s = self.read_source(slug)
        if s is None:
            raise FileNotFoundError(f"Source not found: {slug}")
        self.write_source(s.model_copy(update={"summary": summary}), slug)

    def update_entity_questions(self, slug: str, entity_type: str, questions: List[str]) -> None:
        ent = self.read_entity(slug, entity_type)
        if ent is None:
            raise FileNotFoundError(f"Entity not found: {entity_type}/{slug}")
        self.write_entity(ent.model_copy(update={"questions": questions}), slug)

    def update_concept_questions(self, slug: str, questions: List[str]) -> None:
        c = self.read_concept(slug)
        if c is None:
            raise FileNotFoundError(f"Concept not found: {slug}")
        self.write_concept(c.model_copy(update={"questions": questions}), slug)

    def update_source_questions(self, slug: str, questions: List[str]) -> None:
        s = self.read_source(slug)
        if s is None:
            raise FileNotFoundError(f"Source not found: {slug}")
        self.write_source(s.model_copy(update={"questions": questions}), slug)
