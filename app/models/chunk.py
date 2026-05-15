from sqlalchemy import Column, Integer, Text, ForeignKey
from app.db.database import Base


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"))
    content = Column(Text)