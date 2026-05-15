from fastapi import FastAPI

from app.db.database import engine, Base

# Import models (IMPORTANT for table creation)
from app.models.user import User
from app.models.resume import Resume
from app.models.chunk import Chunk

# Import routers
from app.api.routes_auth import router as auth_router
from app.api.routes_resume import router as resume_router

app = FastAPI(title="AI Interview Copilot API")

# Create tables
Base.metadata.create_all(bind=engine)

# Include routers
app.include_router(auth_router)
app.include_router(resume_router)


# Root route
@app.get("/")
def root():
    return {"message": "API is running"}