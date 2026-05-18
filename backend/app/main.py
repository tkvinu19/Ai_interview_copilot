from fastapi import FastAPI, WebSocket, Query
from dotenv import load_dotenv
import os

# ==============================
# 🔐 LOAD ENV VARIABLES
# ==============================
load_dotenv()

# Optional debug (remove later)
print("HF KEY LOADED:", os.getenv("HF_API_KEY") is not None)

# ==============================
# 🚀 IMPORT ROUTERS
# ==============================
from app.api.routes_auth import router as auth_router
from app.api.routes_resume import router as resume_router
from app.api.routes_search import router as search_router
from app.websocket.ws_handler import interview_ws_handler

# ==============================
# 🚀 INIT FASTAPI APP
# ==============================
app = FastAPI(
    title="AI Interview Copilot",
    version="1.0"
)

# ==============================
# 🔗 INCLUDE ROUTES
# ==============================
app.include_router(auth_router)
app.include_router(resume_router)
app.include_router(search_router)

# ==============================
# 🔌 WEBSOCKET ROUTE
# ==============================
@app.websocket("/ws/interview")
async def websocket_interview(
    websocket: WebSocket,
    token: str = Query(...)
):
    """
    WebSocket endpoint for live interview mode.
    Connect with: ws://localhost:8000/ws/interview?token=<jwt>

    Flow:
      1. Client sends binary audio frames (WebM/Opus from MediaRecorder)
      2. Server transcribes via Whisper
      3. Server runs RAG pipeline
      4. Server generates answer + follow-up questions
      5. All responses pushed back as JSON text frames
    """
    await interview_ws_handler(websocket, token)


# ==============================
# 🏠 ROOT ENDPOINT
# ==============================
@app.get("/")
def root():
    return {
        "message": "AI Interview Copilot API is running 🚀"
    }