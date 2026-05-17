from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime
from datetime import datetime, timezone
from app.db.database import Base


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))