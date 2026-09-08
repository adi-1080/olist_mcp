"""
FastAPI Server & REST API Entrypoint.
Provides endpoints for NL analytics queries, runtime agent mode toggling, dashboard pinning, and chart refreshes.
Serves static web application.
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.database.loader import build_sqlite_database, DB_PATH
from src.agent.factory import get_agent, get_current_mode, set_current_mode
from src.agent.base import AgentResponse
from src.dashboard import storage
from dotenv import load_dotenv

if os.path.exists(".env"):
    load_dotenv(".env", override=True)
elif os.path.exists(".env.example"):
    load_dotenv(".env.example", override=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup event: Ensure database and tables exist."""
    logger.info("Initializing E-Commerce Analytics Service...")
    if not DB_PATH.exists():
        build_sqlite_database()
    storage.init_pins_table()
    yield
    logger.info("Shutting down service.")

app = FastAPI(
    title="E-Commerce Sales Analytics Chatbot & Chart Builder",
    description="AI-driven analytics system over Brazilian Olist E-Commerce dataset",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str = Field(..., example="Show monthly revenue trend for 2017")
    mode: Optional[str] = Field(None, example="llm")

class ModeConfigRequest(BaseModel):
    mode: str = Field(..., example="llm")

@app.post("/api/query", response_model=AgentResponse)
async def handle_query(request: QueryRequest = Body(...)):
    """Processes natural language analytics query and returns structured chart response."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")
    
    agent = get_agent(override_mode=request.mode)
    response = await agent.process_query(request.query)
    return response

@app.post("/api/config/mode")
async def update_agent_mode(request: ModeConfigRequest = Body(...)):
    """Updates runtime agent execution mode ('llm' or 'fallback')."""
    if request.mode.lower().strip() not in ["llm", "fallback"]:
        raise HTTPException(status_code=400, detail="Mode must be 'llm' or 'fallback'.")
    updated_mode = set_current_mode(request.mode)
    return {"status": "success", "agent_mode": updated_mode}

@app.get("/api/pins")
async def list_pins():
    """Lists all pinned dashboard charts."""
    return storage.get_all_pins()

@app.post("/api/pins")
async def pin_chart_endpoint(response_data: AgentResponse = Body(...)):
    """Pins a chart query result to the persistent dashboard."""
    pinned_item = storage.pin_chart(response_data)
    return pinned_item

@app.post("/api/pins/{pin_id}/refresh")
async def refresh_pin_endpoint(pin_id: str):
    """Refreshes a pinned chart and runs significant change diff detection."""
    updated = await storage.refresh_pin(pin_id)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Pinned item '{pin_id}' not found.")
    return updated

@app.delete("/api/pins/{pin_id}")
async def delete_pin_endpoint(pin_id: str):
    """Deletes a pinned chart from the dashboard."""
    success = storage.delete_pin(pin_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Pinned item '{pin_id}' not found.")
    return {"status": "success", "message": f"Pin '{pin_id}' removed."}

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "agent_mode": get_current_mode(),
        "database_ready": DB_PATH.exists()
    }

# Static file serving
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(static_dir, "index.html"))
