def chunk_text(text: str, max_chars: int = 300):
    lines = text.split("\n")

    chunks = []
    current_chunk = ""

    for line in lines:
        # 🔹 Clean line (REMOVE bullets, dots, etc.)
        line = line.strip().lstrip(".•- ").strip()

        if not line:
            continue

        # 🔹 New section detection (better structure)
        if line.isupper() or line.endswith(":"):
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = line
            continue

        # 🔹 Build chunk
        if len(current_chunk) + len(line) + 1 <= max_chars:
            current_chunk += " " + line
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = line

    # 🔹 Final chunk
    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks