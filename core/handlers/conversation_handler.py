from typing import Dict, Any, List, Optional
from .base_handler import BaseHandler
from utils.logger import logger

class ConversationHandler(BaseHandler):
    """對話處理器，處理一般對話、問候、幫助等功能"""
    
    async def handle_greeting(
        self, 
        message: str, 
        chat_history: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """處理問候語"""
        try:
            # 根據時間和用戶歷史提供個性化問候
            greeting_response = await self._generate_personalized_greeting(message, chat_history)
            
            return self._create_success_response(
                greeting_response,
                "greeting"
            )
            
        except Exception as e:
            logger.error(f"Error handling greeting: {str(e)}", exc_info=True)
            return self._create_error_response(
                "您好！歡迎使用活動聊天機器人，我可以幫您搜尋和推薦活動。",
                "greeting",
                str(e)
            )

    async def handle_help(
        self, 
        message: str, 
        chat_history: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """處理幫助請求"""
        try:
            help_message = self._generate_help_message()
            
            return self._create_success_response(
                help_message,
                "help"
            )
            
        except Exception as e:
            logger.error(f"Error handling help: {str(e)}", exc_info=True)
            return self._create_error_response(
                "抱歉，獲取幫助信息時發生錯誤。",
                "help",
                str(e)
            )

    async def handle_general_conversation(
        self, 
        message: str, 
        chat_history: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """處理一般對話"""
        try:
            # 分析訊息內容，提供相關回應
            response_message = await self._generate_conversational_response(message, chat_history)
            
            return self._create_success_response(
                response_message,
                "general_conversation"
            )
            
        except Exception as e:
            logger.error(f"Error handling general conversation: {str(e)}", exc_info=True)
            return self._create_error_response(
                "我理解您的訊息，但可能需要更具體的活動相關問題才能更好地幫助您。",
                "general_conversation",
                str(e)
            )

    async def handle_goodbye(
        self, 
        message: str, 
        chat_history: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """處理告別語"""
        try:
            goodbye_response = await self._generate_goodbye_response(message, chat_history)
            
            return self._create_success_response(
                goodbye_response,
                "goodbye"
            )
            
        except Exception as e:
            logger.error(f"Error handling goodbye: {str(e)}", exc_info=True)
            return self._create_error_response(
                "謝謝您的使用，期待下次為您服務！",
                "goodbye",
                str(e)
            )

    async def _generate_personalized_greeting(
        self, 
        message: str, 
        chat_history: List[Dict[str, Any]] = None
    ) -> str:
        """生成個性化問候語"""
        from datetime import datetime
        
        current_hour = datetime.now().hour
        
        # 根據時間選擇問候語
        if 5 <= current_hour < 12:
            time_greeting = "早安"
        elif 12 <= current_hour < 18:
            time_greeting = "午安"
        elif 18 <= current_hour < 22:
            time_greeting = "晚安"
        else:
            time_greeting = "您好"
        
        # 檢查是否為回訪用戶
        is_returning_user = chat_history and len(chat_history) > 1
        
        if is_returning_user:
            greeting = f"{time_greeting}！歡迎回來！我是您的活動助手，很高興再次為您服務。"
        else:
            greeting = f"{time_greeting}！歡迎使用活動聊天機器人！我是您的專屬活動助手。"
        
        greeting += "\n\n我可以幫您：\n"
        greeting += "🔍 搜尋各種活動\n"
        greeting += "🎯 提供個人化推薦\n"
        greeting += "📊 分析活動趨勢\n"
        greeting += "📍 查詢地區活動分布\n"
        greeting += "❓ 回答活動相關問題\n\n"
        greeting += "請告訴我您想要什麼樣的活動，或者直接說「幫助」來了解更多功能！"
        
        return greeting

    def _generate_help_message(self) -> str:
        """生成幫助訊息"""
        help_message = "## 🤖 活動聊天機器人使用指南\n\n"
        help_message += "### 🔍 搜尋活動\n"
        help_message += "- 「搜尋台北的音樂活動」\n"
        help_message += "- 「找本週末的戶外活動」\n"
        help_message += "- 「查詢親子活動」\n\n"
        
        help_message += "### 🎯 個人化推薦\n"
        help_message += "- 「推薦適合我的活動」\n"
        help_message += "- 「根據我的興趣推薦」\n\n"
        
        help_message += "### 📊 數據分析\n"
        help_message += "- 「分析音樂活動趨勢」\n"
        help_message += "- 「台北活動統計」\n"
        help_message += "- 「活動地理分布」\n\n"
        
        help_message += "### 📍 活動詳情\n"
        help_message += "- 「查詢[活動名稱]詳情」\n"
        help_message += "- 「活動比較」\n\n"
        
        help_message += "### 💡 小貼士\n"
        help_message += "- 可以指定城市、時間、類別等條件\n"
        help_message += "- 支援自然語言查詢\n"
        help_message += "- 系統會學習您的偏好提供更好的推薦\n\n"
        
        help_message += "有任何問題都可以直接問我！"
        
        return help_message

    async def _generate_conversational_response(
        self, 
        message: str, 
        chat_history: List[Dict[str, Any]] = None
    ) -> str:
        """生成對話回應"""
        # 分析訊息內容，提供相關的活動建議
        message_lower = message.lower()
        
        # 檢查是否包含活動相關關鍵字
        activity_keywords = [
            "活動", "演出", "展覽", "音樂", "藝術", "運動", "美食", 
            "學習", "親子", "戶外", "室內", "週末", "假日"
        ]
        
        has_activity_keywords = any(keyword in message for keyword in activity_keywords)
        
        if has_activity_keywords:
            response = "我注意到您提到了活動相關的內容！"
            response += "我可以幫您搜尋相關活動，或者提供更具體的建議。\n\n"
            response += "您可以告訴我：\n"
            response += "- 想要什麼類型的活動\n"
            response += "- 偏好的地點或時間\n"
            response += "- 其他特殊需求\n\n"
            response += "這樣我就能為您找到最合適的活動！"
        else:
            response = "謝謝您的訊息！雖然我主要專精於活動相關服務，"
            response += "但我很樂意與您聊天。\n\n"
            response += "如果您對活動有任何需求，隨時可以告訴我：\n"
            response += "🎪 想參加什麼活動\n"
            response += "📅 什麼時候有空\n"
            response += "📍 想在哪裡參加\n\n"
            response += "我會盡力為您找到最棒的活動體驗！"
        
        return response

    async def _generate_goodbye_response(
        self, 
        message: str, 
        chat_history: List[Dict[str, Any]] = None
    ) -> str:
        """生成告別回應"""
        goodbye_messages = [
            "謝謝您的使用！希望我的建議對您有幫助。",
            "很高興為您服務！期待下次再為您推薦精彩活動。",
            "再見！祝您參加活動愉快，有美好的體驗！",
            "感謝您的信任！隨時歡迎回來尋找更多有趣的活動。"
        ]
        
        # 根據對話歷史選擇合適的告別語
        if chat_history and len(chat_history) > 5:
            # 長對話，表示感謝
            goodbye = goodbye_messages[0]
        else:
            # 短對話，鼓勵再次使用
            goodbye = goodbye_messages[1]
        
        goodbye += "\n\n🌟 記得關注我們的最新活動推薦！"
        
        return goodbye 