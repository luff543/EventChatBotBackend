from typing import Dict, Any, List, Optional
from datetime import datetime
from .base_handler import BaseHandler
from utils.logger import logger

class RecommendationHandler(BaseHandler):
    """推薦處理器，處理個人化推薦和活動比較功能"""
    
    async def handle_get_recommendations(
        self, 
        message: str, 
        chat_history: List[Dict[str, Any]] = None, 
        user_profile: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """處理個人化推薦請求"""
        try:
            # 結合用戶畫像和訊息內容生成推薦參數
            recommendation_params = await self._build_recommendation_params(message, user_profile)
            
            # 調用推薦API
            from llm_handler import recommend_events
            result = await recommend_events(recommendation_params)
            
            # 構建回應
            response_message = "## 🎯 為您推薦的活動\n\n"
            
            if result.get("events"):
                response_message += f"根據您的偏好，為您找到 {len(result['events'])} 個推薦活動：\n\n"
                
                for i, event in enumerate(result["events"][:5], 1):  # 只顯示前5個
                    response_message += f"### {i}. {event.get('name', '未知活動')}\n"
                    if event.get('start_time'):
                        start_date = datetime.fromtimestamp(event['start_time'] / 1000)
                        response_message += f"📅 **時間**：{start_date.strftime('%Y-%m-%d %H:%M')}\n"
                    if event.get('location'):
                        response_message += f"📍 **地點**：{event['location']}\n"
                    if event.get('category'):
                        response_message += f"🏷️ **類別**：{event['category']}\n"
                    if event.get('link'):
                        response_message += f"🔗 **詳情**：[點擊查看]({event['link']})\n"
                    response_message += "\n"
            else:
                response_message += "抱歉，目前沒有找到符合您偏好的活動，請嘗試調整搜尋條件。"
            
            return self._create_success_response(
                response_message,
                "get_recommendations",
                events=result,
                recommendation_params=recommendation_params
            )
            
        except Exception as e:
            logger.error(f"Error handling get recommendations: {str(e)}", exc_info=True)
            return self._create_error_response(
                "抱歉，獲取推薦活動時發生錯誤，請稍後再試。",
                "get_recommendations",
                str(e)
            )

    async def handle_compare_events(
        self, 
        message: str, 
        chat_history: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """處理活動比較請求"""
        try:
            # 提取比較參數
            comparison_params = await self._extract_comparison_params(message)
            
            # 根據比較類型執行不同的比較邏輯
            if comparison_params.get("type") == "geographic":
                return await self._compare_geographic_events(comparison_params)
            elif comparison_params.get("type") == "temporal":
                return await self._compare_temporal_events(comparison_params)
            elif comparison_params.get("type") == "category":
                return await self._compare_category_events(comparison_params)
            else:
                return await self._general_event_comparison(comparison_params)
                
        except Exception as e:
            logger.error(f"Error handling compare events: {str(e)}", exc_info=True)
            return self._create_error_response(
                "抱歉，比較活動時發生錯誤，請稍後再試。",
                "compare_events",
                str(e)
            )

    async def _build_recommendation_params(
        self, 
        message: str, 
        user_profile: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """構建推薦參數"""
        params = {
            "num": 10,
            "sort": "start_time",
            "asc": True
        }
        
        # 從用戶畫像中提取偏好
        if user_profile:
            interests = user_profile.get("interests", [])
            if interests:
                # 取第一個興趣作為類別
                first_interest = interests[0]
                if isinstance(first_interest, dict):
                    params["category"] = first_interest.get("interest", "")
                else:
                    params["category"] = str(first_interest)
        
        # 從訊息中提取額外參數
        analysis_params = await self._extract_analysis_params(message)
        params.update(analysis_params)
        
        # 設置時間範圍為未來活動
        if "from" not in params:
            params["from"] = int(datetime.now().timestamp() * 1000)
        
        return params

    async def _extract_comparison_params(self, message: str) -> Dict[str, Any]:
        """提取比較參數"""
        params = {"type": "general"}
        
        if any(keyword in message for keyword in ["地區", "城市"]):
            params["type"] = "geographic"
        elif any(keyword in message for keyword in ["時間", "月份", "年份"]):
            params["type"] = "temporal"
        elif any(keyword in message for keyword in ["類別", "種類"]):
            params["type"] = "category"
        
        return params

    async def _compare_geographic_events(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """比較不同地區的活動"""
        try:
            # 實現地理比較邏輯
            # 這裡可以調用地理分析API來獲取不同城市的數據進行比較
            response_message = "## 🗺️ 地理活動比較分析\n\n"
            response_message += "地理比較功能正在開發中，將提供以下功能：\n"
            response_message += "- 不同城市活動數量對比\n"
            response_message += "- 活動類型分布差異\n"
            response_message += "- 熱門活動地點排行\n"
            response_message += "- 地區活動特色分析\n"
            
            return self._create_success_response(
                response_message,
                "compare_events",
                comparison_type="geographic"
            )
            
        except Exception as e:
            logger.error(f"Error in geographic comparison: {str(e)}")
            return self._create_error_response(
                "地理比較分析時發生錯誤。",
                "compare_events",
                str(e)
            )

    async def _compare_temporal_events(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """比較不同時間的活動"""
        try:
            # 實現時間比較邏輯
            response_message = "## 📅 時間活動比較分析\n\n"
            response_message += "時間比較功能正在開發中，將提供以下功能：\n"
            response_message += "- 不同月份活動數量對比\n"
            response_message += "- 季節性活動趨勢分析\n"
            response_message += "- 週末vs平日活動分布\n"
            response_message += "- 節慶期間活動特色\n"
            
            return self._create_success_response(
                response_message,
                "compare_events",
                comparison_type="temporal"
            )
            
        except Exception as e:
            logger.error(f"Error in temporal comparison: {str(e)}")
            return self._create_error_response(
                "時間比較分析時發生錯誤。",
                "compare_events",
                str(e)
            )

    async def _compare_category_events(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """比較不同類別的活動"""
        try:
            # 實現類別比較邏輯
            response_message = "## 🏷️ 類別活動比較分析\n\n"
            response_message += "類別比較功能正在開發中，將提供以下功能：\n"
            response_message += "- 不同活動類型數量對比\n"
            response_message += "- 各類別活動熱門程度\n"
            response_message += "- 類別間參與者特徵分析\n"
            response_message += "- 跨類別活動推薦\n"
            
            return self._create_success_response(
                response_message,
                "compare_events",
                comparison_type="category"
            )
            
        except Exception as e:
            logger.error(f"Error in category comparison: {str(e)}")
            return self._create_error_response(
                "類別比較分析時發生錯誤。",
                "compare_events",
                str(e)
            )

    async def _general_event_comparison(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """一般活動比較"""
        try:
            # 實現一般比較邏輯
            response_message = "## 📊 綜合活動比較分析\n\n"
            response_message += "綜合比較功能正在開發中，將提供以下功能：\n"
            response_message += "- 多維度活動對比分析\n"
            response_message += "- 活動相似度計算\n"
            response_message += "- 個人化比較建議\n"
            response_message += "- 活動選擇決策支援\n"
            
            return self._create_success_response(
                response_message,
                "compare_events",
                comparison_type="general"
            )
            
        except Exception as e:
            logger.error(f"Error in general comparison: {str(e)}")
            return self._create_error_response(
                "綜合比較分析時發生錯誤。",
                "compare_events",
                str(e)
            ) 