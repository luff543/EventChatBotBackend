from typing import Dict, Any, List, Optional
import json
from datetime import datetime
from openai import OpenAI
import openai
from utils.config import OPENAI_API_KEY
from utils.logger import logger

client = OpenAI(api_key=OPENAI_API_KEY)

class ConversationStageService:
    """對話階段分析服務"""
    
    @staticmethod
    async def analyze_conversation_stage(
        chat_history: List[Dict[str, Any]], 
        context: Dict[str, Any] = None
    ) -> str:
        """
        分析當前對話階段
        
        返回值：
        - opening: 開場階段
        - exploring: 探索需求階段
        - clarifying: 澄清細節階段
        - searching: 搜尋階段
        - recommending: 推薦階段
        - deciding: 決策階段
        - closing: 結束階段
        """
        try:
            if not chat_history:
                return "opening"
            
            # 分析對話長度和內容
            conversation_length = len(chat_history)
            user_messages = [msg for msg in chat_history if msg.get("role") == "user"]
            bot_messages = [msg for msg in chat_history if msg.get("role") == "assistant"]
            
            # 如果對話剛開始
            if conversation_length <= 2:
                return "opening"
            
            # 分析最近的訊息內容
            recent_messages = chat_history[-6:]  # 最近3輪對話
            recent_user_messages = [msg.get("content", "") for msg in recent_messages if msg.get("role") == "user"]
            recent_bot_messages = [msg.get("content", "") for msg in recent_messages if msg.get("role") == "assistant"]
            
            # 使用GPT分析對話階段
            analysis_prompt = f"""
            請分析以下對話的當前階段。對話階段定義如下：
            
            1. opening: 開場階段 - 初次問候、介紹服務
            2. exploring: 探索需求階段 - 了解用戶興趣、偏好
            3. clarifying: 澄清細節階段 - 確認具體需求、參數
            4. searching: 搜尋階段 - 正在搜尋或已搜尋活動
            5. recommending: 推薦階段 - 提供活動推薦、解釋選擇
            6. deciding: 決策階段 - 用戶在考慮或選擇活動
            7. closing: 結束階段 - 準備結束對話
            
            對話歷史（最近的訊息）：
            用戶訊息：{json.dumps(recent_user_messages, ensure_ascii=False)}
            機器人回應：{json.dumps(recent_bot_messages, ensure_ascii=False)}
            
            對話總長度：{conversation_length}
            
            請只返回階段名稱（opening/exploring/clarifying/searching/recommending/deciding/closing）。
            """
            
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "你是一個專業的對話分析師，請準確識別對話階段。"},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.1,
                max_tokens=50,
                timeout=10
            )
            
            stage = response.choices[0].message.content.strip().lower()
            
            # 驗證返回的階段是否有效
            valid_stages = ["opening", "exploring", "clarifying", "searching", "recommending", "deciding", "closing"]
            if stage not in valid_stages:
                # 使用規則基礎的備用分析
                stage = ConversationStageService._rule_based_stage_analysis(chat_history, context)
            
            logger.info(f"Analyzed conversation stage: {stage}")
            return stage
            
        except (openai.APIConnectionError, openai.APITimeoutError) as e:
            logger.warning(f"OpenAI API connection error, using rule-based analysis: {str(e)}")
            return ConversationStageService._rule_based_stage_analysis(chat_history, context)
        except Exception as e:
            logger.error(f"Error analyzing conversation stage: {str(e)}")
            # 使用規則基礎的備用分析
            return ConversationStageService._rule_based_stage_analysis(chat_history, context)
    
    @staticmethod
    def _rule_based_stage_analysis(
        chat_history: List[Dict[str, Any]], 
        context: Dict[str, Any] = None
    ) -> str:
        """基於規則的對話階段分析（備用方法）"""
        try:
            if not chat_history:
                return "opening"
            
            conversation_length = len(chat_history)
            user_messages = [msg.get("content", "").lower() for msg in chat_history if msg.get("role") == "user"]
            bot_messages = [msg.get("content", "").lower() for msg in chat_history if msg.get("role") == "assistant"]
            
            # 最近的用戶訊息
            last_user_message = user_messages[-1] if user_messages else ""
            last_bot_message = bot_messages[-1] if bot_messages else ""
            
            # 開場階段關鍵詞
            opening_keywords = ["你好", "hello", "hi", "嗨", "您好", "開始", "幫助"]
            
            # 探索階段關鍵詞
            exploring_keywords = ["喜歡", "想要", "偏好", "興趣", "類型", "什麼樣", "推薦"]
            
            # 澄清階段關鍵詞
            clarifying_keywords = ["具體", "詳細", "確認", "是否", "對嗎", "正確嗎", "意思是"]
            
            # 搜尋階段關鍵詞
            searching_keywords = ["搜尋", "查找", "找", "活動", "事件", "搜索"]
            
            # 推薦階段關鍵詞（在機器人回應中）
            recommending_keywords = ["推薦", "建議", "適合", "可以試試", "為您找到"]
            
            # 決策階段關鍵詞
            deciding_keywords = ["考慮", "想想", "決定", "選擇", "報名", "參加", "不錯", "感興趣"]
            
            # 結束階段關鍵詞
            closing_keywords = ["謝謝", "再見", "結束", "不用了", "夠了", "bye"]
            
            # 規則判斷
            if conversation_length <= 2:
                return "opening"
            
            # 檢查結束階段
            if any(keyword in last_user_message for keyword in closing_keywords):
                return "closing"
            
            # 檢查搜尋階段
            if any(keyword in last_user_message for keyword in searching_keywords):
                return "searching"
            
            # 檢查機器人是否在推薦
            if any(keyword in last_bot_message for keyword in recommending_keywords):
                return "recommending"
            
            # 檢查決策階段
            if any(keyword in last_user_message for keyword in deciding_keywords):
                return "deciding"
            
            # 檢查澄清階段
            if any(keyword in last_user_message for keyword in clarifying_keywords):
                return "clarifying"
            
            # 檢查探索階段
            if any(keyword in last_user_message for keyword in exploring_keywords):
                return "exploring"
            
            # 檢查開場階段
            if any(keyword in last_user_message for keyword in opening_keywords):
                return "opening"
            
            # 根據對話長度判斷
            if conversation_length <= 4:
                return "exploring"
            elif conversation_length <= 8:
                return "clarifying"
            elif conversation_length <= 12:
                return "searching"
            else:
                return "recommending"
                
        except Exception as e:
            logger.error(f"Error in rule-based stage analysis: {str(e)}")
            return "exploring"  # 默認階段
    
    @staticmethod
    async def get_stage_appropriate_questions(stage: str) -> List[str]:
        """根據對話階段獲取合適的問題模板"""
        try:
            stage_questions = {
                "opening": [
                    "您今天想找什麼類型的活動呢？",
                    "有特別想參加的活動類別嗎？",
                    "您比較偏好室內還是戶外活動？",
                    "想找這週末的活動，還是之後的時間？"
                ],
                "exploring": [
                    "您平常喜歡什麼樣的休閒活動？",
                    "有特別想去的地區或城市嗎？",
                    "您比較喜歡一個人參加還是和朋友一起？",
                    "對活動的時間有什麼偏好嗎？",
                    "有預算上的考量嗎？"
                ],
                "clarifying": [
                    "您剛才提到的是指...對嗎？",
                    "想確認一下，您希望的活動時間是...？",
                    "關於地點，您的意思是...？",
                    "我理解的對嗎，您想要...？"
                ],
                "searching": [
                    "需要我調整搜尋條件嗎？",
                    "想看看其他類型的活動嗎？",
                    "要不要試試不同的時間範圍？",
                    "需要更改地點範圍嗎？"
                ],
                "recommending": [
                    "這些活動中有您感興趣的嗎？",
                    "想了解哪個活動的更多詳情？",
                    "需要我推薦類似的其他活動嗎？",
                    "對這些推薦有什麼想法？"
                ],
                "deciding": [
                    "有需要我提供更多資訊幫助您決定嗎？",
                    "想比較一下不同活動的特色嗎？",
                    "需要我幫您查看活動的報名方式嗎？",
                    "還有其他考慮因素嗎？"
                ],
                "closing": [
                    "還有其他需要幫助的嗎？",
                    "希望今天的推薦對您有幫助！",
                    "祝您參加活動愉快！",
                    "歡迎隨時回來搜尋更多活動！"
                ]
            }
            
            return stage_questions.get(stage, stage_questions["exploring"])
            
        except Exception as e:
            logger.error(f"Error getting stage appropriate questions: {str(e)}")
            return ["有什麼我可以幫助您的嗎？"]
    
    @staticmethod
    async def should_transition_stage(
        current_stage: str, 
        user_message: str, 
        bot_response: str,
        context: Dict[str, Any] = None
    ) -> tuple[bool, str]:
        """判斷是否應該轉換對話階段"""
        try:
            # 定義階段轉換規則
            transition_rules = {
                "opening": {
                    "to": "exploring",
                    "triggers": ["想找", "需要", "喜歡", "偏好", "活動"]
                },
                "exploring": {
                    "to": "clarifying",
                    "triggers": ["具體", "確認", "是的", "對", "沒錯"]
                },
                "clarifying": {
                    "to": "searching",
                    "triggers": ["搜尋", "查找", "找", "開始", "好的"]
                },
                "searching": {
                    "to": "recommending",
                    "triggers": ["結果", "推薦", "建議", "看看"]
                },
                "recommending": {
                    "to": "deciding",
                    "triggers": ["考慮", "想想", "不錯", "感興趣", "喜歡"]
                },
                "deciding": {
                    "to": "closing",
                    "triggers": ["決定", "選擇", "謝謝", "夠了", "不用了"]
                }
            }
            
            user_message_lower = user_message.lower()
            
            # 檢查當前階段的轉換規則
            if current_stage in transition_rules:
                rule = transition_rules[current_stage]
                triggers = rule["triggers"]
                
                if any(trigger in user_message_lower for trigger in triggers):
                    return True, rule["to"]
            
            # 特殊情況：直接跳轉到結束階段
            closing_triggers = ["再見", "謝謝", "結束", "bye", "不用了"]
            if any(trigger in user_message_lower for trigger in closing_triggers):
                return True, "closing"
            
            return False, current_stage
            
        except Exception as e:
            logger.error(f"Error checking stage transition: {str(e)}")
            return False, current_stage
    
    @staticmethod
    async def get_stage_context(stage: str) -> Dict[str, Any]:
        """獲取階段相關的上下文信息"""
        try:
            stage_contexts = {
                "opening": {
                    "focus": "建立關係，了解基本需求",
                    "goals": ["歡迎用戶", "介紹服務", "引導表達需求"],
                    "tone": "友善、歡迎",
                    "question_style": "開放式、探索性"
                },
                "exploring": {
                    "focus": "深入了解用戶偏好和需求",
                    "goals": ["收集偏好信息", "了解限制條件", "建立用戶畫像"],
                    "tone": "好奇、關心",
                    "question_style": "具體、引導性"
                },
                "clarifying": {
                    "focus": "澄清模糊信息，確認理解",
                    "goals": ["消除歧義", "確認細節", "準確理解需求"],
                    "tone": "確認、專業",
                    "question_style": "確認式、具體化"
                },
                "searching": {
                    "focus": "執行搜尋，提供結果",
                    "goals": ["找到相關活動", "展示搜尋結果", "解釋搜尋邏輯"],
                    "tone": "專業、有效率",
                    "question_style": "調整式、優化性"
                },
                "recommending": {
                    "focus": "推薦合適活動，解釋選擇理由",
                    "goals": ["提供個性化推薦", "解釋推薦理由", "引導深入了解"],
                    "tone": "建議性、專業",
                    "question_style": "評估式、比較性"
                },
                "deciding": {
                    "focus": "協助決策，提供支持信息",
                    "goals": ["提供決策支持", "回答疑慮", "促進行動"],
                    "tone": "支持性、鼓勵",
                    "question_style": "決策支持式、行動導向"
                },
                "closing": {
                    "focus": "結束對話，留下好印象",
                    "goals": ["總結服務", "表達關心", "邀請再次使用"],
                    "tone": "感謝、溫暖",
                    "question_style": "關懷式、開放性"
                }
            }
            
            return stage_contexts.get(stage, stage_contexts["exploring"])
            
        except Exception as e:
            logger.error(f"Error getting stage context: {str(e)}")
            return {
                "focus": "協助用戶",
                "goals": ["提供幫助"],
                "tone": "友善",
                "question_style": "開放式"
            } 