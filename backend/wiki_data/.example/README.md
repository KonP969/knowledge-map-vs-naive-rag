# Demo corpus

A pre-built knowledge base (3 Wikipedia articles on RAG, vector databases, and
word embeddings) so you can explore the app before ingesting anything of your own.

**Try it:**

```bash
cd backend
WIKI_DATA_DIR=wiki_data/.example uvicorn main:app --port 8000
```

Then open the frontend and browse **Sources**, **Knowledge Map**, and **Lint**
without an API key. **Wiki Chat** and **Ingest** still call OpenAI, so those need
`OPENAI_API_KEY` in `backend/.env`.

Sample questions that exercise cross-source retrieval:

- *What problem with large language models does retrieval-augmented generation address?*
- *How do vector databases find similar records?*
- *How are word embeddings related to vector search?*

To start clean, point `WIKI_DATA_DIR` back at `wiki_data/default` (empty by default)
or a directory of your own.

Source text licensing: see `ATTRIBUTION.md`.
