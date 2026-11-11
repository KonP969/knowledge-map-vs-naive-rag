"""Store-wide lookup of entity/concept nodes by name, used by the resolver.

The LLM names the same thing in many ways across documents — "PORTA HIDE",
"drzwi ukryte PORTA HIDE", "modele z kolekcji PORTA HIDE" — and sometimes with a
different entity type. Matching only exact names inside the current document
left most claims pointing at nodes that don't exist ("dangling subjects"), which
cut them out of the knowledge map.

Lookup order (first hit wins):
  1. exact slug of a node's name or of one of its aliases
  2. descriptive prefix: the name ENDS with a known multi-word node name
     ("drzwi ukryte porta-hide" -> porta-hide)
  3. generic suffix: the name STARTS with a known multi-word node name and the
     rest is only a generic word ("porta-hide doors" -> porta-hide)

Deliberately NOT matched: a longer product name that merely starts with a
shorter one ("porta-system-elegance" is not "porta-system"), and single-word
nodes inside longer names ("porta" never swallows "drzwi porta hide").
"""
import re
from dataclasses import dataclass
from typing import Dict, Optional

import frontmatter as fm

from services._slug import slugify
from services.wiki_store import CONCEPTS_DIR, ENTITIES_DIR, WikiStore

# Words that may trail a node name without changing what it refers to.
_GENERIC_TRAILING = {
    "drzwi", "door", "doors", "kolekcja", "kolekcji", "collection", "seria",
    "series", "model", "modele", "modelu",
}
# Descriptive words that may precede a node name ("drzwi wewnetrzne PORTA").
_GENERIC_LEADING = {
    "drzwi", "wewnetrzne", "door", "doors", "kolekcja", "kolekcji", "z",
    "modele", "model", "seria", "collection", "linia", "wzornicza", "marka", "brand",
}


@dataclass(frozen=True)
class NodeRef:
    kind: str          # "entity" | "concept"
    id: str            # e_006 / c_012
    slug: str
    entity_type: Optional[str] = None

    @property
    def subject_id(self) -> str:
        return f"{self.kind}:{self.id}"


def _safe_slug(text: str) -> Optional[str]:
    try:
        return slugify(text)
    except ValueError:
        return None


class NodeIndex:
    def __init__(self):
        # key -> {kind: NodeRef}; one key can name both an entity and a concept
        self._by_key: Dict[str, Dict[str, NodeRef]] = {}

    # ── building ──────────────────────────────────────────────────────────
    @classmethod
    def from_store(cls, store: WikiStore) -> "NodeIndex":
        idx = cls()
        entities_root = store.root / "wiki" / ENTITIES_DIR
        if entities_root.exists():
            for type_dir in sorted(p for p in entities_root.iterdir() if p.is_dir()):
                for md in sorted(type_dir.glob("*.md")):
                    idx._add_file(md, "entity", type_dir.name)
        concepts_root = store.root / "wiki" / CONCEPTS_DIR
        if concepts_root.exists():
            for md in sorted(concepts_root.glob("*.md")):
                idx._add_file(md, "concept", None)
        return idx

    def _add_file(self, md, kind, entity_type):
        try:
            post = fm.load(str(md))
        except Exception:
            return
        node_id = str(post.get("id", "")).strip()
        if not re.match(r"^[ec]_\d+$", node_id):
            return
        ref = NodeRef(kind=kind, id=node_id, slug=md.stem, entity_type=entity_type)
        self.add(ref, [md.stem] + list(post.get("aliases") or []))

    def add(self, ref: NodeRef, names) -> None:
        for name in names:
            key = _safe_slug(str(name)) if name else None
            if key:
                # first writer wins: the earliest node keeps the name
                self._by_key.setdefault(key, {}).setdefault(ref.kind, ref)

    # ── lookup ────────────────────────────────────────────────────────────
    def _pick(self, hits: Dict[str, NodeRef], prefer_kind: Optional[str]) -> NodeRef:
        if prefer_kind and prefer_kind in hits:
            return hits[prefer_kind]
        return hits.get("entity") or hits["concept"]

    def find(self, name: str, prefer_kind: Optional[str] = None) -> Optional[NodeRef]:
        key = _safe_slug(name) if name else None
        if not key:
            return None
        if key in self._by_key:
            return self._pick(self._by_key[key], prefer_kind)

        tokens = key.split("-")
        # "drzwi wewnetrzne PORTA" -> "porta": descriptive words in front of a name
        core = list(tokens)
        while len(core) > 1 and core[0] in _GENERIC_LEADING:
            core.pop(0)
        if core != tokens and "-".join(core) in self._by_key:
            return self._pick(self._by_key["-".join(core)], prefer_kind)

        best: Optional[NodeRef] = None
        best_len = 0
        for n in range(len(tokens) - 1, 1, -1):  # candidate node names of >= 2 words
            suffix = "-".join(tokens[-n:])
            if suffix in self._by_key and n > best_len:
                best, best_len = self._pick(self._by_key[suffix], prefer_kind), n
            prefix = "-".join(tokens[:n])
            rest = tokens[n:]
            if (prefix in self._by_key and n > best_len
                    and rest and all(t in _GENERIC_TRAILING for t in rest)):
                best, best_len = self._pick(self._by_key[prefix], prefer_kind), n
        return best

    def find_entity_by_name(self, name: str) -> Optional[NodeRef]:
        """Exact name/alias match against entities only (any type)."""
        key = _safe_slug(name) if name else None
        hits = self._by_key.get(key or "", {})
        return hits.get("entity")
