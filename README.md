# RAG Chatbot

Upload your documents and chat with them. Uses Google Gemini for answers and HuggingFace embeddings for search. Each user gets their own isolated document space.

---

## What it does

- Upload PDF, DOCX, TXT, Markdown, CSV, Excel, or a web URL
- Ask questions — answers come from your documents only
- Source citations show exactly which document and page was used
- Per-session conversation memory (last 5 turns)
- Streaming responses token by token
- Multi-user with isolated document collections

## Tech Stack

| Layer | Tech |
|---|---|
| LLM | Google Gemini 1.5 Flash |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector Store | ChromaDB (local) |
| RAG Framework | LangChain |
| Backend | FastAPI + SQLAlchemy |
| Database | SQLite |
| Frontend | Streamlit |
| Auth | JWT (python-jose + passlib) |

---

## Project Structure

```
rag_chatbot/
├── backend/
│   ├── main.py
│   ├── routers/          # auth, documents, chat, admin
│   ├── models/           # SQLAlchemy ORM models
│   ├── schemas/          # Pydantic request/response models
│   ├── services/         # Business logic
│   └── middleware/       # Auth, logging, rate limiting
├── core/
│   ├── document_loader.py
│   ├── embeddings.py
│   ├── vectorstore.py
│   ├── llm.py
│   └── rag_chain.py
├── frontend/
│   ├── app.py
│   └── api_client.py
├── db/
│   └── database.py
├── configs/
│   ├── settings.py
│   └── logger.py
├── tests/
├── .env.example
└── requirements.txt
```

---

## Setup

```bash
git clone https://github.com/ZahidMiana/Rag_Based_Chatbot.git
cd Rag_Based_Chatbot

python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
```

Edit `.env` and set your keys:

```env
GEMINI_API_KEY=your_gemini_api_key_here
JWT_SECRET_KEY=your_secret_key_here
```

Get a free Gemini API key at https://aistudio.google.com

---

## Running

```bash
# Backend
uvicorn backend.main:app --reload --port 8000
# API docs: http://localhost:8000/docs

# Frontend
streamlit run frontend/app.py --server.port 8501
# UI: http://localhost:8501
```

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `GEMINI_API_KEY` | Google Gemini API key | required |
| `JWT_SECRET_KEY` | JWT signing secret | required |
| `HF_MODEL_NAME` | HuggingFace embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| `CHROMA_DB_PATH` | ChromaDB storage path | `./chroma_db` |
| `DATABASE_URL` | SQLAlchemy DB URL | `sqlite:///./rag_chatbot.db` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT access token TTL | `30` |
| `MAX_FILE_SIZE_MB` | Max upload size | `50` |
| `ALLOWED_ORIGINS` | CORS origins | `http://localhost:8501` |

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/auth/register` | POST | Register a user |
| `/auth/login` | POST | Login, returns JWT |
| `/documents/upload` | POST | Upload a document |
| `/documents/list` | GET | List uploaded documents |
| `/documents/{id}/status` | GET | Check ingestion status |
| `/chat/query` | POST | Ask a question |
| `/chat/stream` | POST | Streaming answer (SSE) |
| `/chat/history` | GET | Get session history |
| `/chat/sessions` | GET | List all sessions |
| `/admin/users` | GET | List users (admin) |

---

## Build Progress

| Module | Status | What was built |
|---|---|---|
| M1 | done | Project scaffold, config, logging, .env setup |
| M2 | done | Document ingestion — 7 formats, chunking, dedup, DB storage |
| M3 | done | HuggingFace embeddings, ChromaDB per-user collections, MMR search |
| M4 | done | Gemini LLM, RAG chain, conversation memory, chat API endpoints |
| M5 | pending | JWT auth, user model, protected routes |
| M6 | pending | FastAPI main app, all routers wired together |
| M7 | pending | Streamlit frontend |

---

## Tests

```bash
pytest tests/ -v
```

---

## License

MIT
