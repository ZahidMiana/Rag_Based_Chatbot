import asyncio
from typing import AsyncGenerator, Dict, List, Any, Optional

from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import PromptTemplate
from langchain.schema import Document

from core.llm import get_llm
from core.vectorstore import get_vector_store_manager
from configs.logger import get_logger

logger = get_logger(__name__)

# ── Prompt Template ───────────────────────────────────────────────────────────

_COMBINE_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template="""You are a helpful AI assistant called DocuMind AI. \
Answer the user's question based ONLY on the provided context below. \
If the answer is not found in the context, respond exactly with: \
"I couldn't find relevant information in your documents." \
Do not make up information. Be concise, accurate, and well-structured.

Context:
{context}

Question: {question}
Answer:""",
)

_CONDENSE_PROMPT = PromptTemplate(
    input_variables=["chat_history", "question"],
    template="""Given the following conversation history and a follow-up question, \
rephrase the follow-up question to be a standalone question that captures \
all necessary context from the history.

Chat History:
{chat_history}

Follow-Up Question: {question}
Standalone Question:""",
)


# ── Source Extraction ─────────────────────────────────────────────────────────

def _extract_sources(source_docs: List[Document]) -> List[Dict[str, Any]]:
    """Deduplicate and format source documents into citation dicts."""
    seen = set()
    sources = []
    for doc in source_docs:
        meta = doc.metadata or {}
        key = (meta.get("doc_id", ""), meta.get("page", 1))
        if key not in seen:
            seen.add(key)
            sources.append({
                "doc_id": meta.get("doc_id", ""),
                "filename": meta.get("source_name", "Unknown"),
                "page": meta.get("page", 1),
                "file_type": meta.get("file_type", ""),
            })
    return sources


# ── RAGChain ──────────────────────────────────────────────────────────────────

class RAGChain:
    """
    Manages per-user / per-session ConversationalRetrievalChain instances.
    Each combination of (user_id, session_id) gets its own chain with
    an independent ConversationBufferWindowMemory (last 5 turns).
    """

    def __init__(self):
        self._chains: Dict[str, ConversationalRetrievalChain] = {}
        self._vsm = get_vector_store_manager()

    def _chain_key(self, user_id: str, session_id: str) -> str:
        return f"{user_id}::{session_id}"

    def _get_or_create_chain(
        self, user_id: str, session_id: str
    ) -> ConversationalRetrievalChain:
        key = self._chain_key(user_id, session_id)
        if key not in self._chains:
            retriever = self._vsm._get_store(user_id).as_retriever(
                search_type="mmr",
                search_kwargs={
                    "k": 5,
                    "fetch_k": 20,
                    "lambda_mult": 0.5,
                },
            )
            memory = ConversationBufferWindowMemory(
                k=5,
                return_messages=True,
                memory_key="chat_history",
                output_key="answer",
            )
            self._chains[key] = ConversationalRetrievalChain.from_llm(
                llm=get_llm(),
                retriever=retriever,
                memory=memory,
                combine_docs_chain_kwargs={"prompt": _COMBINE_PROMPT},
                condense_question_prompt=_CONDENSE_PROMPT,
                return_source_documents=True,
                verbose=False,
            )
            logger.info("rag_chain_created", user_id=user_id, session_id=session_id)
        return self._chains[key]

    def query(
        self, user_id: str, question: str, session_id: str
    ) -> Dict[str, Any]:
        """
        Run a RAG query synchronously.
        Returns: {answer, sources, session_id}
        """
        chain = self._get_or_create_chain(user_id, session_id)
        try:
            result = chain.invoke({"question": question})
            sources = _extract_sources(result.get("source_documents", []))
            answer = result.get("answer", "").strip()

            logger.info(
                "rag_query_complete",
                user_id=user_id,
                session_id=session_id,
                sources_count=len(sources),
            )
            return {
                "answer": answer,
                "sources": sources,
                "session_id": session_id,
            }
        except Exception as e:
            logger.error("rag_query_failed", user_id=user_id, error=str(e))
            raise

    async def stream_query(
        self, user_id: str, question: str, session_id: str
    ) -> AsyncGenerator[str, None]:
        """
        Stream answer tokens one by one from Gemini.
        Uses LangChain's astream under the hood.
        Yields each token chunk as a string.
        At the end yields a special JSON marker with sources.
        """
        import json
        chain = self._get_or_create_chain(user_id, session_id)
        collected_sources: List[Document] = []

        try:
            async for chunk in chain.astream({"question": question}):
                if "answer" in chunk and chunk["answer"]:
                    yield chunk["answer"]
                if "source_documents" in chunk:
                    collected_sources.extend(chunk["source_documents"])

            # Emit sources as a final metadata chunk
            sources = _extract_sources(collected_sources)
            yield f"\n__SOURCES__{json.dumps(sources)}__END_SOURCES__"

        except Exception as e:
            logger.error("rag_stream_failed", user_id=user_id, error=str(e))
            yield "Sorry, an error occurred while generating the response."

    def reset_session(self, user_id: str, session_id: str) -> None:
        """Clear memory for a specific session."""
        key = self._chain_key(user_id, session_id)
        if key in self._chains:
            del self._chains[key]
            logger.info("session_reset", user_id=user_id, session_id=session_id)

    def reset_all_sessions(self, user_id: str) -> None:
        """Clear all chains for a user (e.g., on account delete)."""
        keys = [k for k in self._chains if k.startswith(f"{user_id}::")]
        for k in keys:
            del self._chains[k]


# ── Module-level singleton ────────────────────────────────────────────────────
_rag_chain_instance: Optional[RAGChain] = None


def get_rag_chain() -> RAGChain:
    global _rag_chain_instance
    if _rag_chain_instance is None:
        _rag_chain_instance = RAGChain()
    return _rag_chain_instance
