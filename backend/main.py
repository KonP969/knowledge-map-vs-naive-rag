from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from api.documents import router as documents_router
from api.chunks import router as chunks_router
from api.embeddings import router as embeddings_router
from api.chat import router as chat_router
from api.metrics import router as metrics_router

load_dotenv()

app = FastAPI(title="RAG Learning Lab API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents_router)
app.include_router(chunks_router)
app.include_router(embeddings_router)
app.include_router(chat_router)
app.include_router(metrics_router)

@app.get("/health")
def health():
    return {"status": "ok"}
