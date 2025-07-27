from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./scheduled_posts.db"

Base = declarative_base()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

class ScheduledPost(Base):
    __tablename__ = "scheduled_posts"
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(String, unique=True, index=True)
    text = Column(Text)
    image_url = Column(String, nullable=True)
    scheduled_datetime = Column(String)
    posted = Column(Boolean, default=False)

Base.metadata.create_all(bind=engine)
