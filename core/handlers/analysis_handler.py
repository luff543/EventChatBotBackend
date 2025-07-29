from typing import Dict, Any, List, Optional
import httpx
from .base_handler import BaseHandler
from utils.logger import logger

class AnalysisHandler(BaseHandler):
    """分析處理器，處理各種數據分析功能"""
    
    async def handle_analyze_trends(
        self, 
        message: str, 
        chat_history: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """處理趨勢分析請求"""
        try:
            # 從訊息中提取分析參數
            analysis_params = await self._extract_analysis_params(message)
            
            # 調用趨勢分析API
            from llm_handler import analyze_monthly_trends
            
            category = analysis_params.get("category", "")
            if not category:
                # 嘗試從訊息中提取類別
                category = await self._extract_category_from_message(message)
            
            result = await analyze_monthly_trends(category)
            
            # 構建回應
            response_message = f"## 📈 {category}活動趨勢分析\n\n"
            response_message += result.get("message", "")
            
            if result.get("trend_analysis"):
                trend = result["trend_analysis"]
                response_message += f"\n\n### 📊 統計摘要\n"
                response_message += f"- 總活動數：{trend.get('total_events', 0)} 個\n"
                response_message += f"- 平均每月：{trend.get('average_events', 0):.1f} 個\n"
                response_message += f"- 分析期間：{trend.get('time_period', {}).get('start', '')} 至 {trend.get('time_period', {}).get('end', '')}\n"
                
                if trend.get('max_month'):
                    response_message += f"- 活動最多月份：{trend['max_month'].get('month', '')} ({trend['max_month'].get('count', 0)} 個)\n"
                if trend.get('min_month'):
                    response_message += f"- 活動最少月份：{trend['min_month'].get('month', '')} ({trend['min_month'].get('count', 0)} 個)\n"
            
            return self._create_success_response(
                response_message,
                "analyze_trends",
                analysis_data=result,
                visualization=result.get("visualization")
            )
            
        except Exception as e:
            logger.error(f"Error handling analyze trends: {str(e)}", exc_info=True)
            return self._create_error_response(
                "抱歉，分析活動趨勢時發生錯誤，請稍後再試。",
                "analyze_trends",
                str(e)
            )

    async def handle_analyze_statistics(
        self, 
        message: str, 
        chat_history: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """處理統計分析請求"""
        try:
            # 從訊息中提取統計類型
            stats_type = await self._extract_statistics_type(message)
            analysis_params = await self._extract_analysis_params(message)
            
            # 根據統計類型調用不同的API
            if stats_type == "geographic" or "地區" in message or "城市" in message:
                return await self.handle_analyze_geographic(message, chat_history)
            elif stats_type == "category" or "類別" in message or "分類" in message:
                return await self._handle_category_statistics(message, analysis_params)
            else:
                # 默認提供綜合統計
                return await self._handle_comprehensive_statistics(message, analysis_params)
                
        except Exception as e:
            logger.error(f"Error handling analyze statistics: {str(e)}", exc_info=True)
            return self._create_error_response(
                "抱歉，分析活動統計時發生錯誤，請稍後再試。",
                "analyze_statistics",
                str(e)
            )

    async def handle_analyze_geographic(
        self, 
        message: str, 
        chat_history: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """處理地理分析請求"""
        try:
            # 從訊息中提取分析參數
            analysis_params = await self._extract_analysis_params(message)
            
            # 調用地理分析API
            from llm_handler import analyze_geographic_distribution
            
            category = analysis_params.get("category", "")
            if not category:
                category = await self._extract_category_from_message(message)
            
            result = await analyze_geographic_distribution(category)
            
            # 構建回應
            response_message = f"## 🗺️ {category}活動地理分布分析\n\n"
            
            if result.get("data"):
                response_message += "### 📊 各城市活動數量分布\n\n"
                
                # 排序並顯示前10個城市
                sorted_data = sorted(result["data"], key=lambda x: x.get("value", 0), reverse=True)
                for i, item in enumerate(sorted_data[:10], 1):
                    city = item.get("key", "未知城市")
                    count = item.get("value", 0)
                    response_message += f"{i}. **{city}**：{count} 個活動\n"
                
                # 計算總計
                total_events = sum(item.get("value", 0) for item in result["data"])
                response_message += f"\n**總計**：{total_events} 個活動分布在 {len(result['data'])} 個城市\n"
            else:
                response_message += "目前沒有找到相關的地理分布數據。"
            
            return self._create_success_response(
                response_message,
                "analyze_geographic",
                analysis_data=result,
                visualization=result.get("visualization")
            )
            
        except Exception as e:
            logger.error(f"Error handling analyze geographic: {str(e)}", exc_info=True)
            return self._create_error_response(
                "抱歉，分析地理分布時發生錯誤，請稍後再試。",
                "analyze_geographic",
                str(e)
            )

    async def handle_generate_report(
        self, 
        message: str, 
        chat_history: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """處理報告生成請求"""
        try:
            # 調用報告生成API
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(f"http://127.0.0.1:8000/api/analysis/report")
                result = response.json()
            
            # 構建回應
            response_message = "## 📋 活動分析報告\n\n"
            response_message += result.get("report", "報告生成中...")
            
            return self._create_success_response(
                response_message,
                "generate_report",
                report_data=result,
                visualizations=result.get("visualizations", {})
            )
            
        except Exception as e:
            logger.error(f"Error handling generate report: {str(e)}", exc_info=True)
            return self._create_error_response(
                "抱歉，生成分析報告時發生錯誤，請稍後再試。",
                "generate_report",
                str(e)
            )

    async def _handle_category_statistics(
        self, 
        message: str, 
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """處理類別統計"""
        try:
            # 調用類別統計API
            api_params = {
                "group": "category",
                "sort": "value",
                "asc": False,
                "num": 20
            }
            api_params.update(params)
            
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(
                    "http://127.0.0.1:8000/api/activity/histogram",
                    params=api_params
                )
                result = response.json()
            
            # 構建回應
            response_message = "## 📊 活動類別統計分析\n\n"
            
            if result:
                response_message += "### 各類別活動數量排行\n\n"
                for i, item in enumerate(result[:10], 1):
                    category = item.get("key", "未知類別")
                    count = item.get("value", 0)
                    response_message += f"{i}. **{category}**：{count} 個活動\n"
                
                total_events = sum(item.get("value", 0) for item in result)
                response_message += f"\n**總計**：{total_events} 個活動分布在 {len(result)} 個類別\n"
            
            return self._create_success_response(
                response_message,
                "analyze_statistics",
                statistics_data=result
            )
            
        except Exception as e:
            logger.error(f"Error in category statistics: {str(e)}")
            return self._create_error_response(
                "抱歉，分析類別統計時發生錯誤。",
                "analyze_statistics",
                str(e)
            )

    async def _handle_comprehensive_statistics(
        self, 
        message: str, 
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """處理綜合統計"""
        try:
            # 同時獲取地理和類別統計
            geographic_result = await self.handle_analyze_geographic(message, [])
            category_result = await self._handle_category_statistics(message, params)
            
            response_message = "## 📈 綜合活動統計分析\n\n"
            response_message += "### 🗺️ 地理分布概況\n"
            if geographic_result.get("success"):
                response_message += geographic_result["message"].split("### 📊 各城市活動數量分布")[1] if "### 📊 各城市活動數量分布" in geographic_result["message"] else "暫無地理分布數據\n"
            
            response_message += "\n### 🏷️ 類別分布概況\n"
            if category_result.get("success"):
                response_message += category_result["message"].split("### 各類別活動數量排行")[1] if "### 各類別活動數量排行" in category_result["message"] else "暫無類別分布數據\n"
            
            return self._create_success_response(
                response_message,
                "analyze_statistics",
                comprehensive_data={
                    "geographic": geographic_result.get("analysis_data"),
                    "category": category_result.get("statistics_data")
                }
            )
            
        except Exception as e:
            logger.error(f"Error in comprehensive statistics: {str(e)}")
            return self._create_error_response(
                "抱歉，分析綜合統計時發生錯誤。",
                "analyze_statistics",
                str(e)
            ) 