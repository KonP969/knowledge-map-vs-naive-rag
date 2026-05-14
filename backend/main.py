from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from api.metrics import router as metrics_router
from api.ingest import router as ingest_router
from api.wiki import router as wiki_router
from api.retrieval import router as retrieval_router
from api.lint import router as lint_router

load_dotenv()

app = FastAPI(title="RAG 2.0 Karpathy Method API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(metrics_router)
app.include_router(ingest_router)
app.include_router(wiki_router)
app.include_router(retrieval_router)
app.include_router(lint_router)

@app.get("/health")
def health():
    return {"status": "ok"}
