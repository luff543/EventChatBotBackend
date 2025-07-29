from typing import Dict, Any, List, Optional
import json
from datetime import datetime
from sqlalchemy.orm import Session

# 導入配置和日誌
from utils.config import OPENAI_API_KEY
from utils.logger import logger

# 導入核心模型
from core.models import ConversationContext, Tool

# 導入處理器
from core.handlers import (
    SearchHandler, 
    AnalysisHandler, 
    RecommendationHandler, 
    ConversationHandler
)

# 導入服務
from services.filter_service import ChatHistoryFilterService
from services.analysis_service import (
    IntentAnalysisService, 
    SentimentAnalysisService, 
    EntityExtractionService, 
    InterestAnalysisService
)
from services.proactive_questioning_service import ProactiveQuestioningService
from services.user_profile_db_service import UserProfileDBService
from tools.search_tools import SearchParamsExtractor, EventSearchService

class Agent:
    """簡化的智能代理核心類，具備主動式提問功能和資料庫支援"""
    
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id
        self.context = ConversationContext()
        self.tools = self._initialize_tools()
        self.search_params = None  # 儲存搜尋參數
        
        # 初始化主動式提問相關服務（使用資料庫版本）
        self.user_profile_service = UserProfileDBService()
        self.proactive_service = ProactiveQuestioningService()
        
        # 初始化處理器
        self.search_handler = SearchHandler(self)
        self.analysis_handler = AnalysisHandler(self)
        self.recommendation_handler = RecommendationHandler(self)
        self.conversation_handler = ConversationHandler(self)
        
        logger.info(f"Agent initialized successfully with session_id: {session_id}")
    
    def _initialize_tools(self) -> List[Tool]:
        """初始化工具列表"""
        return [
            Tool(
                name="search_events",
                description="搜尋活動",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "搜尋關鍵字"},
                        "city": {"type": "string", "description": "城市"},
                        "from": {"type": "integer", "description": "開始時間戳"},
                        "to": {"type": "integer", "description": "結束時間戳"}
                    }
                },
                category="search"
            ),
            Tool(
                name="analyze_intent",
                description="分析用戶意圖",
                parameters={
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "用戶訊息"}
                    }
                },
                category="analysis"
            )
        ]
    
    async def process_message(
        self, 
        message: str, 
        db: Session,
        chat_history: List[Dict[str, Any]] = None, 
        page: int = 1, 
        search_params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        處理用戶訊息的主要方法，整合主動式提問功能和資料庫支援
        """
        try:
            logger.info(f"Processing message: {message}")
            logger.info(f"Page: {page}, Search params: {search_params}")
            
            # 如果有搜尋參數，直接進行搜尋
            if search_params:
                logger.info("Search parameters provided, using direct search")
                self.search_params = search_params
                return await self.direct_search_events(page, search_params)
            
            # 更新對話上下文
            self.context.conversation_history = chat_history or []
            
            # 分析用戶畫像（使用資料庫）
            user_profile = await self.user_profile_service.analyze_user_from_conversation(
                db, self.session_id, chat_history
            )
            
            # 分析對話階段
            conversation_stage = await self.proactive_service.analyze_conversation_stage(
                chat_history or [], self.context.dict()
            )
            
            logger.info(f"Conversation stage: {conversation_stage}")
                
            # 分析用戶意圖
            intent = await IntentAnalysisService.analyze_user_intent(message, chat_history)
            self.context.user_intent = intent
            
            # 根據意圖使用對應的處理器處理訊息
            if intent == "search_events":
                response = await self.search_handler.handle_search_events(message, chat_history, page, search_params)
            elif intent == "greeting":
                response = await self.conversation_handler.handle_greeting(message, chat_history)
            elif intent == "goodbye":
                response = await self.conversation_handler.handle_goodbye(message, chat_history)
            elif intent == "help":
                response = await self.conversation_handler.handle_help(message, chat_history)
            elif intent == "analyze_trends":
                response = await self.analysis_handler.handle_analyze_trends(message, chat_history)
            elif intent == "analyze_statistics":
                response = await self.analysis_handler.handle_analyze_statistics(message, chat_history)
            elif intent == "get_recommendations":
                response = await self.recommendation_handler.handle_get_recommendations(message, chat_history, user_profile)
            elif intent == "compare_events":
                response = await self.recommendation_handler.handle_compare_events(message, chat_history)
            elif intent == "analyze_geographic":
                response = await self.analysis_handler.handle_analyze_geographic(message, chat_history)
            elif intent == "generate_report":
                response = await self.analysis_handler.handle_generate_report(message, chat_history)
            elif intent == "get_event_details":
                response = await self.search_handler.handle_get_event_details(message, chat_history)
            else:
                response = await self._handle_general_question(message, chat_history, user_profile, conversation_stage)
            
            # 檢查是否需要主動提問
            should_ask, reason = await self.proactive_service.should_ask_proactive_question(
                message, response.get("message", ""), self.context.dict()
            )
            
            if should_ask:
                logger.info(f"Adding proactive question. Reason: {reason}")
                proactive_questions = await self.proactive_service.generate_proactive_questions(
                    self.context.dict(), user_profile, conversation_stage
                )
                
                # 將主動式問題添加到回應中
                response = await self._enhance_response_with_proactive_questions(
                    response, proactive_questions
                )
            
            # 更新用戶畫像（基於這次互動）
            await self._update_user_profile_from_interaction(db, message, response, intent)
            
            # 獲取最新的用戶畫像並添加到回應中
            try:
                updated_profile = await self.user_profile_service.get_user_profile(db, self.session_id)
                if updated_profile:
                    response["user_profile_summary"] = {
                        "visit_count": updated_profile.get("visit_count", 1),
                        "interests": [
                            interest.get("interest") if isinstance(interest, dict) else interest 
                            for interest in updated_profile.get("interests", [])
                        ][:5],  # 只返回前5個興趣
                        "activity_preferences": updated_profile.get("activity_preferences", {}),
                        "personality_traits": updated_profile.get("personality_traits", {}),
                        "last_activity": updated_profile.get("last_activity"),
                        "total_interactions": updated_profile.get("total_interactions", 0)
                    }
                    response["conversation_stage"] = conversation_stage
            except Exception as profile_error:
                logger.error(f"Error getting updated user profile: {str(profile_error)}")
                
            return response
                
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            return {
                "message": "抱歉，處理您的訊息時發生錯誤，請稍後再試。",
                "intent": "error",
                "success": False
            }

    async def direct_search_events(
        self,
        page: int = 1,
        search_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """直接搜尋活動，不需要處理訊息"""
        return await self.search_handler.direct_search_events(page, search_params)

    async def _handle_general_question(
        self, 
        message: str, 
        chat_history: List[Dict[str, Any]] = None,
        user_profile: Dict[str, Any] = None,
        conversation_stage: str = "exploring"
    ) -> Dict[str, Any]:
        """處理一般問題，使用對話處理器"""
        return await self.conversation_handler.handle_general_conversation(message, chat_history)

    async def _enhance_response_with_proactive_questions(
        self, 
        original_response: Dict[str, Any], 
        proactive_questions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """增強回應，添加主動式問題"""
        try:
            enhanced_response = original_response.copy()
            
            if proactive_questions and proactive_questions.get("questions"):
                # 添加主動式問題到回應中
                enhanced_response["proactive_questions"] = proactive_questions
                
                # 在訊息末尾添加主動式問題
                original_message = enhanced_response.get("message", "")
                
                # 添加分隔線和主動式問題
                enhanced_response["message"] = original_message + "\n\n---\n\n"
                enhanced_response["message"] += "💡 **我還可以幫您：**\n\n"
                
                for i, question in enumerate(proactive_questions["questions"][:3], 1):
                    enhanced_response["message"] += f"{i}. {question}\n"
                
                # 添加後續建議
                if proactive_questions.get("follow_up_suggestions"):
                    enhanced_response["message"] += "\n🔍 **相關建議：**\n"
                    for suggestion in proactive_questions["follow_up_suggestions"][:2]:
                        enhanced_response["message"] += f"• {suggestion}\n"
            
            return enhanced_response
            
        except Exception as e:
            logger.error(f"Error enhancing response with proactive questions: {str(e)}")
            return original_response

    async def _update_user_profile_from_interaction(
        self, 
        db: Session,
        user_message: str, 
        agent_response: Dict[str, Any], 
        intent: str
    ):
        """從互動中更新用戶畫像"""
        try:
            # 提取用戶興趣
            interests = await self._extract_interests_from_message(user_message)
            
            if interests:
                # 更新用戶興趣到資料庫
                for interest in interests:
                    await self.user_profile_service.update_user_interest(
                        db, self.session_id, interest, confidence=0.7, source="conversation"
                    )
                logger.info(f"Updated user interests: {interests}")
            
            # 根據意圖更新活動偏好
            if intent == "search_events" and agent_response.get("search_params"):
                search_params = agent_response["search_params"]
                
                # 更新偏好地點
                if search_params.get("city"):
                    await self.user_profile_service.update_activity_preference(
                        db, self.session_id, "preferred_locations", [search_params["city"]]
                    )
                
                # 更新偏好類別
                if search_params.get("category"):
                    await self.user_profile_service.update_activity_preference(
                        db, self.session_id, "preferred_categories", [search_params["category"]]
                    )
            
            # 更新互動統計
            await self.user_profile_service.update_interaction_stats(db, self.session_id)
            
        except Exception as e:
            logger.error(f"Error updating user profile from interaction: {str(e)}")

    async def _extract_interests_from_message(self, message: str) -> List[str]:
        """從訊息中提取興趣"""
        try:
            activity_keywords = {
                "音樂": ["音樂", "演唱會", "音樂會", "演出", "表演", "歌手", "樂團"],
                "藝術": ["藝術", "展覽", "美術", "畫展", "藝文", "博物館", "畫廊"],
                "運動": ["運動", "健身", "瑜伽", "跑步", "球類", "游泳", "登山"],
                "美食": ["美食", "餐廳", "料理", "烹飪", "品酒", "咖啡", "甜點"],
                "學習": ["學習", "課程", "講座", "工作坊", "研習", "教學"],
                "親子": ["親子", "兒童", "家庭", "小孩", "孩子"],
                "戶外": ["戶外", "野餐", "露營", "踏青", "自然", "郊遊"],
                "社交": ["社交", "聚會", "交友", "派對", "聯誼"]
            }
            
            detected_interests = []
            message_lower = message.lower()
            
            for category, keywords in activity_keywords.items():
                if any(keyword in message_lower for keyword in keywords):
                    detected_interests.append(category)
            
            return detected_interests[:3]  # 最多返回3個興趣
            
        except Exception as e:
            logger.error(f"Error extracting interests from message: {str(e)}")
            return [] 