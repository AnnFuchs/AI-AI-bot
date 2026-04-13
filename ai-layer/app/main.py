import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from qdrant_client import AsyncQdrantClient

from app.graph import run_graph, build_workflow
from app.llm import LLMHandler
from app.rag import RAGService
from app.schemas import UserContext
from app.config import settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing shared resources...")
    llm_handler = LLMHandler()
    qdrant_client = AsyncQdrantClient(url=settings.QDRANT_URL)
    rag_service = RAGService(qdrant_client=qdrant_client, llm_handler=llm_handler)
    graph = build_workflow()

    app.state.llm_handler = llm_handler
    app.state.qdrant_client = qdrant_client
    app.state.rag_service = rag_service
    app.state.graph = graph

    logger.info("Resources initialized.")
    yield

    logger.info("Shutting down resources...")
    await llm_handler.close()
    await qdrant_client.close()
    logger.info("Resources released.")


app = FastAPI(
    title="AI-Layer Stroke Buddy",
    description="Medical AI Assistant Layer",
    lifespan=lifespan
)


class ChatRequest(BaseModel):
    user_id: str
    session_id: str
    message: str
    user_context: UserContext


async def event_generator(request: ChatRequest, rag_service: RAGService, llm_handler: LLMHandler, graph) -> AsyncGenerator[str, None]:
    input_data = {
        "user_id": request.user_id,
        "session_id": request.session_id,
        "user_message": request.message,
        "user_context": request.user_context
    }

    config = {
        "configurable": {"thread_id": request.session_id}
    }

    try:
        async for event in run_graph(input_data, config, graph=graph, rag_service=rag_service, llm_handler=llm_handler):
            event_type = event.get("type")

            if event_type == "token":
                yield f"data: {json.dumps({'type': 'token', 'content': event.get('content', '')})}\n\n"
            elif event_type == "commands":
                yield f"data: {json.dumps({'type': 'commands', 'payload': event.get('payload')})}\n\n"
            elif event_type == "alert":
                yield f"data: {json.dumps({'type': 'alert', 'payload': event.get('payload')})}\n\n"
            elif event_type == "buttons":
                yield f"data: {json.dumps({'type': 'buttons', 'payload': event.get('payload')})}\n\n"
            elif event_type == "error":
                yield f"data: {json.dumps({'type': 'error', 'message': event.get('message')})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    except Exception as e:
        logger.error(f"Stream error: {e}")
        yield f"data: {json.dumps({'type': 'error', 'message': 'Internal Server Error'})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"


@app.post("/chat/stream")
async def chat_endpoint(request: ChatRequest):
    return StreamingResponse(
        event_generator(
            request,
            rag_service=app.state.rag_service,
            llm_handler=app.state.llm_handler,
            graph=app.state.graph
        ),
        media_type="text/event-stream"
    )


@app.get("/health")
async def health_check():
    return {"status": "ok"}