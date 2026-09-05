# -*- coding: utf-8 -*-
"""Buduje ODDZIELNY vault na eksperyment „jezyk czy struktura dokumentu?".

Gold-set pokazal, ze zrodla EN (artykuly blogowe) wypadaja duzo lepiej niz PL
(katalogi produktowe) — ale w `wiki_data/default` te dwie zmienne sa sklejone:
kazde zrodlo PL jest katalogiem, kazde EN artykulem. Nie da sie orzec, czy winny
jest jezyk, czy struktura tekstu.

Ten skrypt dokłada brakujaca kratke tabelki: **polskie artykuly narracyjne**.
Wtedy:
    PL katalog  vs  PL artykul   -> izoluje strukture przy stalym jezyku
    PL artykul  vs  EN artykul   -> izoluje jezyk przy stalej strukturze

Pisze do osobnego katalogu (domyslnie `wiki_data/eval_lang`), wiec `default`
zostaje nietkniety.

    cd backend
    python scripts/build_eval_vault.py --dry-run     # tylko odkryj URL-e, nic nie kosztuje
    python scripts/build_eval_vault.py --max 3       # crawl + ingest 3 artykulow
"""
import argparse
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from services.ingest_pipeline import ingest_source  # noqa: E402
from services.web_crawler import crawl_url  # noqa: E402
from services.wiki_index import regenerate_index  # noqa: E402
from services.wiki_store import WikiStore  # noqa: E402
from services._slug import slugify  # noqa: E402

DEFAULT_LISTING = "https://www.porta.com.pl/otworzsiena/wnetrza"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_LISTING, help="strona listingu artykulow")
    ap.add_argument("--vault", default="wiki_data/eval_lang")
    ap.add_argument("--max", type=int, default=3, help="ile artykulow zaciagnac")
    ap.add_argument("--folder", default="pl-artykuly")
    ap.add_argument("--dry-run", action="store_true", help="tylko crawl, bez ingestu (bez kosztow LLM)")
    args = ap.parse_args()

    print("crawl: %s (max %d)" % (args.url, args.max), flush=True)
    result = crawl_url(args.url, args.max)
    articles = result.get("articles") or []
    if result.get("error") and not articles:
        print("BLAD crawla: %s" % result["error"], file=sys.stderr)
        return 1

    print("znaleziono %d artykulow (odkryto %d URL-i):"
          % (len(articles), result.get("discovered", len(articles))))
    for a in articles:
        print("   %-58s %6d znakow  %s" % (a["title"][:58], len(a["text"]), a["url"]))

    if args.dry_run:
        print("\nDRY RUN — nic nie zaingestowano.")
        return 0

    store = WikiStore(args.vault)
    ok = failed = 0
    for i, a in enumerate(articles, 1):
        print("\n[%d/%d] ingest: %s" % (i, len(articles), a["title"][:60]), flush=True)
        try:
            filename = slugify(a["title"])[:80] + ".txt"
        except ValueError:
            filename = "article-%d.txt" % i
        try:
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / filename
                path.write_text("# %s\n\n%s" % (a["title"], a["text"]), encoding="utf-8")
                res = ingest_source(file_path=path, store=store)
            if res.status == "error":
                failed += 1
                print("    BLAD: %s" % (res.error or "pipeline error"), file=sys.stderr)
            else:
                ok += 1
                store.set_source_folder(res.slug, args.folder)
                print("    ok -> %s" % res.slug)
        except Exception as exc:
            failed += 1
            print("    BLAD: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)

    if ok:
        regenerate_index(store)
        print("\nindeks przebudowany dla %s" % args.vault)
    print("zaingestowano %d, bledow %d" % (ok, failed))
    print("\nDalej: zbuduj embeddingi i odpal eval na tym vaulcie:")
    print("  python scripts/rebuild_embeddings.py --vault %s" % args.vault)
    print("  python scripts/run_gold_eval.py --vault %s --category ..." % args.vault)
    return 0


if __name__ == "__main__":
    sys.exit(main())
