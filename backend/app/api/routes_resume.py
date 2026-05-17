from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
import fitz
import os
import json

from app.db.deps import get_db
from app.models.resume import Resume
from app.models.chunk import Chunk
from app.core.dependencies import get_current_user
from app.core.chunking import chunk_text
from app.core.embeddings import get_embedding

router = APIRouter(prefix="/resume", tags=["Resume"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    user_id = int(user_id)

    # ==============================
    # ✅ STEP 1: DELETE OLD DATA
    # ==============================

    old_resumes = db.query(Resume).filter(Resume.user_id == user_id).all()

    for resume in old_resumes:
        # delete related chunks first
        db.query(Chunk).filter(Chunk.resume_id == resume.id).delete()

    # delete resumes
    db.query(Resume).filter(Resume.user_id == user_id).delete()

    db.commit()

    # ==============================
    # ✅ STEP 2: VALIDATE FILE
    # ==============================

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    file_path = os.path.join(UPLOAD_DIR, file.filename)

    # ==============================
    # ✅ STEP 3: SAVE FILE
    # ==============================

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # ==============================
    # ✅ STEP 4: EXTRACT TEXT
    # ==============================

    try:
        doc = fitz.open(file_path)
        text = ""

        for page in doc:
            text += page.get_text()

        doc.close()

    except Exception:
        raise HTTPException(status_code=500, detail="Error reading PDF")

    if not text.strip():
        raise HTTPException(status_code=400, detail="Empty or unreadable PDF")

    # ==============================
    # ✅ STEP 5: SAVE RESUME
    # ==============================

    new_resume = Resume(
        user_id=user_id,
        content=text
    )

    db.add(new_resume)
    db.flush()  # get ID before commit

    # ==============================
    # ✅ STEP 6: CHUNK + EMBEDDING
    # ==============================

    chunks = chunk_text(text)

    for chunk_content in chunks:
        embedding = get_embedding(chunk_content)

        new_chunk = Chunk(
            resume_id=new_resume.id,
            content=chunk_content,
            embedding=json.dumps(embedding)
        )

        db.add(new_chunk)

    db.commit()

    # ==============================
    # ✅ RESPONSE
    # ==============================

    return {
        "message": "Resume uploaded, replaced old data, chunked, and embedded successfully",
        "resume_id": new_resume.id,
        "chunks_created": len(chunks),
        "preview": text[:300]
    }