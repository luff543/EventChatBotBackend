from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from utils.logger import logger

class BaseHandler:
    """基礎處理器類，提供共同的工具方法和介面"""
    
    def __init__(self, agent_instance):
        """
        初始化處理器
        
        Args:
            agent_instance: Agent實例，用於訪問Agent的屬性和方法
        """
        self.agent = agent_instance
        self.context = agent_instance.context
        self.session_id = agent_instance.session_id
        self.user_profile_service = agent_instance.user_profile_service
        self.proactive_service = agent_instance.proactive_service
    
    async def _extract_analysis_params(self, message: str) -> Dict[str, Any]:
        """從訊息中提取分析參數"""
        params = {}
        
        # 提取時間範圍
        if "本月" in message:
            now = datetime.now()
            start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            params["from"] = int(start_of_month.timestamp() * 1000)
            params["to"] = int(now.timestamp() * 1000)
        elif "上個月" in message:
            from datetime import timedelta
            now = datetime.now()
            start_of_last_month = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
            end_of_last_month = now.replace(day=1) - timedelta(days=1)
            params["from"] = int(start_of_last_month.timestamp() * 1000)
            params["to"] = int(end_of_last_month.timestamp() * 1000)
        elif "半年" in message or "6個月" in message:
            from datetime import timedelta
            now = datetime.now()
            six_months_ago = now - timedelta(days=180)
            params["from"] = int(six_months_ago.timestamp() * 1000)
            params["to"] = int(now.timestamp() * 1000)
        
        # 提取城市
        cities = ["台北", "臺北", "新北", "桃園", "台中", "臺中", "台南", "臺南", "高雄", "基隆", "新竹", "苗栗", "彰化", "南投", "雲林", "嘉義", "屏東", "宜蘭", "花蓮", "台東", "臺東", "澎湖", "金門", "連江"]
        for city in cities:
            if city in message:
                params["city"] = city
                break
        
        return params

    async def _extract_category_from_message(self, message: str) -> str:
        """從訊息中提取活動類別"""
        categories = {
            "運動": ["運動", "健身", "瑜伽", "跑步", "球類", "游泳"],
            "音樂": ["音樂", "演唱會", "音樂會", "演出", "表演"],
            "藝術": ["藝術", "展覽", "美術", "畫展", "藝文"],
            "美食": ["美食", "餐廳", "料理", "烹飪", "品酒"],
            "學習": ["學習", "講座", "課程", "工作坊", "研習"],
            "親子": ["親子", "兒童", "家庭", "小孩"],
            "戶外": ["戶外", "野餐", "露營", "踏青", "自然"]
        }
        
        for category, keywords in categories.items():
            if any(keyword in message for keyword in keywords):
                return category
        
        return "全部"

    async def _extract_statistics_type(self, message: str) -> str:
        """從訊息中提取統計類型"""
        if any(keyword in message for keyword in ["地區", "城市", "地理", "分布"]):
            return "geographic"
        elif any(keyword in message for keyword in ["類別", "分類", "種類"]):
            return "category"
        elif any(keyword in message for keyword in ["時間", "月份", "趨勢"]):
            return "temporal"
        else:
            return "general"

    async def _extract_event_identifier(self, message: str) -> str:
        """從訊息中提取活動識別符"""
        import re
        
        # 移除常見的問句詞彙
        cleaned_message = re.sub(r'(請問|查詢|詳情|資訊|活動|的)', '', message)
        cleaned_message = cleaned_message.strip()
        
        return cleaned_message if len(cleaned_message) > 2 else ""

    def _create_success_response(self, message: str, intent: str, **kwargs) -> Dict[str, Any]:
        """創建成功回應"""
        response = {
            "message": message,
            "intent": intent,
            "success": True
        }
        response.update(kwargs)
        return response

    def _create_error_response(self, message: str, intent: str, error: str = None) -> Dict[str, Any]:
        """創建錯誤回應"""
        response = {
            "message": message,
            "intent": intent,
            "success": False
        }
        if error:
            response["error"] = error
        return response 