from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from api.documents import router as documents_router
from api.chunks import router as chunks_router
from api.embeddings import router as embeddings_router
from api.chat import router as chat_router
from api.metrics import router as metrics_router
from api.folders import router as folders_router
from api.ingest import router as ingest_router
from api.wiki import router as wiki_router
from api.retrieval import router as retrieval_router
from api.lint import router as lint_router

load_dotenv()

app = FastAPI(title="RAG Learning Lab API", version="1.0.0")


@app.on_event("startup")
def startup() -> None:
    from api.documents import load_documents
    from api.chunks import load_chunks
    from api.folders import load_folders
    load_documents()
    load_chunks()
    load_folders()

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents_router)
app.include_router(chunks_router)
app.include_router(embeddings_router)
app.include_router(chat_router)
app.include_router(metrics_router)
app.include_router(folders_router)
app.include_router(ingest_router)
app.include_router(wiki_router)
app.include_router(retrieval_router)
app.include_router(lint_router)

@app.get("/health")
def health():
    return {"status": "ok"}
