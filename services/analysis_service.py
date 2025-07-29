from typing import Dict, Any, List
import json
from openai import OpenAI
from openai.types.chat import ChatCompletion
import openai
from utils.config import OPENAI_API_KEY
from utils.logger import logger
from services.filter_service import ChatHistoryFilterService

client = OpenAI(api_key=OPENAI_API_KEY)

class IntentAnalysisService:
    """意圖分析服務"""
    
    @staticmethod
    async def analyze_user_intent(message: str, chat_history: List[Dict[str, Any]] = None) -> str:
        """
        分析用戶意圖
        """
        try:
            # 過濾聊天歷史中的 markdown 搜尋結果
            filtered_history = ChatHistoryFilterService.filter_markdown_from_chat_history(chat_history) if chat_history else []
            
            prompt = f"""
            請分析用戶的意圖，並從以下選項中選擇最合適的一個：
            
            1. search_events - 搜尋活動
            2. get_event_details - 獲取特定活動詳情
            3. analyze_trends - 分析活動趨勢（月度、時間分布）
            4. analyze_statistics - 分析活動統計（地區分布、類別分布）
            5. get_recommendations - 獲取個人化活動推薦
            6. compare_events - 比較不同活動或地區
            7. analyze_geographic - 分析地理分布
            8. generate_report - 生成分析報告
            9. ask_question - 詢問問題
            10. greeting - 打招呼
            11. goodbye - 告別
            12. other - 其他
            
            用戶訊息：{message}
            聊天歷史：{json.dumps(filtered_history, ensure_ascii=False)}
            
            請只返回意圖類別，不要添加其他文字。
            """
            
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "你是一個專業的意圖分析助手，請準確識別用戶的意圖。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=50,
                timeout=10  # 添加超時設置
            )
            
            intent = response.choices[0].message.content.strip()
            logger.info(f"Analyzed user intent: {intent}")
            return intent
            
        except (openai.APIConnectionError, openai.APITimeoutError) as e:
            logger.warning(f"OpenAI API connection error, using fallback intent analysis: {str(e)}")
            return IntentAnalysisService._fallback_intent_analysis(message)
        except Exception as e:
            logger.error(f"Error analyzing user intent: {str(e)}")
            return IntentAnalysisService._fallback_intent_analysis(message)

    @staticmethod
    def _fallback_intent_analysis(message: str) -> str:
        """備用意圖分析（基於關鍵詞）"""
        message_lower = message.lower()
        
        # 搜尋活動相關關鍵詞
        search_keywords = ["找", "搜尋", "查找", "活動", "展覽", "音樂會", "講座", "課程", "推薦"]
        if any(keyword in message_lower for keyword in search_keywords):
            return "search_events"
        
        # 詳情查詢關鍵詞
        detail_keywords = ["詳情", "詳細", "資訊", "介紹", "說明"]
        if any(keyword in message_lower for keyword in detail_keywords):
            return "get_event_details"
        
        # 分析相關關鍵詞
        analysis_keywords = ["分析", "統計", "趨勢", "報告"]
        if any(keyword in message_lower for keyword in analysis_keywords):
            return "analyze_trends"
        
        # 推薦相關關鍵詞
        recommendation_keywords = ["推薦", "建議", "適合"]
        if any(keyword in message_lower for keyword in recommendation_keywords):
            return "get_recommendations"
        
        # 打招呼關鍵詞
        greeting_keywords = ["你好", "哈囉", "嗨", "hello", "hi"]
        if any(keyword in message_lower for keyword in greeting_keywords):
            return "greeting"
        
        # 告別關鍵詞
        goodbye_keywords = ["再見", "掰掰", "bye", "goodbye"]
        if any(keyword in message_lower for keyword in goodbye_keywords):
            return "goodbye"
        
        # 默認為其他
        return "other"

class SentimentAnalysisService:
    """情感分析服務"""
    
    @staticmethod
    async def analyze_user_sentiment(message: str, chat_history: List[Dict[str, Any]] = None) -> str:
        """
        分析用戶情感
        """
        try:
            # 過濾聊天歷史中的 markdown 搜尋結果
            filtered_history = ChatHistoryFilterService.filter_markdown_from_chat_history(chat_history) if chat_history else []
            
            prompt = f"""
            請分析用戶的情感狀態，並從以下選項中選擇最合適的一個：
            
            1. positive - 積極正面
            2. negative - 消極負面
            3. neutral - 中性
            4. excited - 興奮期待
            5. frustrated - 沮喪困惑
            6. curious - 好奇探索
            
            用戶訊息：{message}
            聊天歷史：{json.dumps(filtered_history, ensure_ascii=False)}
            
            請只返回情感類別，不要添加其他文字。
            """
            
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "你是一個專業的情感分析助手，請準確識別用戶的情感狀態。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=50,
                timeout=10
            )
            
            sentiment = response.choices[0].message.content.strip()
            logger.info(f"Analyzed user sentiment: {sentiment}")
            return sentiment
            
        except (openai.APIConnectionError, openai.APITimeoutError) as e:
            logger.warning(f"OpenAI API connection error, using fallback sentiment analysis: {str(e)}")
            return SentimentAnalysisService._fallback_sentiment_analysis(message)
        except Exception as e:
            logger.error(f"Error analyzing user sentiment: {str(e)}")
            return SentimentAnalysisService._fallback_sentiment_analysis(message)

    @staticmethod
    def _fallback_sentiment_analysis(message: str) -> str:
        """備用情感分析（基於關鍵詞）"""
        message_lower = message.lower()
        
        # 積極情感關鍵詞
        positive_keywords = ["好", "棒", "讚", "喜歡", "愛", "開心", "高興", "滿意", "謝謝", "感謝"]
        if any(keyword in message_lower for keyword in positive_keywords):
            return "positive"
        
        # 興奮期待關鍵詞
        excited_keywords = ["期待", "興奮", "迫不及待", "太棒了", "哇", "驚喜"]
        if any(keyword in message_lower for keyword in excited_keywords):
            return "excited"
        
        # 消極情感關鍵詞
        negative_keywords = ["不好", "糟", "討厭", "失望", "難過", "生氣", "煩", "爛"]
        if any(keyword in message_lower for keyword in negative_keywords):
            return "negative"
        
        # 沮喪困惑關鍵詞
        frustrated_keywords = ["困惑", "不懂", "搞不清楚", "複雜", "麻煩", "煩惱"]
        if any(keyword in message_lower for keyword in frustrated_keywords):
            return "frustrated"
        
        # 好奇探索關鍵詞
        curious_keywords = ["想知道", "好奇", "有趣", "探索", "了解", "學習"]
        if any(keyword in message_lower for keyword in curious_keywords):
            return "curious"
        
        # 默認為中性
        return "neutral"

class EntityExtractionService:
    """實體提取服務"""
    
    @staticmethod
    async def extract_entities(message: str) -> List[Dict[str, Any]]:
        """
        從用戶訊息中提取實體
        """
        try:
            prompt = f"""
            請從以下用戶訊息中提取實體，並以JSON格式返回：
            
            用戶訊息：{message}
            
            請提取以下類型的實體：
            - location: 地點（城市、區域、場所）
            - time: 時間（日期、時間範圍）
            - activity_type: 活動類型（展覽、音樂會、講座等）
            - person: 人物（藝術家、講者等）
            - organization: 組織（主辦單位等）
            
            返回格式：
            [
                {{"entity": "實體名稱", "type": "實體類型", "value": "標準化值"}}
            ]
            
            請直接返回JSON格式，不要添加任何markdown標記或其他文字。
            """
            
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "你是一個專業的實體提取助手，請準確提取用戶訊息中的實體信息。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=300,
                timeout=10
            )
            
            content = response.choices[0].message.content.strip()
            
            # 清理回應內容
            content = content.replace('```json', '').replace('```', '').strip()
            
            try:
                entities = json.loads(content)
                logger.info(f"Extracted entities: {entities}")
                return entities
            except json.JSONDecodeError:
                logger.error(f"Failed to parse entities JSON: {content}")
                return EntityExtractionService._fallback_entity_extraction(message)
                
        except (openai.APIConnectionError, openai.APITimeoutError) as e:
            logger.warning(f"OpenAI API connection error, using fallback entity extraction: {str(e)}")
            return EntityExtractionService._fallback_entity_extraction(message)
        except Exception as e:
            logger.error(f"Error extracting entities: {str(e)}")
            return EntityExtractionService._fallback_entity_extraction(message)

    @staticmethod
    def _fallback_entity_extraction(message: str) -> List[Dict[str, Any]]:
        """備用實體提取（基於關鍵詞和模式）"""
        entities = []
        message_lower = message.lower()
        
        # 地點實體
        location_keywords = {
            "台北": "台北市", "新北": "新北市", "桃園": "桃園市", "台中": "台中市",
            "台南": "台南市", "高雄": "高雄市", "基隆": "基隆市", "新竹": "新竹市",
            "嘉義": "嘉義市", "宜蘭": "宜蘭縣", "花蓮": "花蓮縣", "台東": "台東縣"
        }
        
        for keyword, standard_name in location_keywords.items():
            if keyword in message_lower:
                entities.append({
                    "entity": keyword,
                    "type": "location",
                    "value": standard_name
                })
        
        # 活動類型實體
        activity_types = {
            "展覽": "exhibition", "音樂會": "concert", "講座": "lecture",
            "工作坊": "workshop", "課程": "course", "演出": "performance",
            "表演": "show", "活動": "event"
        }
        
        for keyword, standard_type in activity_types.items():
            if keyword in message_lower:
                entities.append({
                    "entity": keyword,
                    "type": "activity_type",
                    "value": standard_type
                })
        
        return entities

class InterestAnalysisService:
    """興趣分析服務"""
    
    @staticmethod
    async def analyze_user_interests(message: str, chat_history: List[Dict[str, Any]] = None) -> List[str]:
        """
        分析用戶興趣
        """
        try:
            # 過濾聊天歷史中的 markdown 搜尋結果
            filtered_history = ChatHistoryFilterService.filter_markdown_from_chat_history(chat_history) if chat_history else []
            
            prompt = f"""
            請分析用戶的興趣偏好，並從以下類別中選擇相關的興趣（可多選）：
            
            藝術文化：展覽、美術、攝影、文學、戲劇、舞蹈
            音樂娛樂：音樂會、演唱會、音樂節、KTV、夜生活
            運動健身：健身、瑜伽、跑步、球類運動、戶外運動
            親子家庭：親子活動、兒童教育、家庭聚會
            學習成長：講座、研習、工作坊、技能培訓
            美食餐飲：美食、餐廳、料理課程、品酒
            旅遊探索：旅遊、戶外探險、自然景觀
            科技創新：科技展、創新論壇、數位體驗
            社交聚會：聚會、交友、社群活動
            
            用戶訊息：{message}
            聊天歷史：{json.dumps(filtered_history, ensure_ascii=False)}
            
            請以JSON陣列格式返回興趣類別，例如：["藝術文化", "音樂娛樂"]
            """
            
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "你是一個專業的興趣分析助手，請準確識別用戶的興趣偏好。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=200,
                timeout=10
            )
            
            content = response.choices[0].message.content.strip()
            
            # 清理回應內容
            content = content.replace('```json', '').replace('```', '').strip()
            
            try:
                interests = json.loads(content)
                logger.info(f"Analyzed user interests: {interests}")
                return interests if isinstance(interests, list) else []
            except json.JSONDecodeError:
                logger.error(f"Failed to parse interests JSON: {content}")
                return InterestAnalysisService._fallback_interest_analysis(message)
                
        except (openai.APIConnectionError, openai.APITimeoutError) as e:
            logger.warning(f"OpenAI API connection error, using fallback interest analysis: {str(e)}")
            return InterestAnalysisService._fallback_interest_analysis(message)
        except Exception as e:
            logger.error(f"Error analyzing user interests: {str(e)}")
            return InterestAnalysisService._fallback_interest_analysis(message)

    @staticmethod
    def _fallback_interest_analysis(message: str) -> List[str]:
        """備用興趣分析（基於關鍵詞）"""
        message_lower = message.lower()
        detected_interests = []
        
        interest_keywords = {
            "藝術文化": ["藝術", "展覽", "美術", "攝影", "文學", "戲劇", "舞蹈", "藝文", "博物館", "畫廊"],
            "音樂娛樂": ["音樂", "演唱會", "音樂會", "演出", "表演", "歌手", "樂團", "音樂節"],
            "運動健身": ["運動", "健身", "瑜伽", "跑步", "球類", "游泳", "登山", "戶外運動"],
            "親子家庭": ["親子", "兒童", "家庭", "小孩", "孩子", "親子活動"],
            "學習成長": ["學習", "課程", "講座", "工作坊", "研習", "教學", "培訓"],
            "美食餐飲": ["美食", "餐廳", "料理", "烹飪", "品酒", "咖啡", "甜點"],
            "旅遊探索": ["旅遊", "戶外", "野餐", "露營", "踏青", "自然", "郊遊"],
            "科技創新": ["科技", "創新", "數位", "AI", "程式", "技術"],
            "社交聚會": ["社交", "聚會", "交友", "派對", "聯誼", "社群"]
        }
        
        for category, keywords in interest_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                detected_interests.append(category)
        
        return detected_interests[:3]  # 最多返回3個興趣 