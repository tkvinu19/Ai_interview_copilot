import numpy as np
from typing import List, Dict


def cosine_similarity(vec1: list, vec2: list) -> float:
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    norm1, norm2 = np.linalg.norm(vec1), np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(vec1, vec2) / (norm1 * norm2))


def score_chunks(
    query: str,
    query_embedding: list,
    chunks: list,  # list of Chunk ORM objects
    top_k: int = 3
) -> List[Dict]:
    """
    Score all chunks against the query embedding.
    Applies keyword boosting to surface the right project.
    Returns top_k results sorted by score descending.
    """

    # ── keyword signals from the query ──────────────────────────
    query_lower = query.lower()

    # Map query keywords → content keywords to boost
    BOOST_RULES = [
        # If query mentions healthcare/cloudmedi/patient → boost healthcare chunks
        (["healthcare", "cloudmedi", "patient", "clinical", "hospital", "medical"],
         ["cloudmedi", "patient", "healthcare", "clinical", "llama", "whatsapp", "ocr", "prescription"]),

        # If query mentions CRISPR/bioinformatics/DNA → boost CRISPR chunks
        (["crispr", "bioinformatics", "dna", "sgrna", "gene", "prediction"],
         ["crispr", "dna", "sgrna", "bert", "biogru", "cnn", "gene"]),

        # If query mentions blog/ai blog/mistral → boost blog chunks
        (["blog", "mistral", "blip", "writing", "content"],
         ["blog", "mistral", "blip", "salesforce", "twitter", "reddit"]),
    ]

    results = []
    import json

    for chunk in chunks:
        try:
            embedding = json.loads(chunk.embedding)
        except Exception:
            continue

        score = cosine_similarity(query_embedding, embedding)
        content_lower = chunk.content.lower()

        # Apply boost rules
        for query_signals, content_signals in BOOST_RULES:
            query_match = any(kw in query_lower for kw in query_signals)
            content_match = any(kw in content_lower for kw in content_signals)

            if query_match and content_match:
                score += 0.12  # Boost same project chunks up
            elif query_match and not content_match:
                score -= 0.05  # Penalise irrelevant project chunks

        results.append({
            "content": chunk.content,
            "score": round(float(score), 6)
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]