from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey, Float, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from utils.config import DATABASE_URL
import uuid
import re
from typing import List, Dict, Any, Optional

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(50), unique=True, index=True)
    ip_address = Column(String(50), index=True)
    message_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    messages = relationship("ChatMessage", back_populates="session", order_by="ChatMessage.created_at")
    user_profile = relationship("UserProfile", back_populates="session", uselist=False)

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(50), ForeignKey("chat_sessions.session_id"))
    role = Column(String(20))  # 'user' or 'assistant'
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    session = relationship("ChatSession", back_populates="messages")

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(50), ForeignKey("chat_sessions.session_id"), unique=True, index=True)
    visit_count = Column(Integer, default=1)
    total_interactions = Column(Integer, default=0)
    satisfaction_score = Column(Float, default=0.0)
    last_activity = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # JSON fields for complex data
    personality_traits = Column(JSON, default=dict)  # openness, social_level, adventure_seeking, etc.
    communication_style = Column(JSON, default=dict)  # formality, detail_preference, question_style
    engagement_patterns = Column(JSON, default=dict)  # response_length, enthusiasm_level, decision_making
    
    # Relationships
    session = relationship("ChatSession", back_populates="user_profile")
    interests = relationship("UserInterest", back_populates="profile", cascade="all, delete-orphan")
    preferences = relationship("UserPreference", back_populates="profile", cascade="all, delete-orphan")
    behaviors = relationship("UserBehavior", back_populates="profile", cascade="all, delete-orphan")
    feedbacks = relationship("UserFeedback", back_populates="profile", cascade="all, delete-orphan")

class UserInterest(Base):
    __tablename__ = "user_interests"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("user_profiles.id"))
    interest = Column(String(100), index=True)
    confidence = Column(Float, default=0.5)  # 0.0 to 1.0
    source = Column(String(50), default="conversation")  # conversation, explicit, inferred
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    profile = relationship("UserProfile", back_populates="interests")

class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("user_profiles.id"))
    preference_type = Column(String(50), index=True)  # category, location, time, group_size, budget
    preference_value = Column(String(200))
    confidence = Column(Float, default=0.5)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    profile = relationship("UserProfile", back_populates="preferences")

class UserBehavior(Base):
    __tablename__ = "user_behaviors"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("user_profiles.id"))
    behavior_type = Column(String(50), index=True)  # search, click, view, interaction
    behavior_data = Column(JSON)  # flexible data storage
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    profile = relationship("UserProfile", back_populates="behaviors")

class UserFeedback(Base):
    __tablename__ = "user_feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("user_profiles.id"))
    feedback_type = Column(String(50), index=True)  # rating, comment, satisfaction
    feedback_value = Column(String(500))
    rating = Column(Float)  # 1.0 to 5.0
    context = Column(JSON)  # context when feedback was given
    created_at = Column(DateTime, default=datetime.utcnow)
    
    profile = relationship("UserProfile", back_populates="feedbacks")

# Create all tables
Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 

async def get_or_create_session(db, ip_address: str, session_id: str = None):
    """
    獲取或創建會話，根據消息數量和 IP 地址管理會話
    """
    if session_id:
        # 嘗試獲取現有會話
        session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
        if session:
            # 檢查消息數量
            if session.message_count < 20:
                return session
            # 如果 session 已滿，不使用傳入的 session_id，讓系統創建新的
    
    # 嘗試獲取該 IP 的最新未滿的會話
    latest_session = (
        db.query(ChatSession)
        .filter(
            ChatSession.ip_address == ip_address,
            ChatSession.message_count < 20
        )
        .order_by(ChatSession.created_at.desc())
        .first()
    )
    
    if latest_session:
        return latest_session
    
    # 創建新會話（總是使用新的 UUID，不使用傳入的 session_id）
    new_session = ChatSession(
        session_id=str(uuid.uuid4()),
        ip_address=ip_address,
        message_count=0
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session

async def add_message_to_session(db, session: ChatSession, role: str, content: str):
    """
    添加消息到會話並更新消息計數
    """
    message = ChatMessage(
        session_id=session.session_id,
        role=role,
        content=content
    )
    db.add(message)
    
    # 更新會話的消息計數
    session.message_count += 1
    session.updated_at = datetime.utcnow()
    
    db.commit()
    return message 