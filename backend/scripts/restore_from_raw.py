"""Restore deleted sources by re-ingesting preserved raw/<dir>/parsed.md files.

Usage (from backend/):
    python scripts/restore_from_raw.py            # list what would be restored
    python scripts/restore_from_raw.py all        # restore everything below
    python scripts/restore_from_raw.py kolorystyka-projekt-porta   # restore one

Slugs of already-present sources are skipped. After restoring, run:
    python scripts/rebuild_embeddings.py
"""
import shutil
import sys
import tempfile
import time
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND))

from dotenv import load_dotenv

load_dotenv(_BACKEND / ".env")

from services.ingest_pipeline import ingest_source  # noqa: E402
from services.wiki_store import WikiStore  # noqa: E402

RAW = _BACKEND / "wiki_data" / "default" / "raw"

# raw dir -> target filename (drives the slug); mapping per wiki/log.md titles
SOURCES = {
    "6051fb6916a949d49ed5df5e5aa333c1": "katalog-2026-drzwi-do-domu-i-mieszkania.txt",
    "e2b02870d3c4467a93057b3d8326702e": "zabudowa-panelowa-porta-hide.txt",
    "4bc2e4dcdbe64ffba4b3dc3285844768": "porta-door-handles-and-accessories-pricing.txt",
    "ea634823feaa4bd5b11f341c01ba292e": "kolorystyka-projekt-porta.txt",
    "atomic-habits-the-life-changing-million-copy-bestseller-james-clear-2018-random":
        "atomic-habits-james-clear.txt",
}


def main() -> None:
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    store = WikiStore(root=_BACKEND / "wiki_data" / "default")
    existing = set(store.list_sources())

    for raw_dir, filename in SOURCES.items():
        slug = filename.removesuffix(".txt")
        parsed = RAW / raw_dir / "parsed.md"
        if arg is None:
            status = "MISSING parsed.md" if not parsed.exists() else (
                "already present — skip" if slug in existing else "would restore")
            print(f"{slug}: {status}")
            continue
        if arg != "all" and arg != slug:
            continue
        if slug in existing:
            print(f"{slug}: already present — skip")
            continue
        if not parsed.exists():
            print(f"{slug}: MISSING parsed.md — skip")
            continue

        print(f"{slug}: ingesting ({parsed.stat().st_size} bytes)...", flush=True)
        t0 = time.time()
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / filename
            shutil.copyfile(parsed, target)
            result = ingest_source(file_path=target, store=store)
        if result.status == "error":
            print(f"{slug}: ERROR: {result.error}")
        else:
            print(f"{slug}: OK slug={result.slug} ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
