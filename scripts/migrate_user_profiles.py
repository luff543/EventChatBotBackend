#!/usr/bin/env python3
"""
用戶畫像資料庫遷移腳本
將用戶畫像從記憶體存儲遷移到資料庫存儲
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from database import Base, UserProfile, UserInterest, UserPreference, UserBehavior, UserFeedback, ChatSession
from utils.config import DATABASE_URL
from utils.logger import logger
import json
from datetime import datetime

def create_tables():
    """創建新的用戶畫像相關表"""
    try:
        engine = create_engine(DATABASE_URL)
        
        # 創建所有表
        Base.metadata.create_all(bind=engine)
        
        logger.info("Successfully created user profile tables")
        return True
        
    except Exception as e:
        logger.error(f"Error creating tables: {str(e)}")
        return False

def migrate_existing_data():
    """遷移現有數據（如果有的話）"""
    try:
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # 檢查是否有現有的會話需要創建用戶畫像
        sessions = db.query(ChatSession).all()
        
        for session in sessions:
            # 檢查是否已有用戶畫像
            existing_profile = db.query(UserProfile).filter(
                UserProfile.session_id == session.session_id
            ).first()
            
            if not existing_profile:
                # 創建基本用戶畫像
                profile = UserProfile(
                    session_id=session.session_id,
                    visit_count=1,
                    total_interactions=session.message_count,
                    satisfaction_score=0.0,
                    last_activity=session.updated_at,
                    personality_traits={},
                    communication_style={},
                    engagement_patterns={}
                )
                
                db.add(profile)
                logger.info(f"Created user profile for session: {session.session_id}")
        
        db.commit()
        db.close()
        
        logger.info("Successfully migrated existing data")
        return True
        
    except Exception as e:
        logger.error(f"Error migrating data: {str(e)}")
        return False

def verify_migration():
    """驗證遷移結果"""
    try:
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # 檢查表是否存在
        tables_to_check = [
            'user_profiles',
            'user_interests', 
            'user_preferences',
            'user_behaviors',
            'user_feedbacks'
        ]
        
        for table_name in tables_to_check:
            result = db.execute(text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"))
            if result.fetchone():
                logger.info(f"Table {table_name} exists")
            else:
                logger.error(f"Table {table_name} does not exist")
                return False
        
        # 檢查用戶畫像數量
        profile_count = db.query(UserProfile).count()
        session_count = db.query(ChatSession).count()
        
        logger.info(f"Found {profile_count} user profiles and {session_count} chat sessions")
        
        db.close()
        return True
        
    except Exception as e:
        logger.error(f"Error verifying migration: {str(e)}")
        return False

def main():
    """主遷移流程"""
    logger.info("Starting user profile database migration...")
    
    # 步驟1: 創建表
    logger.info("Step 1: Creating tables...")
    if not create_tables():
        logger.error("Failed to create tables")
        return False
    
    # 步驟2: 遷移現有數據
    logger.info("Step 2: Migrating existing data...")
    if not migrate_existing_data():
        logger.error("Failed to migrate existing data")
        return False
    
    # 步驟3: 驗證遷移
    logger.info("Step 3: Verifying migration...")
    if not verify_migration():
        logger.error("Migration verification failed")
        return False
    
    logger.info("User profile database migration completed successfully!")
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("✅ Migration completed successfully!")
        sys.exit(0)
    else:
        print("❌ Migration failed!")
        sys.exit(1) 