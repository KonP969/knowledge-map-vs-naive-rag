import json
import os
import tempfile
from pathlib import Path
from typing import Iterator, Optional
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from services._slug import slugify
from services.web_crawler import crawl_url
from services.ingest_pipeline import ingest_source
from services.wiki_store import WikiStore

router = APIRouter(prefix="/api/crawl", tags=["crawl"])

_WIKI_DATA_DIR = Path(os.getenv("WIKI_DATA_DIR", "wiki_data/default"))


def _get_store() -> WikiStore:
    return WikiStore(root=_WIKI_DATA_DIR)


class CrawlRequest(BaseModel):
    url: str
    max_articles: int = Field(default=5, ge=1, le=100)
    folder: Optional[str] = None


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


def _generate_crawl_events(req: CrawlRequest) -> Iterator[str]:
    crawl_result = crawl_url(req.url, req.max_articles)

    if crawl_result["error"] and not crawl_result["articles"]:
        yield _sse({"event": "fatal_error", "error": crawl_result["error"]})
        return

    articles = crawl_result["articles"]
    yield _sse({
        "event": "articles_found",
        "count": len(articles),
        "discovered": crawl_result.get("discovered", len(articles)),
    })

    store = _get_store()
    ingested = 0
    failed = 0

    for i, article in enumerate(articles):
        yield _sse({"event": "article_start", "index": i, "title": article["title"], "url": article["url"]})

        try:
            # The ingested filename drives the source slug — derive it from the
            # article title (a NamedTemporaryFile name gives slugs like 'tmpek833q').
            try:
                filename = slugify(article["title"])[:80] + ".txt"
            except ValueError:
                filename = "article.txt"
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir) / filename
                tmp_path.write_text(
                    f"# {article['title']}\n\n{article['text']}", encoding="utf-8"
                )
                ingest_result = ingest_source(file_path=tmp_path, store=store)

            if ingest_result.status == "error":
                failed += 1
                yield _sse({
                    "event": "article_done", "index": i,
                    "title": article["title"], "status": "error",
                    "error": ingest_result.error or "Pipeline error",
                })
            else:
                ingested += 1
                if req.folder:
                    try:
                        store.set_source_folder(ingest_result.slug, req.folder)
                    except Exception:
                        pass  # non-fatal: source is ingested, just unfiled
                yield _sse({
                    "event": "article_done", "index": i,
                    "title": article["title"], "status": "ok",
                    "slug": ingest_result.slug,
                })
        except Exception as exc:
            failed += 1
            yield _sse({
                "event": "article_done", "index": i,
                "title": article["title"], "status": "error",
                "error": str(exc),
            })

    yield _sse({"event": "done", "ingested": ingested, "failed": failed})


@router.post("/ingest")
def crawl_and_ingest(req: CrawlRequest) -> StreamingResponse:
    return StreamingResponse(
        _generate_crawl_events(req),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
