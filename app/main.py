from fastapi import FastAPI
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
# 🏠 ROOT ENDPOINT
# ==============================
@app.get("/")
def root():
    return {
        "message": "AI Interview Copilot API is running 🚀"
    }