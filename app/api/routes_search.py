from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.models.chunk import Chunk
from app.models.resume import Resume
from app.core.dependencies import get_current_user
from app.services.embeddings import get_embedding
from app.services.llm import generate_answer
from app.core.search import score_chunks


router = APIRouter(prefix="/search", tags=["Search"])


@router.post("/")
def semantic_search(
    query: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    try:
        user_id = int(user_id)

        # ── 1. Embed the query ───────────────────────────────────
        query_embedding = get_embedding(query)

        # ── 2. Load all user chunks ──────────────────────────────
        chunks = db.query(Chunk).join(Resume).filter(
            Resume.user_id == user_id
        ).all()

        if not chunks:
            raise HTTPException(status_code=404, detail="No resume data found. Please upload your resume first.")

        # ── 3. Score + rank chunks (boost logic inside) ──────────
        top_matches = score_chunks(
            query=query,
            query_embedding=query_embedding,
            chunks=chunks,
            top_k=3
        )

        # ── 4. Smart chunk selection for LLM ────────────────────
        # Only pass chunks that are genuinely relevant (score > 0.25)
        # This is the key fix for project mixing
        relevant_chunks = [
            item["content"]
            for item in top_matches
            if item["score"] > 0.25
        ]

        # Always pass at least 1 chunk even if scores are low
        if not relevant_chunks:
            relevant_chunks = [top_matches[0]["content"]]

        # ── 5. Generate LLM answer ───────────────────────────────
        answer = generate_answer(query, relevant_chunks)

        return {
            "query": query,
            "answer": answer,
            "top_matches": top_matches  # keep for debugging
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))