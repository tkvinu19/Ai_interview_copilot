import json
from fastapi import WebSocket, WebSocketDisconnect, Query
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.core.security import SECRET_KEY, ALGORITHM
from app.db.database import SessionLocal
from app.models.chunk import Chunk
from app.models.resume import Resume
from app.core.search import score_chunks
from app.services.embeddings import get_embedding
from app.services.llm import generate_answer, generate_followups
from app.services.whisper_service import transcribe_audio


# ===============================
# 🔐 JWT AUTH FOR WEBSOCKET
# ===============================
def get_user_from_token(token: str) -> int | None:
    """
    WebSockets can't use HTTPBearer like REST routes.
    Token is passed as a query param: ws://...?token=<jwt>
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return int(user_id)
    except (JWTError, ValueError):
        return None


# ===============================
# 📤 SEND HELPER
# ===============================
async def send_json(ws: WebSocket, data: dict):
    await ws.send_text(json.dumps(data))


# ===============================
# 🎤 MAIN WEBSOCKET HANDLER
# ===============================
async def interview_ws_handler(
    websocket: WebSocket,
    token: str = Query(...)
):
    """
    WebSocket endpoint for live interview mode.

    Message protocol (client → server):
    ┌─────────────────────────────────────────────────────┐
    │ Binary frame  → raw audio bytes (WebM/Opus)         │
    │ Text frame    → JSON { "type": "ping" }             │
    └─────────────────────────────────────────────────────┘

    Message protocol (server → client):
    ┌─────────────────────────────────────────────────────┐
    │ { "type": "connected", "message": "..." }           │
    │ { "type": "transcript", "text": "..." }             │
    │ { "type": "answer", "text": "..." }                 │
    │ { "type": "followups", "questions": [...] }         │
    │ { "type": "error", "message": "..." }               │
    │ { "type": "pong" }                                  │
    └─────────────────────────────────────────────────────┘
    """

    # ── 1. Auth check before accepting ──────────────────────────
    user_id = get_user_from_token(token)
    if user_id is None:
        await websocket.close(code=4001)
        return

    await websocket.accept()
    print(f"[WS] User {user_id} connected")

    await send_json(websocket, {
        "type": "connected",
        "message": "Interview session started. Start speaking!"
    })

    # ── 2. DB session for this connection ────────────────────────
    db: Session = SessionLocal()

    # ── 3. Pre-load user chunks once (not on every audio frame) ──
    chunks = db.query(Chunk).join(Resume).filter(
        Resume.user_id == user_id
    ).all()

    if not chunks:
        await send_json(websocket, {
            "type": "error",
            "message": "No resume found. Please upload your resume first."
        })
        await websocket.close(code=4002)
        db.close()
        return

    print(f"[WS] Loaded {len(chunks)} chunks for user {user_id}")

    # ── 4. Main receive loop ─────────────────────────────────────
    try:
        while True:
            message = await websocket.receive()

            # ── 4a. Binary frame = audio bytes ───────────────────
            if "bytes" in message and message["bytes"]:
                audio_bytes = message["bytes"]
                print(f"[WS] Received audio: {len(audio_bytes)} bytes")

                # Step 1: Transcribe
                await send_json(websocket, {
                    "type": "status",
                    "message": "Transcribing..."
                })

                transcript = transcribe_audio(audio_bytes)

                if not transcript:
                    await send_json(websocket, {
                        "type": "error",
                        "message": "Could not transcribe audio. Please speak clearly and try again."
                    })
                    continue

                # Send transcript back immediately so user sees what was heard
                await send_json(websocket, {
                    "type": "transcript",
                    "text": transcript
                })

                # Step 2: RAG — embed + retrieve
                await send_json(websocket, {
                    "type": "status",
                    "message": "Finding relevant context..."
                })

                query_embedding = get_embedding(transcript)
                top_matches = score_chunks(
                    query=transcript,
                    query_embedding=query_embedding,
                    chunks=chunks,
                    top_k=3
                )

                relevant_chunks = [
                    item["content"]
                    for item in top_matches
                    if item["score"] > 0.25
                ] or [top_matches[0]["content"]]

                # Step 3: Generate answer
                await send_json(websocket, {
                    "type": "status",
                    "message": "Generating answer..."
                })

                answer = generate_answer(transcript, relevant_chunks)

                await send_json(websocket, {
                    "type": "answer",
                    "text": answer
                })

                # Step 4: Generate follow-ups
                followups = generate_followups(transcript, answer, relevant_chunks)

                await send_json(websocket, {
                    "type": "followups",
                    "questions": followups
                })

            # ── 4b. Text frame = control messages ────────────────
            elif "text" in message and message["text"]:
                try:
                    data = json.loads(message["text"])
                    if data.get("type") == "ping":
                        await send_json(websocket, {"type": "pong"})
                except json.JSONDecodeError:
                    pass

    except WebSocketDisconnect:
        print(f"[WS] User {user_id} disconnected")

    except Exception as e:
        print(f"[WS ERROR] {e}")
        try:
            await send_json(websocket, {
                "type": "error",
                "message": "Something went wrong. Please reconnect."
            })
        except Exception:
            pass

    finally:
        db.close()
        print(f"[WS] Session closed for user {user_id}")