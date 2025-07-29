from typing import Dict, Any
import json
from datetime import datetime, timedelta
from openai import OpenAI
import re
from utils.config import OPENAI_API_KEY, DEFAULT_EVENTS_PER_PAGE
from utils.logger import logger

client = OpenAI(api_key=OPENAI_API_KEY)

class SearchParamsExtractor:
    """搜尋參數提取器"""
    
    @staticmethod
    async def extract_search_params(message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        從用戶消息中提取搜尋參數
        context: 已存在的搜尋參數（例如從前端傳來的排序參數）
        """
        logger.info(f"Extracting search parameters from message: {message}")
        logger.info(f"Existing parameters: {context}")
        
        # Get today's date in different formats for the prompt
        today = datetime.now()
        today_str = today.strftime("%Y-%m-%d")
        today_timestamp = int(today.timestamp() * 1000)  # Convert to milliseconds
        
        # Calculate next month timestamp
        next_month = today.replace(day=1) + timedelta(days=32)
        next_month = next_month.replace(day=1)
        next_month_timestamp = int(next_month.timestamp() * 1000)
        next_month_end = next_month.replace(day=1) + timedelta(days=32)
        next_month_end = next_month_end.replace(day=1) - timedelta(days=1)
        next_month_end_timestamp = int(next_month_end.timestamp() * 1000)
        
        # Define valid cities
        valid_cities = [
            "臺北", "新北", "臺中", "臺南", "高雄", "桃園", "基隆", "新竹", "嘉義",
            "苗栗", "彰化", "南投", "雲林", "屏東", "宜蘭", "花蓮", "臺東", "澎湖",
            "金門", "連江"
        ]
        
        # Define valid sort keys
        valid_sort_keys = [
            "_score", "start_time", "end_time", "updated_time", "distance"
        ]
        
        prompt = f"""請從以下用戶訊息中提取活動搜尋參數，並以JSON格式返回：
        用戶訊息：{message}
        
        今天的日期是：{today_str}（時間戳：{today_timestamp}）
        下個月開始：{next_month.strftime('%Y-%m-%d')}（時間戳：{next_month_timestamp}）
        下個月結束：{next_month_end.strftime('%Y-%m-%d')}（時間戳：{next_month_end_timestamp}）
        
        請確保返回的是有效的JSON格式，包含以下參數（如果存在）：
        - query: 搜尋關鍵字
        - city: 城市（必須是以下城市之一或多個，用逗號分隔：{', '.join(valid_cities)}）
        - from: 開始時間（毫秒時間戳，例如：{today_timestamp}）
        - to: 結束時間（毫秒時間戳）
        - type: 活動類型（預設為 "Web Post"）
        - timeKey: 時間過濾條件（預設為 "start_time"）
        - sort: 排序欄位（預設為 "_score"，可選值：{', '.join(valid_sort_keys)}）
        - asc: 排序方向（預設為 true，表示升序）
        
        重要提取規則：
        
        關鍵字查詢：
        - 將用戶提到的活動類型、興趣等作為 query 參數
        - 例如："展覽" -> query: "展覽"
        - 例如："音樂活動" -> query: "音樂"
        - 例如："親子展覽" -> query: "親子 展覽"
        - 多個關鍵字用空格分隔
        
        時間處理規則：
        1. "下個月" -> from: {next_month_timestamp}, to: {next_month_end_timestamp}
        2. "這個月" -> from: {int(today.replace(day=1).timestamp() * 1000)}, to: {today_timestamp}
        3. "今天" -> from: {today_timestamp}, to: {today_timestamp + 86400000}
        4. "明天" -> from: {today_timestamp + 86400000}, to: {today_timestamp + 172800000}
        5. "這週" -> from: {today_timestamp}, to: {today_timestamp + 604800000}
        6. "下週" -> from: {today_timestamp + 604800000}, to: {today_timestamp + 1209600000}
        7. 如果沒有明確時間，預設 from: {today_timestamp}
        
        城市處理規則：
        1. 如果提到"台灣"或"全台"，則包含所有城市
        2. 如果提到多個城市，用逗號分隔
        3. 城市名稱必須完全匹配以下列表：{', '.join(valid_cities)}
        
        排序規則：
        1. 如果包含關鍵字搜索（query），使用 "_score" 和降序（asc: false）
        2. 如果提到"最新"，使用 "start_time" 和降序（asc: false）
        3. 如果提到"即將開始"，使用 "start_time" 和升序（asc: true）
        4. 默認使用 "start_time" 和升序（asc: true）
        
        請直接返回JSON格式，不要添加任何markdown標記或其他文字。
        """
        
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "你是一個專業的活動搜尋助手，請從用戶訊息中提取搜尋參數，並以JSON格式返回。請確保返回的是純JSON格式，不要添加任何markdown標記或其他文字。必須正確識別活動類別和時間範圍。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # 降低溫度以提高一致性
                max_tokens=500
            )
            
            content = response.choices[0].message.content.strip()
            logger.info(f"Raw response from GPT-4: {content}")
            
            # Clean the response content
            cleaned_content = content
            cleaned_content = re.sub(r'^```json\s*', '', cleaned_content)
            cleaned_content = re.sub(r'^```\s*', '', cleaned_content)
            cleaned_content = re.sub(r'\s*```$', '', cleaned_content)
            cleaned_content = cleaned_content.strip()
            
            logger.info(f"Cleaned content: {cleaned_content}")
            
            try:
                # Try to parse the content as JSON
                params = json.loads(cleaned_content)
                logger.info(f"Successfully parsed JSON: {params}")
                
                # Validate and process city parameter
                if 'city' in params:
                    cities = params['city'].split(',')
                    valid_cities_list = []
                    for city in cities:
                        city = city.strip()
                        if city in valid_cities:
                            valid_cities_list.append(city)
                    if valid_cities_list:
                        params['city'] = ','.join(valid_cities_list)
                    else:
                        del params['city']
                
                # 處理排序參數的優先級
                if context:
                    # 如果前端指定了要保留排序參數
                    if context.get('preserve_sort'):
                        params['sort'] = context['sort']
                        logger.info(f"Using frontend sort parameter: {context['sort']}")
                    # 如果前端指定了要保留排序方向
                    if context.get('preserve_asc'):
                        params['asc'] = context['asc']
                        logger.info(f"Using frontend asc parameter: {context['asc']}")
                else:
                    # 根據搜索條件設置默認排序
                    if 'query' in params:
                        # 如果有關鍵字搜索，按相關度排序
                        params['sort'] = '_score'
                        params['asc'] = False
                    elif 'sort' not in params:
                        # 默認按開始時間升序
                        params['sort'] = 'start_time'
                        params['asc'] = True
                
                # 如果前端沒有指定要保留排序參數，但提供了排序參數，則使用前端的排序參數
                if context and not context.get('preserve_sort'):
                    if 'sort' in context:
                        params['sort'] = context['sort']
                        logger.info(f"Using frontend sort parameter without preserve flag: {context['sort']}")
                    if 'asc' in context:
                        params['asc'] = context['asc']
                        logger.info(f"Using frontend asc parameter without preserve flag: {context['asc']}")
                
                # Add default values if not present
                if 'type' not in params:
                    params['type'] = 'Web Post'
                if 'timeKey' not in params:
                    params['timeKey'] = 'start_time'
                if 'from' not in params:
                    params['from'] = today_timestamp
                if 'num' not in params:
                    params['num'] = DEFAULT_EVENTS_PER_PAGE
                if 'p' not in params:
                    params['p'] = 1
                
                # 驗證必要參數
                SearchParamsExtractor._validate_search_params(params, message)
                
                logger.info(f"Final search parameters: {params}")
                return params
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON: {str(e)}")
                logger.error(f"Content that failed to parse: {cleaned_content}")
                
                # 使用規則基礎的回退機制
                fallback_params = SearchParamsExtractor._extract_params_with_rules(message, today_timestamp, next_month_timestamp, next_month_end_timestamp)
                logger.info(f"Using rule-based fallback parameters: {fallback_params}")
                return fallback_params
                
        except Exception as e:
            logger.error(f"Error extracting search parameters: {str(e)}", exc_info=True)
            
            # 使用規則基礎的回退機制
            fallback_params = SearchParamsExtractor._extract_params_with_rules(message, today_timestamp, next_month_timestamp, next_month_end_timestamp)
            logger.info(f"Using rule-based fallback parameters due to error: {fallback_params}")
            return fallback_params

    @staticmethod
    def _extract_params_with_rules(message: str, today_timestamp: int, next_month_timestamp: int, next_month_end_timestamp: int) -> Dict[str, Any]:
        """
        使用規則基礎的方法提取搜索參數（回退機制）
        """
        params = {
            'type': 'Web Post',
            'timeKey': 'start_time',
            'sort': 'start_time',
            'asc': True,
            'from': today_timestamp,
            'num': DEFAULT_EVENTS_PER_PAGE,
            'p': 1
        }
        
        message_lower = message.lower()
        
        # 提取時間範圍
        if '下個月' in message or '下月' in message:
            params['from'] = next_month_timestamp
            params['to'] = next_month_end_timestamp
        elif '這個月' in message or '本月' in message:
            # 這個月的開始到今天
            this_month_start = datetime.now().replace(day=1)
            params['from'] = int(this_month_start.timestamp() * 1000)
            params['to'] = today_timestamp
        elif '今天' in message:
            params['from'] = today_timestamp
            params['to'] = today_timestamp + 86400000
        elif '明天' in message:
            params['from'] = today_timestamp + 86400000
            params['to'] = today_timestamp + 172800000
        elif '這週' in message or '本週' in message:
            params['from'] = today_timestamp
            params['to'] = today_timestamp + 604800000
        elif '下週' in message:
            params['from'] = today_timestamp + 604800000
            params['to'] = today_timestamp + 1209600000
        
        # 提取城市
        valid_cities = [
            "臺北", "新北", "臺中", "臺南", "高雄", "桃園", "基隆", "新竹", "嘉義",
            "苗栗", "彰化", "南投", "雲林", "屏東", "宜蘭", "花蓮", "臺東", "澎湖",
            "金門", "連江"
        ]
        
        for city in valid_cities:
            if city in message or city.replace('臺', '台') in message:
                params['city'] = city
                break
        
        logger.info(f"Rule-based extraction result: {params}")
        return params

    @staticmethod
    def _validate_search_params(params: Dict[str, Any], original_message: str):
        """
        驗證搜索參數的完整性和正確性
        """
        logger.info(f"Validating search parameters: {params}")
        
        # 檢查是否缺少重要參數
        missing_params = []
        
        # 對於包含時間範圍的訊息，檢查是否正確提取了時間參數
        time_keywords = ['下個月', '下月', '這個月', '本月', '今天', '明天', '這週', '本週', '下週']
        has_time_keyword = any(keyword in original_message for keyword in time_keywords)
        if has_time_keyword and 'to' not in params:
            missing_params.append("to (time range detected in message)")
        
        if missing_params:
            logger.warning(f"Missing important parameters: {missing_params}")
            logger.warning(f"Original message: {original_message}")
            logger.warning(f"Extracted parameters: {params}")

class EventSearchService:
    """活動搜尋服務"""
    
    @staticmethod
    async def search_events(params: Dict[str, Any]) -> Dict[str, Any]:
        """
        執行活動搜尋
        """
        try:
            from llm_handler import recommend_events
            return await recommend_events(params)
        except Exception as e:
            logger.error(f"Error searching events: {str(e)}", exc_info=True)
            raise 