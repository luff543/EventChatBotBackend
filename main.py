from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import httpx
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
import uuid
import uvicorn
from sqlalchemy.orm import Session
from database import get_db, ChatSession, ChatMessage, Base, engine, get_or_create_session, add_message_to_session
from utils.config import (
    API_PREFIX,
    API_TITLE,
    API_DESCRIPTION,
    API_VERSION,
    DATABASE_URL,
    EVENTGO_API_BASE
)
from llm_handler import (
    process_chat_message,
    analyze_monthly_trends,
    analyze_geographic_distribution,
    recommend_events,
    generate_analysis_report
)
from utils.logger import logger
import json
from pydantic import validator
from core.agent import Agent

# Create database tables
logger.info("Creating database tables...")
Base.metadata.create_all(bind=engine)
logger.info("Database tables created successfully")

# Initialize FastAPI app
logger.info("Initializing FastAPI application...")
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    prefix=API_PREFIX
)
logger.info("FastAPI application initialized successfully")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://eventgo.widm.csie.ncu.edu.tw", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("CORS middleware configured")

# Initialize global httpx client
logger.info("Initializing global httpx client...")
http_client = httpx.AsyncClient(verify=False)  # Disable SSL verification for local development
logger.info("Global httpx client initialized successfully")

# Add startup and shutdown events
@app.on_event("startup")
async def startup_event():
    logger.info("Starting up application...")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down application...")
    await http_client.aclose()
    logger.info("Global httpx client closed successfully")

# 添加獲取客戶端 IP 的依賴函數
def get_client_ip(request: Request) -> str:
    """
    獲取客戶端 IP 地址
    """
    # 嘗試從 X-Real-IP 頭獲取（Nginx 代理設置）
    if "x-real-ip" in request.headers:
        return request.headers["x-real-ip"]
    
    # 嘗試從 X-Forwarded-For 頭獲取
    if "x-forwarded-for" in request.headers:
        return request.headers["x-forwarded-for"].split(",")[0]
    
    # 使用直接客戶端 IP
    return request.client.host

class EventSearchParams(BaseModel):
    query: Optional[str] = None
    type: Optional[str] = None
    from_: Optional[int] = Field(None, alias="from"),
    to: Optional[int] = None
    city: Optional[str] = None
    category: Optional[str] = None
    gps: Optional[str] = None
    radius: Optional[int] = None
    num: Optional[int] = 200
    page: Optional[int] = 1
    sort: Optional[str] = "start_time"
    asc: Optional[bool] = True

    # Pydantic v2 用法
    model_config = {
        "populate_by_name": True  # ← 等同舊版的 allow_population_by_field_name
    }

class EventResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    location: Optional[str]
    start_time: int
    end_time: Optional[int]
    category: Optional[str]
    venue: Optional[Dict[str, Any]]

class EventSearchResponse(BaseModel):
    count: int
    queryTime: float
    events: List[Dict[str, Any]]

class Pagination(BaseModel):
    current_page: int = Field(default=1, description="當前頁碼")
    events_per_page: int = Field(default=5, description="每頁顯示的事件數量")
    total_events: int = Field(default=0, description="總事件數量")

class ChatMessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    chat_history: Optional[List[Dict[str, Any]]] = None
    page: Optional[int] = Field(default=1, alias="p")
    search_params: Optional[Dict[str, Any]] = None
    is_proactive_response: Optional[bool] = False
    is_follow_up_suggestion: Optional[bool] = False
    
    model_config = {
        "populate_by_name": True  # 允許使用 p 作為 page 的別名
    }

class ProactiveQuestions(BaseModel):
    questions: List[str] = Field(default_factory=list, description="主動式問題列表")
    follow_up_suggestions: List[str] = Field(default_factory=list, description="後續建議列表")
    confidence: float = Field(default=0.0, description="信心度分數")
    personalization_level: Optional[str] = Field(default=None, description="個性化等級")

class UserProfileSummary(BaseModel):
    visit_count: int = Field(default=1, description="訪問次數")
    interests: List[str] = Field(default_factory=list, description="興趣列表")
    activity_preferences: Optional[Dict[str, Any]] = Field(default=None, description="活動偏好")
    personality_traits: Optional[Dict[str, Any]] = Field(default=None, description="個性特徵")
    satisfaction_scores: List[float] = Field(default_factory=list, description="滿意度評分")
    last_activity: Optional[str] = Field(default=None, description="最後活動時間")

class ChatMessageResponse(BaseModel):
    message: str
    search_result: Optional[EventSearchResponse] = None
    search_params: Optional[Dict[str, Any]] = None
    pagination: Optional[Pagination] = None
    session_id: Optional[str] = None
    proactive_questions: Optional[ProactiveQuestions] = None
    user_profile_summary: Optional[UserProfileSummary] = None
    conversation_stage: Optional[str] = None

class ActivityHistogramParams(BaseModel):
    group: str
    type: Optional[str] = None
    query: Optional[str] = None
    from_: Optional[int] = Field(None, alias='from')
    to: Optional[int] = None
    id: Optional[str] = None
    city: Optional[str] = None
    category: Optional[str] = None
    sort: Optional[str] = "value"
    asc: Optional[bool] = False
    num: Optional[int] = 20

    # Pydantic v2 用法
    model_config = {
        "populate_by_name": True  # ← 等同舊版的 allow_population_by_field_name
    }

class ActivityDateHistogramParams(BaseModel):
    interval: str
    group: str
    timezone: Optional[str] = "Asia/Taipei"
    query: Optional[str] = None
    from_: Optional[int] = Field(None, alias='from')
    to: Optional[int] = None
    timeKey: Optional[str] = None
    id: Optional[str] = None
    city: Optional[str] = None
    category: Optional[str] = None
    type: Optional[str] = None
    num: Optional[int] = 100

    model_config = {
        "populate_by_name": True  # 允許用 from_ 傳值
    }

@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to Event Chatbot API"}

@app.post("/api/chat", response_model=ChatMessageResponse)
async def chat(
    request: ChatMessageRequest,
    client_ip: str = Depends(get_client_ip),
    db: Session = Depends(get_db)
):
    try:
        # 獲取或創建會話
        session = await get_or_create_session(db, client_ip, request.session_id)
        
        # 保存用戶消息
        await add_message_to_session(db, session, "user", request.message)
        
        # 初始化Agent
        agent = Agent(session_id=session.session_id)
        
        # 使用Agent處理消息（傳入資料庫session）
        response = await agent.process_message(
            message=request.message,
            db=db,
            chat_history=request.chat_history or [],
            page=request.page,
            search_params=request.search_params
        )
        
        # 保存助手回覆
        await add_message_to_session(db, session, "assistant", response.get("message", ""))
        
        logger.info(f"Chat response generated for session {session.session_id}")
        
        # 構建回應
        chat_response = {
            "message": response.get("message", ""),
            "search_result": response.get("events"),
            "search_params": response.get("search_params"),
            "pagination": response.get("pagination"),
            "session_id": session.session_id,
            "proactive_questions": response.get("proactive_questions"),
            "user_profile_summary": response.get("user_profile_summary"),
            "conversation_stage": response.get("conversation_stage")
        }
        
        return chat_response
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"處理聊天訊息時發生錯誤: {str(e)}")

@app.get("/api/chat/history/latest")
async def get_latest_chat_history(
    client_ip: str = Depends(get_client_ip),
    db: Session = Depends(get_db)
):
    """
    獲取該 IP 最近的未滿會話歷史
    """
    try:
        # 查找該 IP 的最新未滿會話
        session = (
            db.query(ChatSession)
            .filter(
                ChatSession.ip_address == client_ip,
                ChatSession.message_count < 20
            )
            .order_by(ChatSession.updated_at.desc())
            .first()
        )
        
        if not session:
            return {
                "session_id": None,
                "messages": [],
                "message_count": 0
            }
        
        # 獲取會話消息
        messages = [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.created_at.isoformat()
            }
            for msg in session.messages
        ]
        
        return {
            "session_id": session.session_id,
            "messages": messages,
            "message_count": session.message_count
        }
        
    except Exception as e:
        logger.error(f"Error getting latest chat history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/history/{session_id}")
async def get_chat_history(
    session_id: str,
    client_ip: str = Depends(get_client_ip),
    db: Session = Depends(get_db)
):
    try:
        # 驗證會話是否屬於當前客戶端
        session = db.query(ChatSession).filter(
            ChatSession.session_id == session_id,
            ChatSession.client_ip == client_ip
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="會話不存在或無權限訪問")
        
        # 獲取會話的所有消息
        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.timestamp).all()
        
        # 格式化消息
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            })
        
        return {
            "session_id": session_id,
            "messages": formatted_messages,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chat history: {str(e)}")
        raise HTTPException(status_code=500, detail="獲取聊天歷史失敗")

@app.get("/api/user-profile/{session_id}")
async def get_user_profile(
    session_id: str,
    client_ip: str = Depends(get_client_ip),
    db: Session = Depends(get_db),
    integrated: bool = False  # 新增參數，是否返回整合畫像
):
    """獲取用戶畫像信息"""
    try:
        # 驗證會話是否屬於當前客戶端
        session = db.query(ChatSession).filter(
            ChatSession.session_id == session_id,
            ChatSession.ip_address == client_ip
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="會話不存在或無權限訪問")
        
        # 初始化Agent並獲取用戶畫像（使用資料庫版本）
        agent = Agent(session_id=session_id)
        
        if integrated:
            # 返回跨session整合的用戶畫像
            user_profile = await agent.user_profile_service.get_cross_session_profile(db, client_ip)
        else:
            # 返回當前session的用戶畫像
            user_profile = await agent.user_profile_service.get_user_profile(db, session_id)
        
        if not user_profile:
            # 如果沒有用戶畫像，創建一個基本的
            user_profile = {
                "visit_count": 1,
                "interests": [],
                "activity_preferences": {},
                "personality_traits": {},
                "satisfaction_scores": [],
                "last_activity": datetime.now().isoformat()
            }
        
        return user_profile
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        raise HTTPException(status_code=500, detail="獲取用戶畫像失敗")

@app.get("/api/user-profile-integrated")
async def get_integrated_user_profile(
    client_ip: str = Depends(get_client_ip),
    db: Session = Depends(get_db)
):
    """獲取整合的跨session用戶畫像"""
    try:
        # 創建臨時Agent來使用服務
        from services.user_profile_db_service import UserProfileDBService
        profile_service = UserProfileDBService()
        
        # 獲取跨session整合的用戶畫像
        user_profile = await profile_service.get_cross_session_profile(db, client_ip)
        
        return user_profile
        
    except Exception as e:
        logger.error(f"Error getting integrated user profile: {str(e)}")
        raise HTTPException(status_code=500, detail="獲取整合用戶畫像失敗")

class ConversationStageRequest(BaseModel):
    chat_history: List[Dict[str, Any]]

@app.post("/api/conversation-stage")
async def analyze_conversation_stage(request: ConversationStageRequest):
    """分析對話階段"""
    try:
        # 初始化Agent並分析對話階段
        agent = Agent()
        stage = await agent.conversation_stage_service.determine_conversation_stage(
            request.chat_history
        )
        
        return {
            "stage": stage,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error analyzing conversation stage: {str(e)}")
        raise HTTPException(status_code=500, detail="分析對話階段失敗")

@app.get("/api/analysis/monthly")
async def get_monthly_analysis():
    """
    Get monthly analysis of events for the past 6 months
    """
    logger.info("Processing monthly analysis request")
    try:
        result = await analyze_monthly_trends()
        logger.info("Monthly analysis completed successfully")
        return result
    except Exception as e:
        logger.error(f"Error in monthly analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis/geographic")
async def get_geographic_analysis():
    """
    Get geographic distribution analysis
    """
    logger.info("Processing geographic analysis request")
    try:
        result = await analyze_geographic_distribution()
        logger.info("Geographic analysis completed successfully")
        return result
    except Exception as e:
        logger.error(f"Error in geographic analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/recommend")
async def get_recommendations(preferences: EventSearchParams):
    """
    Get event recommendations based on preferences
    """
    logger.info(f"Processing event recommendations request with preferences: {preferences.dict()}")
    try:
        result = await recommend_events(preferences.dict(exclude_none=True))
        logger.info("Event recommendations generated successfully")
        return result
    except Exception as e:
        logger.error(f"Error generating recommendations: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis/report")
async def get_analysis_report():
    """
    Generate a comprehensive analysis report
    """
    logger.info("Generating comprehensive analysis report")
    try:
        # Get data for analysis
        logger.info("Retrieving monthly trends data...")
        monthly_data = await analyze_monthly_trends()
        logger.info("Retrieving geographic distribution data...")
        geo_data = await analyze_geographic_distribution()
        
        # Combine data for report
        analysis_data = {
            "monthly_trends": monthly_data["data"],
            "geographic_distribution": geo_data["data"]
        }
        
        # Generate report
        logger.info("Generating report from combined data...")
        report = generate_analysis_report(analysis_data)
        logger.info("Analysis report generated successfully")
        
        return {
            "report": report,
            "visualizations": {
                "monthly": monthly_data["visualization"],
                "geographic": geo_data["visualization"]
            }
        }
    except Exception as e:
        logger.error(f"Error generating analysis report: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/activity/histogram")
async def get_activity_histogram(request: Request):
    """
    Get activity histogram statistics
    """
    try:
        raw_params = dict(request.query_params)
        if "from" in raw_params:
            raw_params["from_"] = raw_params.pop("from")
        
        # 用手動方式構建 Pydantic 模型
        params = ActivityHistogramParams(**raw_params)
        params_dict = params.dict(exclude_none=True, by_alias=True)
        
        # Make request to EventGO API using global client
        response = await http_client.get(
            f"{EVENTGO_API_BASE}/activity/histogram",
            params=params_dict
        )

        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/activity/date-histogram")
async def get_activity_date_histogram(request: Request):
    """
    Get activity date histogram statistics
    """
    try:

        raw_params = dict(request.query_params)
        if "from" in raw_params:
            raw_params["from_"] = raw_params.pop("from")
        
        # 用手動方式構建 Pydantic 模型
        params = ActivityDateHistogramParams(**raw_params)
        params_dict = params.dict(exclude_none=True, by_alias=True)
        
        # Make request to EventGO API using global client
        logger.info(f"Making request to EventGO API with params: {params_dict}")
        response = await http_client.get(
            f"{EVENTGO_API_BASE}/activity/date-histogram",
            params=params_dict
        )
        
        logger.info(f"EventGO API response status: {response.status_code}")
        logger.info(f"EventGO API response headers: {response.headers}")
        logger.info(f"EventGO API response text: {response.text}")
        
        if response.status_code != 200:
            logger.error(f"EventGO API error: {response.text}")
            raise HTTPException(status_code=response.status_code, detail=response.text)
        
        data = response.json()
        logger.info(f"Received date histogram data: {data}")
        return data
    except Exception as e:
        logger.error(f"Error getting activity date histogram: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    logger.info("Starting Event Chatbot API server...")
    uvicorn.run(app, host="0.0.0.0", port=8000) 