"""Re-extract claims for ingested sources from their preserved raw text.

Replaces ONLY the claims of each source; entities, concepts, descriptions, edges and
summaries are left untouched. Dry-run by default.

Usage (run from the backend/ directory):
    python -m scripts.reextract_claims --all            # dry-run over every source
    python -m scripts.reextract_claims --slug <slug>    # dry-run one source
    python -m scripts.reextract_claims --all --apply    # actually rewrite claims
"""
import argparse
import os
import sys
from pathlib import Path

# Allow running as `python scripts/reextract_claims.py` too.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from services.claim_backfill import reextract_claims_all, reextract_claims_for_source  # noqa: E402
from services.wiki_store import WikiStore  # noqa: E402


def _print_results(results, applied: bool) -> None:
    header = "APPLIED" if applied else "DRY-RUN"
    print(f"\n== claim re-extraction ({header}) ==")
    total_old = total_new = 0
    for r in results:
        total_old += r.old_count
        total_new += r.new_count
        delta = r.new_count - r.old_count
        sign = f"+{delta}" if delta >= 0 else str(delta)
        status = f"skip ({r.skipped_reason})" if r.skipped_reason else "ok"
        print(f"  {r.slug:<40} {r.old_count:>3} -> {r.new_count:>3}  ({sign:>4})  {status}")
    overall = total_new - total_old
    print(f"  {'TOTAL':<40} {total_old:>3} -> {total_new:>3}  ({('+' + str(overall)) if overall >= 0 else overall:>4})")
    if not applied:
        print("\n  Dry-run only -- nothing written. Re-run with --apply to persist.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-extract claims for ingested sources.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="process every source")
    group.add_argument("--slug", help="process a single source by slug")
    parser.add_argument("--apply", action="store_true", help="persist changes (default: dry-run)")
    parser.add_argument("--data-dir", default=os.getenv("WIKI_DATA_DIR", "wiki_data/default"),
                        help="wiki data directory (default: wiki_data/default)")
    args = parser.parse_args()

    store = WikiStore(root=Path(args.data_dir))

    if args.all:
        results = reextract_claims_all(store, apply=args.apply)
    else:
        results = [reextract_claims_for_source(args.slug, store, apply=args.apply)]

    _print_results(results, applied=args.apply)


if __name__ == "__main__":
    main()
