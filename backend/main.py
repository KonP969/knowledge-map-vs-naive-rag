from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from api.metrics import router as metrics_router
from api.ingest import router as ingest_router
from api.wiki import router as wiki_router
from api.retrieval import router as retrieval_router
from api.lint import router as lint_router
from api.crawl import router as crawl_router
from services.openai_client import MissingAPIKeyError

load_dotenv()

app = FastAPI(title="Knowledge-Map RAG API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoints that don't catch errors themselves (e.g. semantic Lint) would otherwise
# answer a bare "Internal Server Error" when there's no API key.
@app.exception_handler(MissingAPIKeyError)
async def missing_api_key_handler(request: Request, exc: MissingAPIKeyError):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


app.include_router(metrics_router)
app.include_router(ingest_router)
app.include_router(wiki_router)
app.include_router(retrieval_router)
app.include_router(lint_router)
app.include_router(crawl_router)

@app.get("/health")
def health():
    return {"status": "ok"}
