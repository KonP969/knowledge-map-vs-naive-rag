import os
import tempfile
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel
from services.web_crawler import crawl_url
from services.ingest_pipeline import ingest_source
from services.wiki_store import WikiStore

router = APIRouter(prefix="/api/crawl", tags=["crawl"])

_WIKI_DATA_DIR = Path(os.getenv("WIKI_DATA_DIR", "wiki_data/default"))


def _get_store() -> WikiStore:
    return WikiStore(root=_WIKI_DATA_DIR)


class CrawlRequest(BaseModel):
    url: str
    max_articles: int = 5


class ArticleResult(BaseModel):
    url: str
    title: str
    status: str  # "ok" | "error"
    error: str | None = None
    slug: str | None = None


class CrawlIngestResult(BaseModel):
    articles_found: int
    ingested: int
    failed: int
    results: list[ArticleResult]
    fatal_error: str | None = None


@router.post("/ingest", response_model=CrawlIngestResult)
def crawl_and_ingest(req: CrawlRequest) -> CrawlIngestResult:
    if req.max_articles < 1 or req.max_articles > 20:
        req.max_articles = 5

    crawl_result = crawl_url(req.url, req.max_articles)

    if crawl_result["error"] and not crawl_result["articles"]:
        return CrawlIngestResult(
            articles_found=0,
            ingested=0,
            failed=0,
            results=[],
            fatal_error=crawl_result["error"],
        )

    store = _get_store()
    results: list[ArticleResult] = []
    ingested = 0
    failed = 0

    for article in crawl_result["articles"]:
        # Write article text to temp file and ingest
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False, encoding="utf-8"
            ) as tmp:
                tmp.write(f"# {article['title']}\n\n{article['text']}")
                tmp_path = Path(tmp.name)

            ingest_result = ingest_source(file_path=tmp_path, store=store)
            tmp_path.unlink(missing_ok=True)

            if ingest_result.status == "error":
                results.append(ArticleResult(
                    url=article["url"],
                    title=article["title"],
                    status="error",
                    error=ingest_result.error,
                ))
                failed += 1
            else:
                results.append(ArticleResult(
                    url=article["url"],
                    title=article["title"],
                    status="ok",
                    slug=ingest_result.slug,
                ))
                ingested += 1
        except Exception as exc:
            results.append(ArticleResult(
                url=article["url"],
                title=article["title"],
                status="error",
                error=str(exc),
            ))
            failed += 1

    return CrawlIngestResult(
        articles_found=len(crawl_result["articles"]),
        ingested=ingested,
        failed=failed,
        results=results,
        fatal_error=crawl_result["error"] if not crawl_result["articles"] else None,
    )
