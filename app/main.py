from fastapi import FastAPI
from app.api.routes_auth import router as auth_router
from app.db.database import engine, Base

app = FastAPI(title="AI Interview Copilot API")

Base.metadata.create_all(bind=engine)

app.include_router(auth_router)

@app.get("/")
def root():
    return {"message": "API is running"}