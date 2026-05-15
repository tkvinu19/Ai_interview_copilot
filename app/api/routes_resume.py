from fastapi import APIRouter, UploadFile, File, HTTPException
import fitz  # PyMuPDF
import os

router = APIRouter(prefix="/resume", tags=["Resume"])

UPLOAD_DIR = "uploads"

# Ensure upload folder exists
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    # Validate file type
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    file_path = os.path.join(UPLOAD_DIR, file.filename)

    # Save file
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Extract text using PyMuPDF
    try:
        doc = fitz.open(file_path)
        text = ""

        for page in doc:
            text += page.get_text()

        doc.close()

    except Exception:
        raise HTTPException(status_code=500, detail="Error reading PDF")

    return {
        "filename": file.filename,
        "extracted_text": text[:1000]  # limit output for now
    }