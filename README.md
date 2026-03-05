# RAG Chatbot

A production-ready Retrieval-Augmented Generation (RAG) chatbot that lets users upload their own documents and chat with them using semantic search and Google Gemini.

---

## Features

- **Multi-format document support** — PDF, DOCX, TXT, Markdown, CSV, Excel, Web URLs
- **Semantic search** — HuggingFace embeddings stored in ChromaDB for fast, accurate retrieval
- **Google Gemini LLM** — Powered by `gemini-1.5-flash` (free tier)
- **Multi-tenant** — Each user has fully isolated document collections and chat history
- **JWT Authentication** — Access + refresh token flow with role-based access (user / admin)
- **Streaming responses** — Token-by-token streaming from Gemini to the UI
- **Source citations** — Every answer shows which document chunks were used
- **FastAPI backend** — REST API with OpenAPI docs at `/docs`
- **Streamlit frontend** — Clean chat UI with upload, document management, and admin panel

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | Google Gemini 1.5 Flash (free API) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (local, free) |
| Vector Store | ChromaDB (local persistent) |
| Orchestration | LangChain |
| Backend | FastAPI + SQLAlchemy |
| Database | SQLite |
| Frontend | Streamlit |
| Auth | JWT (python-jose + passlib bcrypt) |

---

## Project Structure

```
rag_chatbot/
├── backend/
│   ├── main.py               # FastAPI app entry point
│   ├── routers/              # auth, documents, chat, admin
│   ├── models/               # SQLAlchemy ORM models
│   ├── schemas/              # Pydantic request/response models
│   ├── services/             # Business logic layer
│   └── middleware/           # Auth, logging, rate limiting
├── core/
│   ├── document_loader.py    # Multi-format document ingestion
│   ├── embeddings.py         # HuggingFace embeddings singleton
│   ├── vectorstore.py        # ChromaDB operations (per-user)
│   ├── llm.py                # Gemini LLM setup
│   └── rag_chain.py          # ConversationalRetrievalChain
├── frontend/
│   ├── app.py                # Streamlit multi-page UI
│   └── api_client.py         # Centralized HTTP client
├── db/
│   └── database.py           # SQLAlchemy engine + session
├── configs/
│   ├── settings.py           # Pydantic settings (loads .env)
│   └── logger.py             # Structlog setup
├── tests/
├── .env.example
└── requirements.txt
```

---

## Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/ZahidMiana/Rag_Based_Chatbot.git
cd Rag_Based_Chatbot
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate   # Linux / macOS
.venv\Scripts\activate      # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in:

```env
GEMINI_API_KEY=your_gemini_api_key_here
JWT_SECRET_KEY=your_strong_secret_key_here
```

Get a free Gemini API key at [https://aistudio.google.com](https://aistudio.google.com)

### 5. Run the backend

```bash
uvicorn backend.main:app --reload --port 8000
```

API docs available at: `http://localhost:8000/docs`

### 6. Run the frontend

```bash
streamlit run frontend/app.py --server.port 8501
```

Open: `http://localhost:8501`

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `GEMINI_API_KEY` | Google Gemini API key | required |
| `JWT_SECRET_KEY` | Secret for signing JWT tokens | required |
| `HF_MODEL_NAME` | HuggingFace embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| `CHROMA_DB_PATH` | Path to ChromaDB storage | `./chroma_db` |
| `DATABASE_URL` | SQLAlchemy DB URL | `sqlite:///./rag_chatbot.db` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT access token TTL | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | JWT refresh token TTL | `7` |
| `MAX_FILE_SIZE_MB` | Max upload file size | `50` |
| `ALLOWED_ORIGINS` | CORS allowed origins | `http://localhost:8501` |

---

## API Overview

| Endpoint | Method | Description |
|---|---|---|
| `/auth/register` | POST | Register new user |
| `/auth/login` | POST | Login, get JWT tokens |
| `/auth/refresh` | POST | Refresh access token |
| `/documents/upload` | POST | Upload a document (background) |
| `/documents/list` | GET | List user's documents |
| `/documents/{id}/status` | GET | Poll ingestion status |
| `/chat/query` | POST | Send question, get RAG answer |
| `/chat/history` | GET | Get chat history for session |
| `/admin/users` | GET | List all users (admin only) |
| `/admin/stats` | GET | Platform statistics (admin only) |

---

## Build Modules

| Module | Status | Description |
|---|---|---|
| M1 | ✅ Done | Project foundation & configuration |
| M2 | 🔜 | Document ingestion pipeline |
| M3 | 🔜 | Embedding engine & ChromaDB |
| M4 | 🔜 | RAG core engine (LangChain + Gemini) |
| M5 | 🔜 | Multi-tenant auth (JWT) |
| M6 | 🔜 | FastAPI REST API |
| M7 | 🔜 | Streamlit frontend |

---

## Running Tests

```bash
pytest tests/ -v
```

---

## License

MIT
