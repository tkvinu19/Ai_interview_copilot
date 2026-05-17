from sentence_transformers import SentenceTransformer

# Load model once
model = SentenceTransformer('all-MiniLM-L6-v2')


def get_embedding(text: str):
    embedding = model.encode(text)
    return embedding.tolist()