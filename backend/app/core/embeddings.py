from sentence_transformers import SentenceTransformer

# Upgraded: better semantic understanding than all-MiniLM-L6-v2
# Still free, same API, just more accurate for resume/job context
model = SentenceTransformer('BAAI/bge-small-en-v1.5')


def get_embedding(text: str):
    # BGE models need this prefix for better retrieval accuracy
    if not text.startswith("Represent this sentence"):
        text = f"Represent this sentence for searching relevant passages: {text}"
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()