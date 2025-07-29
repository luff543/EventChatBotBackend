import os
from typing import List, Dict, Any, Optional
import json
from datetime import datetime, timedelta
import httpx
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
import re
from openai import OpenAI
from utils.config import OPENAI_API_KEY, EVENTGO_API_BASE
from dotenv import load_dotenv
from utils.logger import logger

# Load environment variables from .env file
load_dotenv(override=True)

# Initialize OpenAI client
logger.info("Initializing OpenAI client...")
client = OpenAI(api_key=OPENAI_API_KEY)
logger.info("OpenAI client initialized successfully")

# Create HTTP client with SSL verification disabled for development
logger.info("Creating HTTP client...")
http_client = httpx.AsyncClient(verify=False)
logger.info("HTTP client created successfully")

SYSTEM_PROMPT = """你是一個專業的活動分析助手，可以幫助用戶查詢和分析活動資訊。
你可以：
1. 搜尋特定類型的活動
2. 分析活動的時間分布
3. 分析活動的地理分布
4. 提供活動推薦
5. 生成活動分析報告

當用戶詢問活動相關問題時，你需要：
1. 理解用戶的偏好和需求
2. 提取關鍵資訊（地點、主題、日期等）
3. 使用結構化查詢來搜尋活動
4. 提供個性化的活動推薦

請根據用戶的需求，使用適當的API來獲取和分析數據。"""

async def extract_search_params(message: str, existing_params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Extract search parameters from natural language message using GPT-4
    existing_params: 已存在的搜尋參數（例如從前端傳來的排序參數）
    """
    logger.info(f"Extracting search parameters from message: {message}")
    logger.info(f"Existing parameters: {existing_params}")
    
    # Get today's date in different formats for the prompt
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    today_timestamp = int(today.timestamp() * 1000)  # Convert to milliseconds
    
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
    
    請確保返回的是有效的JSON格式，包含以下參數（如果存在）：
    - query: 搜尋關鍵字
    - city: 城市（必須是以下城市之一或多個，用逗號分隔：{', '.join(valid_cities)}）
    - category: 活動類別
    - from: 開始時間（毫秒時間戳，例如：{today_timestamp}）
    - to: 結束時間（毫秒時間戳）
    - type: 活動類型（預設為 "Web Post"）
    - timeKey: 時間過濾條件（預設為 "start_time"）
    - sort: 排序欄位（預設為 "_score"，可選值：{', '.join(valid_sort_keys)}）
    - asc: 排序方向（預設為 true，表示升序）
    
    城市處理規則：
    1. 如果提到"台灣"或"全台"，則包含所有城市
    2. 如果提到多個城市，用逗號分隔
    3. 城市名稱必須完全匹配以下列表：{', '.join(valid_cities)}
    4. 如果提到的城市不在列表中，請忽略該城市
    
    時間處理規則：
    1. 如果沒有提到任何時間，預設使用今天的時間戳作為開始時間（from: {today_timestamp}）
    2. 如果提到"今天"，使用今天的時間戳
    3. 如果提到"明天"，使用今天時間戳 + 86400000（一天的毫秒數）
    4. 如果提到"下週"，使用今天時間戳 + 604800000（一週的毫秒數）
    5. 如果提到具體日期，請轉換為對應的時間戳
    6. 如果提到"過去半年"或"最近半年"，設置：
       - from: 今天時間戳 - 15552000000（半年的毫秒數）
       - to: 今天時間戳
    7. 如果提到"過去一個月"或"最近一個月"，設置：
       - from: 今天時間戳 - 2592000000（一個月的毫秒數）
       - to: 今天時間戳
    8. 如果提到"過去一週"或"最近一週"，設置：
       - from: 今天時間戳 - 604800000（一週的毫秒數）
       - to: 今天時間戳
    9. 如果提到"過去一年"或"最近一年"，設置：
       - from: 今天時間戳 - 31536000000（一年的毫秒數）
       - to: 今天時間戳
    10. 如果提到"上個月"，設置：
        - from: 今天時間戳 - 5184000000（兩個月的毫秒數）
        - to: 今天時間戳 - 2592000000（一個月的毫秒數）
    11. 如果提到"上週"，設置：
        - from: 今天時間戳 - 1209600000（兩週的毫秒數）
        - to: 今天時間戳 - 604800000（一週的毫秒數）
    
    排序規則：
    1. 如果包含關鍵字搜索（query），使用 "_score" 和降序（asc: false）
    2. 如果提到"最新"，使用 "start_time" 和降序（asc: false）
    3. 如果提到"即將開始"，使用 "start_time" 和升序（asc: true）
    4. 如果提到"即將結束"，使用 "end_time" 和升序（asc: true）
    5. 如果提到"最近更新"，使用 "updated_time" 和降序（asc: false）
    6. 如果提到"距離最近"，使用 "distance" 和升序（asc: true）
    7. 如果沒有指定排序，預設使用 "start_time" 和升序（asc: true）
    
    請直接返回JSON格式，不要添加任何markdown標記或其他文字。
    例如，如果用戶說"找台北的運動活動"，應該返回：
    {{"city": "臺北", "category": "運動", "type": "Web Post", "timeKey": "start_time", "from": {today_timestamp}, "sort": "_score", "asc": false}}
    
    例如，如果用戶說"找過去半年的展覽活動"，應該返回：
    {{"category": "展覽", "type": "Web Post", "timeKey": "start_time", "from": {today_timestamp - 15552000000}, "to": {today_timestamp}, "sort": "start_time", "asc": true}}
    
    例如，如果用戶說"找上個月的音樂活動"，應該返回：
    {{"category": "音樂", "type": "Web Post", "timeKey": "start_time", "from": {today_timestamp - 5184000000}, "to": {today_timestamp - 2592000000}, "sort": "start_time", "asc": true}}
    
    例如，如果用戶說"找最近一週的展覽"，應該返回：
    {{"category": "展覽", "type": "Web Post", "timeKey": "start_time", "from": {today_timestamp - 604800000}, "to": {today_timestamp}, "sort": "start_time", "asc": true}}
    
    請注意：
    1. 必須返回有效的JSON格式
    2. 如果某個參數不存在，請不要包含在JSON中
    3. 不要添加任何額外的文字說明或markdown標記
    4. 不要使用```json或```等markdown標記
    5. type 參數預設值為 "Web Post"
    6. timeKey 參數預設值為 "start_time"
    7. city 參數必須完全匹配給定的城市列表
    8. 如果沒有提到時間，必須包含 from 參數並設置為今天的時間戳
    9. 如果有關鍵字搜索，sort 參數應設為 "_score"，asc 參數應設為 false
    10. 如果沒有指定排序，sort 參數應設為 "start_time"，asc 參數應設為 true
    11. 時間範圍查詢（如"過去半年"）必須同時設置 from 和 to 參數
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "你是一個專業的活動搜尋助手，請從用戶訊息中提取搜尋參數，並以JSON格式返回。請確保返回的是純JSON格式，不要添加任何markdown標記或其他文字。type 參數預設值為 'Web Post'。如果沒有提到時間，必須包含 from 參數並設置為今天的時間戳。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
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
            # Try to parse the cleaned content as JSON
            params = json.loads(cleaned_content)
            
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
            if existing_params:
                # 如果前端指定了要保留排序參數
                if existing_params.get('preserve_sort'):
                    params['sort'] = existing_params['sort']
                    logger.info(f"Using frontend sort parameter: {existing_params['sort']}")
                # 如果前端指定了要保留排序方向
                if existing_params.get('preserve_asc'):
                    params['asc'] = existing_params['asc']
                    logger.info(f"Using frontend asc parameter: {existing_params['asc']}")
            else:
                # 根據搜索條件設置默認排序
                if 'query' in params:
                    # 如果有關鍵字搜索，按相關度排序
                    params['sort'] = '_score'
                    params['asc'] = False
                elif 'sort' not in params:
                    # 默認按開始時間降序
                    params['sort'] = 'start_time'
                    params['asc'] = False
            
            # 如果前端沒有指定要保留排序參數，但提供了排序參數，則使用前端的排序參數
            if existing_params and not existing_params.get('preserve_sort'):
                if 'sort' in existing_params:
                    params['sort'] = existing_params['sort']
                    logger.info(f"Using frontend sort parameter without preserve flag: {existing_params['sort']}")
                if 'asc' in existing_params:
                    params['asc'] = existing_params['asc']
                    logger.info(f"Using frontend asc parameter without preserve flag: {existing_params['asc']}")
            
            # Add default values if not present
            if 'type' not in params:
                params['type'] = 'Web Post'
            if 'from' not in params:
                params['from'] = today_timestamp
            
            logger.info(f"Successfully parsed JSON with priority handling: {params}")
            return params
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {str(e)}")
            # Try to extract JSON using regex as a fallback
            json_match = re.search(r'\{.*\}', cleaned_content)
            if json_match:
                try:
                    params = json.loads(json_match.group())
                    # 處理排序參數的優先級
                    if existing_params:
                        # 如果前端指定了要保留排序參數
                        if existing_params.get('preserve_sort'):
                            params['sort'] = existing_params['sort']
                            logger.info(f"Using frontend sort parameter: {existing_params['sort']}")
                        # 如果前端指定了要保留排序方向
                        if existing_params.get('preserve_asc'):
                            params['asc'] = existing_params['asc']
                            logger.info(f"Using frontend asc parameter: {existing_params['asc']}")
                    else:
                        # 根據搜索條件設置默認排序
                        if 'query' in params:
                            # 如果有關鍵字搜索，按相關度排序
                            params['sort'] = '_score'
                            params['asc'] = False
                        elif 'sort' not in params:
                            # 默認按開始時間降序
                            params['sort'] = 'start_time'
                            params['asc'] = False
                    
                    # Add default values if not present
                    if 'type' not in params:
                        params['type'] = 'Web Post'
                    if 'from' not in params:
                        params['from'] = today_timestamp
                    
                    logger.info(f"Successfully extracted and parsed JSON with priority handling: {params}")
                    return params
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse extracted JSON: {str(e)}")
                    return {
                        'type': 'Web Post',
                        'sort': 'start_time',
                        'asc': False,
                        'from': today_timestamp
                    }
            else:
                logger.error("No JSON found in response")
                return {
                    'type': 'Web Post',
                    'sort': 'start_time',
                    'asc': False,
                    'from': today_timestamp
                }
    except Exception as e:
        logger.error(f"Error extracting search parameters: {str(e)}", exc_info=True)
        return {
            'type': 'Web Post',
            'sort': 'start_time',
            'asc': False,
            'from': today_timestamp
        }

async def process_chat_message(message: str, chat_history: List[Dict[str, str]], page: int = 1, search_params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Process chat message using OpenAI GPT-4 and handle event search
    """
    logger.info(f"Processing chat message: {message}")
    logger.info(f"Search params from frontend: {search_params}")
    
    # Handle None chat_history
    if chat_history is None:
        chat_history = []
    logger.info(f"Chat history length: {len(chat_history)}")
    logger.info(f"Current page: {page}")

    # Prepare messages for OpenAI
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *chat_history,
        {"role": "user", "content": message}
    ]

    try:
        # Get response from OpenAI
        logger.info("Getting response from OpenAI...")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        response_content = response.choices[0].message.content
        logger.info("Received response from OpenAI")
        
        # Check if the message is about event search
        if any(keyword in message.lower() for keyword in ["找", "搜尋", "推薦", "活動"]):
            logger.info("Message is about event search, extracting parameters...")
            # Extract search parameters with existing params
            logger.info(f"Frontend search parameters: {search_params}")
            extracted_params = await extract_search_params(message, search_params)
            logger.info(f"Extracted search parameters: {extracted_params}")
            
            if extracted_params:
                # Add p parameter to search params (EventGO API uses 'p' for pagination)
                extracted_params['p'] = page
                logger.info(f"Search parameters with page: {extracted_params}")
                
                logger.info("Searching for events with parameters...")
                # Search for events
                events = await recommend_events(extracted_params)
                
                # Format search parameters for display
                formatted_params = []
                if 'query' in extracted_params:
                    formatted_params.append(f"🔍 關鍵字：{extracted_params['query']}")
                if 'city' in extracted_params:
                    formatted_params.append(f"📍 城市：{extracted_params['city']}")
                if 'category' in extracted_params:
                    formatted_params.append(f"🏷️ 類別：{extracted_params['category']}")
                if 'from' in extracted_params:
                    from_date = datetime.fromtimestamp(extracted_params['from'] / 1000)
                    formatted_params.append(f"📅 開始日期：{from_date.strftime('%Y-%m-%d')}")
                if 'to' in extracted_params:
                    to_date = datetime.fromtimestamp(extracted_params['to'] / 1000)
                    formatted_params.append(f"📅 結束日期：{to_date.strftime('%Y-%m-%d')}")
                if 'type' in extracted_params:
                    formatted_params.append(f"📋 活動類型：{extracted_params['type']}")
                if 'sort' in extracted_params:
                    sort_display = {
                        '_score': '相關度',
                        'start_time': '開始時間',
                        'end_time': '結束時間',
                        'updated_time': '更新時間',
                        'distance': '距離'
                    }.get(extracted_params['sort'], extracted_params['sort'])
                    formatted_params.append(f"↕️ 排序方式：{sort_display}")
                if 'asc' in extracted_params:
                    formatted_params.append(f"↕️ 排序方向：{'升序' if extracted_params['asc'] else '降序'}")
                if search_params and search_params.get('preserve_sort'):
                    formatted_params.append("↕️ 排序方式：使用前端指定的排序")
                if search_params and search_params.get('preserve_asc'):
                    formatted_params.append("↕️ 排序方向：使用前端指定的方向")
                
                # Generate personalized response
                logger.info("Generating personalized response...")
                prompt = f"""根據以下搜尋結果，生成一個自然的回應：
                搜尋參數：{json.dumps(extracted_params, ensure_ascii=False)}
                搜尋結果：{json.dumps(events, ensure_ascii=False)}
                
                請包含以下內容：
                1. 符合條件的活動數量（共找到 {events['pagination']['total_events']} 個活動，本頁顯示 {events['pagination']['current_page_count']} 個活動）
                2. 主要活動類型和地點
                3. 特別推薦的活動，每個活動請包含：
                   - 活動名稱
                   - 活動開始日期和結束日期（請將時間戳轉換為可讀的日期時間格式）
                   - 活動地點
                   - 城市（如果有）
                   - 區域（如果有）
                   - 類別（如果有）
                   - 活動來源連結
                
                注意事項：
                1. 日期時間格式請使用：YYYY-MM-DD
                2. 連結請確保是完整的URL，不要因為括號造成連結錯誤
                3. 如果活動沒有結束時間，只顯示開始時間
                4. 活動地點顯示規則：
                   - 如果活動有GPS座標（latitude和longitude），請使用以下格式：
                     [地點名稱](https://www.google.com/maps/place/{{latitude}},{{longitude}})
                     例如：如果活動的latitude是25.0150627，longitude是121.2188074，則連結應該是：
                     [台北市立體育館](https://www.google.com/maps/place/25.0150627,121.2188074)
                   - 如果活動沒有GPS座標，直接顯示地點名稱，不要添加任何連結
                     例如：台北市立體育館
                5. 城市、區域和類別請分別單獨顯示，格式為：
                   城市：台北市
                   區域：信義區
                   類別：運動
                6. 如果某項信息不存在，請不要顯示該項
                7. 在回應開頭必須顯示總活動數和當前頁顯示的活動數，格式為：
                   "共找到 {events['pagination']['total_events']} 個活動，本頁顯示 {events['pagination']['current_page_count']} 個活動"
                
                請以markdown格式返回，確保連結可以正常點擊。
                """
                
                recommendation_response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "你是一個專業的活動推薦助手，請根據搜尋結果生成詳細的活動推薦回應。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )
                
                # Add formatted search parameters to the response
                formatted_response = recommendation_response.choices[0].message.content
                if formatted_params:
                    formatted_response += "\n\n### 搜尋條件\n" + "\n".join(formatted_params)
                
                logger.info("Generated personalized response")
                logger.info(f"Pagination data in response: {json.dumps(events['pagination'], ensure_ascii=False, indent=2)}")
                
                response_data = {
                    "message": formatted_response,
                    "events": events,
                    "search_params": extracted_params,
                    "pagination": events['pagination']
                }
                
                return response_data
        
        return {
            "message": response_content,
            "events": None,
            "search_params": None,
            "pagination": None
        }
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}", exc_info=True)
        raise

async def analyze_monthly_trends(category: str = "藝術") -> Dict[str, Any]:
    """
    Analyze monthly trends for a specific category using the date-histogram API
    """
    logger.info(f"Analyzing monthly trends for category: {category}")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)  # 過去6個月
    
    try:
        logger.info("Fetching data from EventGO date-histogram API...")
        response = await http_client.get(
            f"{EVENTGO_API_BASE}/activity/date-histogram",
            params={
                "interval": "1M",  # 月度間隔
                "group": "start_time",  # 按活動開始時間分組
                "timezone": "Asia/Taipei",  # 台北時區
                "from": int(start_date.timestamp() * 1000),  # 開始時間（毫秒）
                "to": int(end_date.timestamp() * 1000),  # 結束時間（毫秒）
                "category": category,  # 指定類別
            }
        )
        data = response.json()
        logger.info(f"Raw API response: {data}")
        
        # Handle empty data case
        if not data or not isinstance(data, list) or len(data) == 0:
            logger.warning(f"No data available for category '{category}' in the specified time period")
            return {
                "message": f"在過去半年內（{start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}）沒有找到任何{category}相關的活動數據。",
                "data": [],
                "visualization": None,
                "trend_analysis": {
                    "total_events": 0,
                    "average_events": 0,
                    "max_month": None,
                    "min_month": None,
                    "monthly_data": [],
                    "time_period": {
                        "start": start_date.strftime('%Y-%m-%d'),
                        "end": end_date.strftime('%Y-%m-%d')
                    }
                }
            }
        
        # Process data and create visualization
        logger.info("Creating visualization...")
        
        # 轉換API回應格式為DataFrame
        processed_data = []
        for item in data:
            # 將毫秒時間戳轉換為日期
            timestamp_ms = item.get('key', 0)
            date_obj = datetime.fromtimestamp(timestamp_ms / 1000)
            month_str = date_obj.strftime('%Y-%m')
            
            processed_data.append({
                'timestamp': timestamp_ms,
                'key_as_string': item.get('key_as_string', ''),
                'month': month_str,
                'count': item.get('value', 0)
            })
        
        df = pd.DataFrame(processed_data)
        logger.info(f"Processed DataFrame shape: {df.shape}")
        logger.info(f"DataFrame data: {df}")
        
        # 創建月度趨勢圖
        plt.figure(figsize=(12, 6))
        sns.barplot(data=df, x='month', y='count', palette='viridis')
        plt.xticks(rotation=45)
        plt.title(f'{category}活動月度分布趨勢', fontsize=16, pad=20)
        plt.xlabel('月份', fontsize=12)
        plt.ylabel('活動數量', fontsize=12)
        plt.grid(axis='y', alpha=0.3)
        
        # 添加數值標籤
        for i, v in enumerate(df['count']):
            plt.text(i, v + max(df['count']) * 0.01, str(int(v)), 
                    ha='center', va='bottom', fontsize=10)
        
        # Convert plot to base64
        img = io.BytesIO()
        plt.savefig(img, format='png', bbox_inches='tight', dpi=150)
        img.seek(0)
        plot_url = base64.b64encode(img.getvalue()).decode()
        plt.close()
        logger.info("Visualization created successfully")
        
        # Generate trend analysis
        total_events = int(df['count'].sum())
        average_events = float(df['count'].mean()) if not df.empty else 0
        
        max_month_data = None
        min_month_data = None
        if not df.empty:
            max_idx = df['count'].idxmax()
            min_idx = df['count'].idxmin()
            max_month_data = {
                'month': df.loc[max_idx, 'month'],
                'count': int(df.loc[max_idx, 'count'])
            }
            min_month_data = {
                'month': df.loc[min_idx, 'month'],
                'count': int(df.loc[min_idx, 'count'])
            }
        
        trend_analysis = {
            "total_events": total_events,
            "average_events": round(average_events, 1),
            "max_month": max_month_data,
            "min_month": min_month_data,
            "monthly_data": df[['month', 'count']].to_dict('records'),
            "time_period": {
                "start": start_date.strftime('%Y-%m-%d'),
                "end": end_date.strftime('%Y-%m-%d')
            }
        }
        
        # 生成趨勢分析文字
        trend_message = f"在過去半年內（{start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}）共找到 {total_events} 個{category}相關活動。"
        
        if max_month_data and min_month_data:
            trend_message += f" 其中 {max_month_data['month']} 活動最多（{max_month_data['count']}個），{min_month_data['month']} 活動最少（{min_month_data['count']}個）。"
        
        if average_events > 0:
            trend_message += f" 平均每月有 {average_events:.1f} 個活動。"
        
        return {
            "message": trend_message,
            "data": data,  # 原始API回應
            "visualization": plot_url,
            "trend_analysis": trend_analysis
        }
        
    except Exception as e:
        logger.error(f"Error analyzing monthly trends: {str(e)}", exc_info=True)
        return {
            "message": f"分析{category}活動趨勢時發生錯誤：{str(e)}",
            "data": [],
            "visualization": None,
            "trend_analysis": {
                "total_events": 0,
                "average_events": 0,
                "max_month": None,
                "min_month": None,
                "monthly_data": [],
                "time_period": {
                    "start": start_date.strftime('%Y-%m-%d'),
                    "end": end_date.strftime('%Y-%m-%d')
                }
            }
        }

async def analyze_geographic_distribution(category: str = "藝術") -> Dict[str, Any]:
    """
    Analyze geographic distribution of events
    """
    logger.info(f"Analyzing geographic distribution for category: {category}")
    try:
        logger.info("Fetching data from EventGO API...")
        
        # 構建API參數
        api_params = {
            "group": "city"
        }
        
        # 只有當 category 不是 "全部" 時才添加 category 參數
        if category and category != "全部":
            api_params["category"] = category
        
        response = await http_client.get(
            f"{EVENTGO_API_BASE}/activity/histogram",
            params=api_params
        )
        data = response.json()
        logger.info("Data fetched successfully")
        
        # Create visualization
        logger.info("Creating visualization...")
        df = pd.DataFrame(data)
        category_text = "全部" if category == "全部" or not category else category
        plt.figure(figsize=(12, 6))
        sns.barplot(data=df, x='key', y='value')
        plt.xticks(rotation=45)
        plt.title(f'{category_text} Events Distribution by City')
        
        # Convert plot to base64
        img = io.BytesIO()
        plt.savefig(img, format='png', bbox_inches='tight')
        img.seek(0)
        plot_url = base64.b64encode(img.getvalue()).decode()
        logger.info("Visualization created successfully")
        
        return {
            "data": data,
            "visualization": plot_url
        }
    except Exception as e:
        logger.error(f"Error analyzing geographic distribution: {str(e)}", exc_info=True)
        raise

async def recommend_events(preferences: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recommend events based on user preferences
    """
    logger.info(f"Recommending events with preferences: {preferences}")
    try:
        # 確保有必要的分頁參數
        if 'num' not in preferences:
            preferences['num'] = 5  # 每頁顯示5個活動
        
        # 確保有頁碼參數
        if 'p' not in preferences:
            preferences['p'] = 1
        
        logger.info(f"Final API parameters: {preferences}")
        
        logger.info("Fetching events from EventGO API...")
        response = await http_client.get(
            f"{EVENTGO_API_BASE}/activity",
            params=preferences
        )
        data = response.json()
        logger.info(f"API Response status: {response.status_code}")
        logger.info(f"API Response data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
        
        # Get events and total count from API response
        events = data.get('events', [])
        total_events = data.get('count', 0)
        query_time = data.get('queryTime', 0)
        
        logger.info(f"Total events from API: {total_events}")
        logger.info(f"Number of events in response: {len(events)}")
        
        # 獲取分頁參數
        current_page = preferences.get('p', 1)
        events_per_page = preferences.get('num', 5)
        
        # 計算總頁數
        total_pages = max(1, (total_events + events_per_page - 1) // events_per_page)
        current_page_count = len(events)
        
        # Filter out unnecessary fields from each event
        filtered_events = []
        for event in events:
            # Create a copy of the event without heavy fields
            filtered_event = {k: v for k, v in event.items() if k not in ['description', 'highlight_description', 'imgs']}
            filtered_events.append(filtered_event)
        
        # Create pagination data
        pagination_data = {
            'current_page': current_page,
            'events_per_page': events_per_page,
            'total_events': total_events,
            'total_pages': total_pages,
            'current_page_count': current_page_count
        }
        
        logger.info(f"Created pagination data: {pagination_data}")
        
        # Create response with filtered events and pagination
        result = {
            'count': total_events,
            'queryTime': query_time,
            'events': filtered_events,
            'pagination': pagination_data
        }
        
        logger.info(f"Returning {len(filtered_events)} events for page {current_page}")
        return result
    except Exception as e:
        logger.error(f"Error recommending events: {str(e)}", exc_info=True)
        raise

def generate_analysis_report(data: Dict[str, Any]) -> str:
    """
    Generate a natural language analysis report
    """
    logger.info("Generating analysis report...")
    prompt = f"""請根據以下數據生成一份活動分析報告：
    {json.dumps(data, ensure_ascii=False, indent=2)}
    
    請包含以下內容：
    1. 活動總體趨勢
    2. 熱門地區分析
    3. 活動類型分布
    4. 建議和洞察
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "你是一個專業的活動分析師，請根據數據生成詳細的分析報告。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        report = response.choices[0].message.content
        logger.info("Analysis report generated successfully")
        return report
    except Exception as e:
        logger.error(f"Error generating analysis report: {str(e)}", exc_info=True)
        raise 