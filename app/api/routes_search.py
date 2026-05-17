from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.chunk import Chunk
from app.models.resume import Resume
from app.core.dependencies import get_current_user

import numpy as np
import ast

from app.services.embeddings import get_embedding  # make sure this matches your file name

router = APIRouter(prefix="/search", tags=["Search"])


# -------------------------------
# Cosine Similarity Function
# -------------------------------
def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)

    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


# -------------------------------
# Semantic Search Route
# -------------------------------
@router.post("/")
def semantic_search(
    query: str = Query(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    # Step 1: Convert query → embedding
    query_embedding = get_embedding(query)

    # Step 2: Fetch ONLY user's chunks (CRITICAL FIX)
    chunks = db.query(Chunk).join(Resume).filter(
        Resume.user_id == int(user_id)
    ).all()

    results = []

    for chunk in chunks:
        try:
            # Step 3: Convert stored embedding (string → list)
            chunk_embedding = ast.literal_eval(chunk.embedding)

            # Step 4: Compute similarity
            score = cosine_similarity(query_embedding, chunk_embedding)

            # Step 5: Boost for "project-like" chunks
            if "project" in query.lower():
                if "project" in chunk.content.lower() or "built" in chunk.content.lower():
                    score += 0.05

            results.append({
                "content": chunk.content,
                "score": float(score)
            })

        except Exception as e:
            # Skip bad embeddings safely
            continue

    # Step 6: Sort by score (highest first)
    results = sorted(results, key=lambda x: x["score"], reverse=True)

    # Step 7: Return top 3 matches
    top_matches = results[:3]

    return {
        "query": query,
        "top_matches": top_matches
    }