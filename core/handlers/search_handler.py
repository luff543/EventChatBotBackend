from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from .base_handler import BaseHandler
from tools.search_tools import SearchParamsExtractor, EventSearchService
from utils.logger import logger

class SearchHandler(BaseHandler):
    """搜尋處理器，處理活動搜尋和詳情查詢"""
    
    async def handle_search_events(
        self, 
        message: str, 
        chat_history: List[Dict[str, Any]] = None, 
        page: int = 1, 
        search_params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """處理活動搜尋"""
        try:
            # 提取搜尋參數，如果沒有提供則從訊息中提取
            if search_params:
                # 使用提供的搜尋參數，但可能需要從訊息中補充
                extracted_params = await SearchParamsExtractor.extract_search_params(message, search_params)
            else:
                # 從訊息中提取搜尋參數
                extracted_params = await SearchParamsExtractor.extract_search_params(message)
            
            # 設置分頁參數
            extracted_params['p'] = page
            
            # 執行搜尋
            result = await EventSearchService.search_events(extracted_params)
            logger.info(f"Search result structure: {type(result)}")
            
            # 獲取分頁信息
            pagination = result.get("pagination", {})
            logger.info(f"Pagination data: {pagination}")
            
            # 計算當前頁的活動數量
            current_page_count = len(result.get("events", []))
            logger.info(f"Current page count: {current_page_count}")
            
            # 構建回應
            response_parts = [
                f"## 搜尋結果\n",
                f"共找到 {pagination.get('total_events', 0)} 個活動，本頁顯示 {current_page_count} 個活動\n"
            ]
            
            # 添加搜尋條件
            formatted_params = self._format_search_params(extracted_params)
            
            # 添加活動列表
            if result.get("events"):
                response_parts.append("\n### 活動列表\n")
                for i, event in enumerate(result["events"], 1):
                    event_info = self._format_event_info(i, event)
                    response_parts.append(event_info)
            
            # 組合最終回應
            final_response = "\n".join(response_parts)
            
            # 添加搜尋條件到最終回應
            if formatted_params:
                final_response += "\n\n### 搜尋條件\n" + "\n".join(formatted_params)
            
            # 構建符合 main.py 期望的回應格式
            return self._create_success_response(
                final_response,
                "search_events",
                events=result,
                search_params=extracted_params,
                pagination=pagination
            )
            
        except Exception as e:
            logger.error(f"Error handling search events: {str(e)}", exc_info=True)
            return self._create_error_response(
                "抱歉，搜尋活動時發生錯誤，請稍後再試。",
                "search_events",
                str(e)
            )
    
    async def handle_get_event_details(
        self, 
        message: str, 
        chat_history: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """處理活動詳情請求"""
        try:
            # 從訊息中提取活動ID或名稱
            event_identifier = await self._extract_event_identifier(message)
            
            if not event_identifier:
                return self._create_error_response(
                    "請提供具體的活動名稱或ID，我將為您查詢詳細資訊。",
                    "get_event_details"
                )
            
            # 搜尋特定活動
            search_params = {
                "query": event_identifier,
                "num": 1
            }
            
            from llm_handler import recommend_events
            result = await recommend_events(search_params)
            
            if result.get("events") and len(result["events"]) > 0:
                event = result["events"][0]
                
                response_message = f"## 🎪 活動詳情\n\n"
                response_message += f"### {event.get('name', '未知活動')}\n\n"
                response_message += self._format_event_details(event)
                
                return self._create_success_response(
                    response_message,
                    "get_event_details",
                    event_details=event
                )
            else:
                return self._create_error_response(
                    f"抱歉，沒有找到與「{event_identifier}」相關的活動詳情。請嘗試使用其他關鍵字搜尋。",
                    "get_event_details"
                )
            
        except Exception as e:
            logger.error(f"Error handling get event details: {str(e)}", exc_info=True)
            return self._create_error_response(
                "抱歉，查詢活動詳情時發生錯誤，請稍後再試。",
                "get_event_details",
                str(e)
            )
    
    async def direct_search_events(
        self,
        page: int = 1,
        search_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """直接搜尋活動，不需要處理訊息"""
        try:
            logger.info(f"Direct search events - page: {page}, search_params: {search_params}")
            
            # 如果沒有提供搜尋參數，使用默認參數
            if not search_params:
                search_params = {
                    'type': 'Web Post',
                    'timeKey': 'start_time',
                    'sort': 'start_time',
                    'asc': True,
                    'from': int(datetime.now().timestamp() * 1000)
                }
            
            # 設置分頁參數
            search_params['p'] = page
            search_params['num'] = search_params.get('num', 5)
            
            logger.info(f"Final search params for direct search: {search_params}")
            
            # 直接調用 recommend_events
            from llm_handler import recommend_events
            result = await recommend_events(search_params)
            logger.info(f"Direct search result structure: {type(result)}")
            
            # 獲取分頁信息
            pagination = result.get("pagination", {})
            logger.info(f"Direct search pagination data: {pagination}")
            
            # 如果沒有分頁數據，創建默認的分頁數據
            if not pagination or pagination.get('total_events', 0) == 0:
                events_count = len(result.get("events", []))
                total_events = result.get("count", events_count)
                pagination = {
                    'current_page': page,
                    'events_per_page': search_params.get('num', 5),
                    'total_events': total_events,
                    'total_pages': max(1, (total_events + search_params.get('num', 5) - 1) // search_params.get('num', 5)),
                    'current_page_count': events_count
                }
                logger.info(f"Created default pagination data for direct search: {pagination}")
            
            # 計算當前頁的活動數量
            current_page_count = len(result.get("events", []))
            logger.info(f"Direct search current page count: {current_page_count}")
            
            # 構建詳細回應
            response_parts = [
                f"## 搜尋結果\n",
                f"共找到 {pagination.get('total_events', 0)} 個活動，本頁顯示 {current_page_count} 個活動\n"
            ]
            
            # 添加搜尋條件
            formatted_params = self._format_search_params(search_params)
            
            # 添加活動列表
            if result.get("events"):
                response_parts.append("\n### 活動列表\n")
                for i, event in enumerate(result["events"], 1):
                    event_info = self._format_event_info(i, event)
                    response_parts.append(event_info)
            
            # 組合最終回應
            final_response = "\n".join(response_parts)
            
            # 添加搜尋條件到最終回應
            if formatted_params:
                final_response += "\n\n### 搜尋條件\n" + "\n".join(formatted_params)
            
            # 構建回應格式
            return self._create_success_response(
                final_response,
                "search_events",
                events=result,
                search_params=search_params,
                pagination=pagination
            )
            
        except Exception as e:
            logger.error(f"Error in direct search events: {str(e)}", exc_info=True)
            return self._create_error_response(
                "抱歉，搜尋活動時發生錯誤，請稍後再試。",
                "search_events",
                str(e)
            )
    
    def _format_search_params(self, params: Dict[str, Any]) -> List[str]:
        """格式化搜尋參數"""
        formatted_params = []
        
        if 'query' in params:
            formatted_params.append(f"🔍 關鍵字：{params['query']}")
        if 'city' in params:
            formatted_params.append(f"📍 城市：{params['city']}")
        if 'category' in params:
            formatted_params.append(f"🏷️ 類別：{params['category']}")
        if 'from' in params:
            try:
                from_date = datetime.fromtimestamp(params['from'] / 1000)
                formatted_params.append(f"📅 開始日期：{from_date.strftime('%Y-%m-%d')}")
            except Exception as e:
                logger.error(f"Error formatting from date: {str(e)}")
        if 'to' in params:
            try:
                to_date = datetime.fromtimestamp(params['to'] / 1000)
                formatted_params.append(f"📅 結束日期：{to_date.strftime('%Y-%m-%d')}")
            except Exception as e:
                logger.error(f"Error formatting to date: {str(e)}")
        if 'type' in params:
            formatted_params.append(f"📋 活動類型：{params['type']}")
        if 'sort' in params:
            sort_display = {
                '_score': '相關度',
                'start_time': '開始時間',
                'end_time': '結束時間',
                'updated_time': '更新時間',
                'distance': '距離'
            }.get(params['sort'], params['sort'])
            formatted_params.append(f"↕️ 排序方式：{sort_display}")
        if 'asc' in params:
            formatted_params.append(f"↕️ 排序方向：{'升序' if params['asc'] else '降序'}")
        
        return formatted_params
    
    def _format_event_info(self, index: int, event: Dict[str, Any]) -> str:
        """格式化單個活動信息"""
        try:
            event_parts = []
            
            # 活動名稱和連結
            title = event.get("name", "")
            link = event.get("link", "")
            if title and link:
                event_parts.append(f"{index}. [{title}]({link})")
            elif title:
                event_parts.append(f"{index}. {title}")
            
            # 日期時間
            if event.get("start_time"):
                try:
                    start_date = datetime.fromtimestamp(event['start_time'] / 1000)
                    date_str = f"   - 活動日期：{start_date.strftime('%Y-%m-%d')}"
                    if event.get("end_time"):
                        end_date = datetime.fromtimestamp(event['end_time'] / 1000)
                        date_str += f" 至 {end_date.strftime('%Y-%m-%d')}"
                    event_parts.append(date_str)
                except Exception as e:
                    logger.error(f"Error formatting event date: {str(e)}")
            
            # 地點
            has_location = False
            if event.get("location"):
                location = event["location"]
                if event.get("gps", {}).get("lat") and event.get("gps", {}).get("lon"):
                    location_str = f"   - 活動地點：[{location}](https://www.google.com/maps/place/{event['gps']['lat']},{event['gps']['lon']})"
                    has_location = True
                else:
                    location_str = f"   - 活動地點：{location}"
                    has_location = True
                event_parts.append(location_str)
            
            # 城市和區域
            has_city = False
            if event.get("venue", {}).get("city"):
                event_parts.append(f"   - 城市：{event['venue']['city']}")
                has_city = True
            if event.get("venue", {}).get("area"):
                event_parts.append(f"   - 區域：{event['venue']['area']}")
                has_city = True
            
            # 如果沒有地點和城市信息，添加提示
            if not has_location and not has_city:
                event_parts.append("   - 未提供地點與城市區域資訊")
            
            # 類別
            if event.get("category"):
                event_parts.append(f"   - 類別：{event['category']}")
            elif event.get("category_list") and len(event["category_list"]) > 0:
                event_parts.append(f"   - 類別：{', '.join(event['category_list'])}")
            else:
                event_parts.append("   - 類別：無")
            
            # 年齡層
            if event.get("age_group"):
                event_parts.append(f"   - 適合年齡：{event['age_group']}")
            elif event.get("age_group_list") and len(event["age_group_list"]) > 0:
                event_parts.append(f"   - 適合年齡：{', '.join(event['age_group_list'])}")
            else:
                event_parts.append("   - 適合年齡：未提供")
            
            return "\n".join(event_parts)
            
        except Exception as e:
            logger.error(f"Error formatting event {index}: {str(e)}")
            return f"{index}. 活動信息格式化錯誤"
    
    def _format_event_details(self, event: Dict[str, Any]) -> str:
        """格式化活動詳情"""
        details = []
        
        if event.get('start_time'):
            start_date = datetime.fromtimestamp(event['start_time'] / 1000)
            details.append(f"📅 **開始時間**：{start_date.strftime('%Y-%m-%d %H:%M')}")
        
        if event.get('end_time'):
            end_date = datetime.fromtimestamp(event['end_time'] / 1000)
            details.append(f"📅 **結束時間**：{end_date.strftime('%Y-%m-%d %H:%M')}")
        
        if event.get('location'):
            details.append(f"📍 **地點**：{event['location']}")
        
        if event.get('venue', {}).get('city'):
            details.append(f"🏙️ **城市**：{event['venue']['city']}")
        
        if event.get('category'):
            details.append(f"🏷️ **類別**：{event['category']}")
        
        if event.get('age_group'):
            details.append(f"👥 **適合年齡**：{event['age_group']}")
        
        if event.get('link'):
            details.append(f"🔗 **詳細資訊**：[點擊查看]({event['link']})")
        
        return "\n".join(details) 