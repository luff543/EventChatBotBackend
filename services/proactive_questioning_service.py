from typing import Dict, Any, List, Optional, Tuple
import json
from datetime import datetime, timedelta
from openai import OpenAI
from utils.config import OPENAI_API_KEY
from utils.logger import logger
from services.conversation_stage_service import ConversationStageService

client = OpenAI(api_key=OPENAI_API_KEY)

class ProactiveQuestioningService:
    """主動式提問服務"""
    
    @staticmethod
    def _extract_interest_name(interest):
        """提取興趣名稱，處理JSON格式"""
        if isinstance(interest, str):
            return interest
        elif isinstance(interest, dict):
            return interest.get('interest', interest.get('name', str(interest)))
        else:
            return str(interest)
    
    @staticmethod
    def _extract_interest_names(interests):
        """提取興趣名稱列表，處理JSON格式"""
        if not interests:
            return []
        
        names = []
        for interest in interests:
            name = ProactiveQuestioningService._extract_interest_name(interest)
            if name and name not in names:  # 避免重複
                names.append(name)
        return names
    
    @staticmethod
    async def generate_proactive_questions(
        context: Dict[str, Any],
        user_profile: Dict[str, Any],
        conversation_stage: str,
        last_response_type: str = None
    ) -> Dict[str, Any]:
        """
        根據上下文和用戶畫像生成主動式問題
        
        Args:
            context: 當前對話上下文
            user_profile: 用戶畫像
            conversation_stage: 對話階段 (opening, exploring, clarifying, recommending, closing)
            last_response_type: 上一次回應的類型
        """
        try:
            logger.info(f"Generating proactive questions for stage: {conversation_stage}")
            
            # 獲取階段相關的上下文
            stage_context = await ConversationStageService.get_stage_context(conversation_stage)
            
            # 根據對話階段生成不同類型的問題
            if conversation_stage == "opening":
                return await ProactiveQuestioningService._generate_opening_questions(
                    user_profile, stage_context
                )
            elif conversation_stage == "exploring":
                return await ProactiveQuestioningService._generate_exploring_questions(
                    context, user_profile, stage_context
                )
            elif conversation_stage == "clarifying":
                return await ProactiveQuestioningService._generate_clarifying_questions(
                    context, user_profile, stage_context
                )
            elif conversation_stage == "searching":
                return await ProactiveQuestioningService._generate_searching_questions(
                    context, user_profile, stage_context
                )
            elif conversation_stage == "recommending":
                return await ProactiveQuestioningService._generate_recommending_questions(
                    context, user_profile, stage_context
                )
            elif conversation_stage == "deciding":
                return await ProactiveQuestioningService._generate_deciding_questions(
                    context, user_profile, stage_context
                )
            elif conversation_stage == "closing":
                return await ProactiveQuestioningService._generate_closing_questions(
                    user_profile, stage_context
                )
            else:
                # 默認生成探索性問題
                return await ProactiveQuestioningService._generate_exploring_questions(
                    context, user_profile, stage_context
                )
                
        except Exception as e:
            logger.error(f"Error generating proactive questions: {str(e)}")
            return {
                "questions": ["有什麼我可以幫助您的嗎？"],
                "question_type": "general",
                "confidence": 0.3,
                "follow_up_suggestions": []
            }
    
    @staticmethod
    async def _generate_opening_questions(
        user_profile: Dict[str, Any],
        stage_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成開場階段的問題"""
        try:
            is_new_user = user_profile.get("visit_count", 0) <= 1
            interests = user_profile.get("interests", [])
            
            if is_new_user:
                # 新用戶的開場問題
                questions = [
                    "歡迎使用活動推薦服務！您今天想找什麼類型的活動呢？",
                    "您好！我可以幫您搜尋各種精彩的活動。您比較偏好什麼樣的休閒活動？",
                    "很高興為您服務！想找這週末的活動，還是特定日期的活動？"
                ]
                
                follow_up_suggestions = [
                    "音樂表演", "藝文展覽", "戶外活動", "美食體驗", "學習課程"
                ]
            else:
                # 回訪用戶的開場問題
                if interests:
                    questions = [
                        f"歡迎回來！上次您對{ProactiveQuestioningService._extract_interest_name(interests[0])}很感興趣，今天想找類似的活動嗎？",
                        f"您好！根據您的偏好，我注意到您喜歡{', '.join(ProactiveQuestioningService._extract_interest_names(interests[:2]))}，有新的需求嗎？",
                        "很高興再次為您服務！今天想探索什麼新的活動類型呢？"
                    ]
                    follow_up_suggestions = ProactiveQuestioningService._extract_interest_names(interests[:3]) + ["探索新類型"]
                else:
                    questions = [
                        "歡迎回來！今天想找什麼樣的活動呢？",
                        "您好！有什麼新的活動需求嗎？",
                        "很高興再次為您服務！想嘗試什麼類型的活動？"
                    ]
                    follow_up_suggestions = ["音樂", "藝文", "運動", "美食", "學習"]
            
            return {
                "questions": questions[:2],  # 返回前2個問題
                "question_type": "opening",
                "confidence": 0.9,
                "follow_up_suggestions": follow_up_suggestions,
                "personalization_level": "high" if not is_new_user and interests else "medium"
            }
            
        except Exception as e:
            logger.error(f"Error generating opening questions: {str(e)}")
            return {
                "questions": ["您好！我是活動推薦助手，很高興為您服務！"],
                "question_type": "opening",
                "confidence": 0.5,
                "follow_up_suggestions": []
            }
    
    @staticmethod
    async def _generate_exploring_questions(
        context: Dict[str, Any],
        user_profile: Dict[str, Any],
        stage_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成探索需求階段的問題"""
        try:
            interests = user_profile.get("interests", [])
            preferences = user_profile.get("activity_preferences", {})
            personality = user_profile.get("personality_traits", {})
            
            questions = []
            follow_up_suggestions = []
            
            # 根據用戶畫像生成個性化問題
            if not interests:
                # 沒有興趣資料，探索基本偏好
                questions = [
                    "您平常喜歡什麼樣的休閒活動？",
                    "比較偏好室內活動還是戶外活動？",
                    "喜歡一個人參加還是和朋友一起的活動？"
                ]
                follow_up_suggestions = ["音樂", "藝文", "運動", "美食", "戶外", "學習"]
            else:
                # 有興趣資料，深入探索
                if len(interests) == 1:
                    questions = [
                        f"除了{ProactiveQuestioningService._extract_interest_name(interests[0])}，還有其他感興趣的活動類型嗎？",
                        f"在{ProactiveQuestioningService._extract_interest_name(interests[0])}方面，您比較喜歡哪種形式的活動？",
                        "想嘗試一些新的活動類型嗎？"
                    ]
                else:
                    questions = [
                        f"我看到您對{', '.join(ProactiveQuestioningService._extract_interest_names(interests[:2]))}都有興趣，今天想專注在哪一類？",
                        "想結合不同類型的活動嗎？",
                        "有特別想深入探索的領域嗎？"
                    ]
                follow_up_suggestions = ProactiveQuestioningService._extract_interest_names(interests) + ["探索新類型"]
            
            # 根據個性特徵調整問題
            if personality.get("social_level", 0.5) > 0.7:
                questions.append("您比較喜歡大型聚會還是小團體活動？")
            elif personality.get("social_level", 0.5) < 0.3:
                questions.append("有適合一個人參加的活動推薦嗎？")
            
            # 探索地點偏好
            if not preferences.get("preferred_locations"):
                questions.append("有特別想去的地區或城市嗎？")
                follow_up_suggestions.extend(["台北", "台中", "高雄", "台南"])
            
            # 探索時間偏好
            if not preferences.get("preferred_times"):
                questions.append("對活動時間有什麼偏好？週末還是平日？")
                follow_up_suggestions.extend(["週末", "平日晚上", "假日"])
            
            return {
                "questions": questions[:3],  # 返回前3個問題
                "question_type": "exploring_needs",
                "confidence": 0.8,
                "follow_up_suggestions": follow_up_suggestions[:5],
                "personalization_level": "high" if interests else "medium"
            }
            
        except Exception as e:
            logger.error(f"Error generating exploring questions: {str(e)}")
            return {
                "questions": ["您平常喜歡什麼樣的休閒活動？"],
                "question_type": "exploring_needs",
                "confidence": 0.5,
                "follow_up_suggestions": []
            }
    
    @staticmethod
    async def _generate_clarifying_questions(
        context: Dict[str, Any],
        user_profile: Dict[str, Any],
        stage_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成澄清階段的問題"""
        try:
            # 分析上下文中的模糊信息
            ambiguous_entities = context.get("ambiguous_entities", [])
            current_search = context.get("current_search", {})
            
            questions = []
            follow_up_suggestions = []
            
            # 根據模糊實體生成澄清問題
            if ambiguous_entities:
                for entity in ambiguous_entities[:2]:
                    if entity.get("type") == "location":
                        questions.append(f"關於地點「{entity.get('value')}」，您指的是哪個具體區域？")
                    elif entity.get("type") == "time":
                        questions.append(f"關於時間「{entity.get('value')}」，能更具體說明是哪一天嗎？")
                    elif entity.get("type") == "category":
                        questions.append(f"關於「{entity.get('value')}」活動，您想要哪種類型的？")
            
            # 根據搜尋參數生成確認問題
            if current_search:
                if current_search.get("query") and not current_search.get("category"):
                    questions.append("想確認一下，您要找的活動類別是什麼？")
                if current_search.get("location") and not current_search.get("specific_area"):
                    questions.append("地點方面，有特定的區域偏好嗎？")
                if not current_search.get("time_range"):
                    questions.append("時間上有什麼限制嗎？")
            
            # 如果沒有特定的澄清需求，生成一般性確認問題
            if not questions:
                questions = [
                    "我理解的對嗎，您想要找...？",
                    "想確認一下您的需求，是否正確？",
                    "還有其他需要補充的條件嗎？"
                ]
            
            # 生成後續建議
            if current_search.get("category"):
                follow_up_suggestions.append(f"確認{current_search['category']}")
            if current_search.get("location"):
                follow_up_suggestions.append(f"確認{current_search['location']}")
            follow_up_suggestions.extend(["開始搜尋", "修改條件"])
            
            return {
                "questions": questions[:2],
                "question_type": "clarifying",
                "confidence": 0.7,
                "follow_up_suggestions": follow_up_suggestions[:4],
                "clarification_needed": len(ambiguous_entities) > 0
            }
            
        except Exception as e:
            logger.error(f"Error generating clarifying questions: {str(e)}")
            return {
                "questions": ["想確認一下您的需求，是否正確？"],
                "question_type": "clarifying",
                "confidence": 0.5,
                "follow_up_suggestions": []
            }
    
    @staticmethod
    async def _generate_searching_questions(
        context: Dict[str, Any],
        user_profile: Dict[str, Any],
        stage_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成搜尋階段的問題"""
        try:
            last_search_results = context.get("last_search_results", {})
            current_search = context.get("current_search", {})
            
            questions = []
            follow_up_suggestions = []
            
            # 根據搜尋結果生成問題
            if last_search_results:
                result_count = last_search_results.get("count", 0)
                
                if result_count == 0:
                    questions = [
                        "沒有找到符合條件的活動，要不要調整搜尋條件？",
                        "可以試試放寬一些限制條件，比如時間或地點？",
                        "想嘗試搜尋其他類型的活動嗎？"
                    ]
                    follow_up_suggestions = ["放寬時間", "擴大地區", "改變類別", "降低要求"]
                elif result_count > 50:
                    questions = [
                        "找到很多活動！需要我幫您縮小範圍嗎？",
                        "結果太多了，想加一些篩選條件嗎？",
                        "要不要按照特定條件排序？"
                    ]
                    follow_up_suggestions = ["縮小時間", "指定地區", "選擇類別", "按時間排序"]
                else:
                    questions = [
                        "找到一些不錯的活動！想看看詳細資訊嗎？",
                        "這些結果符合您的需求嗎？",
                        "需要調整搜尋條件嗎？"
                    ]
                    follow_up_suggestions = ["查看詳情", "調整條件", "重新搜尋", "換個類型"]
            else:
                # 沒有搜尋結果時的問題
                questions = [
                    "準備開始搜尋了，還有其他條件要加入嗎？",
                    "搜尋條件都確認了嗎？",
                    "需要我調整什麼參數嗎？"
                ]
                follow_up_suggestions = ["開始搜尋", "調整條件", "重新設定"]
            
            return {
                "questions": questions[:2],
                "question_type": "search_optimization",
                "confidence": 0.8,
                "follow_up_suggestions": follow_up_suggestions[:4],
                "search_context": {
                    "has_results": bool(last_search_results),
                    "result_count": last_search_results.get("count", 0) if last_search_results else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating searching questions: {str(e)}")
            return {
                "questions": ["需要調整搜尋條件嗎？"],
                "question_type": "search_optimization",
                "confidence": 0.5,
                "follow_up_suggestions": []
            }
    
    @staticmethod
    async def _generate_recommending_questions(
        context: Dict[str, Any],
        user_profile: Dict[str, Any],
        stage_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成推薦階段的問題"""
        try:
            last_search_results = context.get("last_search_results", {})
            interests = user_profile.get("interests", [])
            
            questions = []
            follow_up_suggestions = []
            
            # 根據推薦結果生成問題
            if last_search_results and last_search_results.get("events"):
                events = last_search_results["events"]
                event_count = len(events)
                
                if event_count == 1:
                    questions = [
                        "這個活動看起來如何？符合您的需求嗎？",
                        "想了解這個活動的更多詳情嗎？",
                        "需要我找一些類似的活動嗎？"
                    ]
                    follow_up_suggestions = ["了解詳情", "查看類似", "重新搜尋"]
                elif event_count <= 5:
                    questions = [
                        "這幾個活動中有您感興趣的嗎？",
                        "想深入了解哪個活動？",
                        "需要我解釋為什麼推薦這些活動嗎？"
                    ]
                    follow_up_suggestions = ["選擇活動", "了解推薦理由", "查看更多"]
                else:
                    questions = [
                        "我為您推薦了這些活動，哪些比較吸引您？",
                        "想按照什麼標準來篩選這些推薦？",
                        "需要我重點介紹幾個最適合的嗎？"
                    ]
                    follow_up_suggestions = ["按時間篩選", "按地點篩選", "看熱門推薦", "個人化推薦"]
            
            # 根據用戶興趣個性化問題
            if interests:
                questions.append(f"根據您對{ProactiveQuestioningService._extract_interest_name(interests[0])}的興趣，這些推薦如何？")
                follow_up_suggestions.extend([f"更多{interest}" for interest in ProactiveQuestioningService._extract_interest_names(interests[:2])])
            
            # 如果沒有具體推薦，生成一般性問題
            if not questions:
                questions = [
                    "對這些推薦有什麼想法？",
                    "想了解推薦的理由嗎？",
                    "需要更個性化的推薦嗎？"
                ]
                follow_up_suggestions = ["了解理由", "個性化推薦", "重新搜尋"]
            
            return {
                "questions": questions[:2],
                "question_type": "recommendation_optimization",
                "confidence": 0.8,
                "follow_up_suggestions": follow_up_suggestions[:4],
                "recommendation_context": {
                    "has_recommendations": bool(last_search_results and last_search_results.get("events")),
                    "recommendation_count": len(last_search_results.get("events", [])) if last_search_results else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating recommending questions: {str(e)}")
            return {
                "questions": ["對這些推薦有什麼想法？"],
                "question_type": "recommendation_optimization",
                "confidence": 0.5,
                "follow_up_suggestions": []
            }
    
    @staticmethod
    async def _generate_deciding_questions(
        context: Dict[str, Any],
        user_profile: Dict[str, Any],
        stage_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成決策階段的問題"""
        try:
            questions = [
                "有需要我提供更多資訊幫助您決定嗎？",
                "想比較一下不同活動的特色嗎？",
                "還有其他考慮因素嗎？",
                "需要我幫您查看活動的報名方式嗎？"
            ]
            
            follow_up_suggestions = [
                "比較活動", "查看報名", "了解詳情", "考慮因素"
            ]
            
            return {
                "questions": questions[:2],
                "question_type": "decision_support",
                "confidence": 0.7,
                "follow_up_suggestions": follow_up_suggestions
            }
            
        except Exception as e:
            logger.error(f"Error generating deciding questions: {str(e)}")
            return {
                "questions": ["有需要我提供更多資訊幫助您決定嗎？"],
                "question_type": "decision_support",
                "confidence": 0.5,
                "follow_up_suggestions": []
            }
    
    @staticmethod
    async def _generate_closing_questions(
        user_profile: Dict[str, Any],
        stage_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成結束階段的問題"""
        try:
            questions = [
                "還有其他需要幫助的嗎？",
                "希望今天的推薦對您有幫助！",
                "祝您參加活動愉快！",
                "歡迎隨時回來搜尋更多活動！"
            ]
            
            follow_up_suggestions = [
                "其他需求", "活動建議", "使用心得"
            ]
            
            return {
                "questions": questions[:2],
                "question_type": "closing",
                "confidence": 0.9,
                "follow_up_suggestions": follow_up_suggestions
            }
            
        except Exception as e:
            logger.error(f"Error generating closing questions: {str(e)}")
            return {
                "questions": ["還有其他需要幫助的嗎？"],
                "question_type": "closing",
                "confidence": 0.5,
                "follow_up_suggestions": []
            }
    
    @staticmethod
    async def should_ask_proactive_question(
        user_message: str,
        bot_response: str,
        context: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        判斷是否應該提出主動式問題
        
        Returns:
            Tuple[bool, str]: (是否應該提問, 提問原因)
        """
        try:
            user_message_lower = user_message.lower()
            bot_response_lower = bot_response.lower()
            
            # 情況1：用戶回應很簡短，可能需要更多引導
            if len(user_message.strip()) < 10:
                return True, "用戶回應簡短，需要更多引導"
            
            # 情況2：用戶表達了模糊的需求
            vague_indicators = ["不知道", "隨便", "都可以", "看看", "沒想法", "不確定"]
            if any(indicator in user_message_lower for indicator in vague_indicators):
                return True, "用戶需求模糊，需要澄清"
            
            # 情況3：機器人提供了搜尋結果，但沒有後續引導
            if "搜尋結果" in bot_response and "?" not in bot_response:
                return True, "提供搜尋結果後需要引導用戶"
            
            # 情況4：用戶表達了興趣但沒有明確行動
            interest_indicators = ["不錯", "有趣", "看起來", "感覺", "好像"]
            if any(indicator in user_message_lower for indicator in interest_indicators):
                return True, "用戶表達興趣，可以深入探索"
            
            # 情況5：對話進行了一段時間但沒有實質進展
            conversation_history = context.get("conversation_history", [])
            if len(conversation_history) > 6:
                recent_messages = conversation_history[-4:]
                user_messages = [msg for msg in recent_messages if msg.get("role") == "user"]
                if len(user_messages) >= 2:
                    # 檢查是否在重複類似的對話
                    if ProactiveQuestioningService._is_conversation_stagnant(user_messages):
                        return True, "對話停滯，需要新的方向"
            
            # 情況6：用戶詢問開放性問題
            open_questions = ["什麼", "如何", "怎麼", "為什麼", "哪裡", "哪個"]
            if any(q in user_message for q in open_questions):
                return True, "用戶提出開放性問題，可以提供更多選項"
            
            # 默認情況：不需要主動提問
            return False, "當前對話流暢，無需主動提問"
            
        except Exception as e:
            logger.error(f"Error determining if should ask proactive question: {str(e)}")
            return False, "判斷錯誤，保持當前對話"
    
    @staticmethod
    def _is_conversation_stagnant(user_messages: List[Dict[str, Any]]) -> bool:
        """判斷對話是否停滯"""
        try:
            if len(user_messages) < 2:
                return False
            
            # 檢查用戶訊息的相似度
            messages_content = [msg.get("content", "").lower() for msg in user_messages]
            
            # 簡單的相似度檢查：如果用戶重複使用相同的關鍵詞
            all_words = []
            for content in messages_content:
                all_words.extend(content.split())
            
            if len(all_words) == 0:
                return True
            
            # 計算重複詞彙的比例
            unique_words = set(all_words)
            repetition_ratio = 1 - (len(unique_words) / len(all_words))
            
            # 如果重複比例超過60%，認為對話停滯
            return repetition_ratio > 0.6
            
        except Exception as e:
            logger.error(f"Error checking conversation stagnation: {str(e)}")
            return False
    
    @staticmethod
    async def analyze_conversation_stage(
        chat_history: List[Dict[str, Any]], 
        context: Dict[str, Any]
    ) -> str:
        """分析對話階段（委託給ConversationStageService）"""
        return await ConversationStageService.analyze_conversation_stage(chat_history, context) 