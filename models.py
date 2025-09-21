import uuid
from sqlalchemy import (Column, String, ForeignKey, DateTime, Text, Integer, Enum as SQLAlchemyEnum, Boolean)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum

#Define an Enum for the recording status
class RecordingStatus(str, enum.Enum):
    PENDING = "pending"
    DONE = "done"
    ERROR = "error"

# User model corresponding to the 'users' table
class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key = True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String)

    # Relationships
    prompts = relationship("Prompt", back_populates="user", cascade="all, delete-orphan")
    recordings = relationship("Recording", back_populates="user", cascade="all, delete-orphan")

#prompt_type model: Relates a prompt with its type
class PromptType(Base):
    __tablename__ = "prompt_types"
    id = Column(Integer, primary_key=True, autoincrement=True)
    label = Column(String, unique=True, nullable=False) #e.g., "Keynote", "Debate" etc

    # Relationships
    prompts = relationship("Prompt", back_populates="prompt_type")

# Prompt Model
class Prompt(Base):
    __tablename__ = "prompts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(Text, nullable=False)
    prompt_type_id = Column(Integer, ForeignKey("prompt_types.id"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="prompts")
    prompt_type = relationship("PromptType", back_populates="prompts")
    recordings = relationship("Recording", back_populates="prompt", cascade="all, delete-orphan")

# Recording Model
class Recording(Base):
    __tablename__ = "recordings"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4) # This is the primary key
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    prompt_id = Column(Integer, ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False)
    audio_url = Column(String, nullable=False)
    transcript = Column(Text, nullable=True)
    duration_seconds = Column(Integer)
    status = Column(SQLAlchemyEnum(RecordingStatus), default=RecordingStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="recordings")
    prompt = relationship("Prompt", back_populates="recordings")