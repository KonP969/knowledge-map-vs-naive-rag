# -*- coding: utf-8 -*-
"""Re-ingest every raw/<slug>/parsed.md of a vault into a FRESH vault.

Use it after changing the ingest pipeline (classifier, resolver, ...) to get a
graph built entirely by the current code. The source vault is only read.

    cd backend
    python scripts/rebuild_vault.py --source wiki_data/default --target wiki_data/rebuilt
    python scripts/rebuild_vault.py ... --extra tests/rag_evaluation/fixtures/conflict

Each raw dir is copied to a temp file named after the dir, so source slugs stay
the same. Documents are ingested in sorted order. Prints a dangling-subject
report at the end (claims whose subject is not a real entity/concept node).
"""
import argparse
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from services.ingest_pipeline import ingest_source  # noqa: E402
from services.wiki_store import WikiStore  # noqa: E402


def dangling_report(store: WikiStore) -> str:
    node_ids = set()
    for kind_dir, kind in (("20-Entities", "entity"), ("10-Concepts", "concept")):
        root = store.root / "wiki" / kind_dir
        for md in root.rglob("*.md") if root.exists() else []:
            for line in md.read_text(encoding="utf-8").splitlines()[:15]:
                if line.startswith("id: "):
                    node_ids.add("%s:%s" % (kind, line[4:].strip()))
                    break
    claims = store.read_all_claims()
    dangling = [c for c in claims if c.subject_id not in node_ids]
    pct = 100.0 * len(dangling) / len(claims) if claims else 0.0
    return "claims=%d dangling=%d (%.0f%%) nodes=%d" % (len(claims), len(dangling), pct, len(node_ids))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="wiki_data/default")
    ap.add_argument("--target", required=True)
    ap.add_argument("--extra", help="folder of extra .md docs to ingest after the raw sources")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--report-only", action="store_true", help="just print the dangling report for --target")
    args = ap.parse_args()

    dst = Path(args.target)
    if args.report_only:
        print(dangling_report(WikiStore(root=dst)))
        return 0
    src_raw = Path(args.source) / "raw"
    if not src_raw.is_dir():
        print("ERROR: %s has no raw/" % args.source, file=sys.stderr)
        return 1
    if dst.exists():
        if not args.force:
            print("ERROR: %s exists (use --force)" % dst, file=sys.stderr)
            return 1
        shutil.rmtree(dst)

    store = WikiStore(root=dst)
    docs = [d / "parsed.md" for d in sorted(src_raw.iterdir()) if (d / "parsed.md").exists()]
    with tempfile.TemporaryDirectory() as tmp:
        for i, parsed in enumerate(docs, 1):
            f = Path(tmp) / (parsed.parent.name + ".md")
            shutil.copyfile(parsed, f)
            res = ingest_source(f, store)
            print("[%d/%d] %-60s %s claims=%d" % (i, len(docs), parsed.parent.name[:60],
                                                 res.status, res.claims_added), flush=True)
    if args.extra:
        for f in sorted(Path(args.extra).glob("*.md")):
            res = ingest_source(f, store)
            print("[extra] %-55s %s claims=%d conflicts=%d"
                  % (f.name, res.status, res.claims_added, len(res.conflicts)), flush=True)
    print(dangling_report(store))
    return 0


if __name__ == "__main__":
    sys.exit(main())
