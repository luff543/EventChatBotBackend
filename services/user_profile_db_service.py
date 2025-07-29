from typing import Dict, Any, List, Optional
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func
from openai import OpenAI
import openai
from utils.config import OPENAI_API_KEY
from utils.logger import logger
from database import UserProfile, UserInterest, UserPreference, UserBehavior, UserFeedback, ChatSession

client = OpenAI(api_key=OPENAI_API_KEY)

class UserProfileDBService:
    """資料庫版本的用戶畫像服務"""
    
    def __init__(self):
        pass
    
    async def get_user_profile(self, db: Session, session_id: str) -> Dict[str, Any]:
        """從資料庫獲取用戶畫像"""
        try:
            # 查找或創建用戶畫像
            profile = db.query(UserProfile).filter(UserProfile.session_id == session_id).first()
            
            if not profile:
                profile = await self._create_user_profile(db, session_id)
            
            # 構建完整的用戶畫像數據
            profile_data = {
                "session_id": profile.session_id,
                "visit_count": profile.visit_count,
                "total_interactions": profile.total_interactions,
                "satisfaction_score": profile.satisfaction_score,
                "last_activity": profile.last_activity.isoformat() if profile.last_activity else None,
                "created_at": profile.created_at.isoformat() if profile.created_at else None,
                "personality_traits": profile.personality_traits or {},
                "communication_style": profile.communication_style or {},
                "engagement_patterns": profile.engagement_patterns or {},
                "interests": await self._get_user_interests(db, profile.id),
                "activity_preferences": await self._get_user_preferences(db, profile.id),
                "recent_behaviors": await self._get_recent_behaviors(db, profile.id),
                "feedback_history": await self._get_feedback_history(db, profile.id)
            }
            
            return profile_data
            
        except Exception as e:
            logger.error(f"Error getting user profile from database: {str(e)}")
            return self._create_default_profile_data(session_id)
    
    async def update_user_profile(
        self, 
        db: Session,
        session_id: str, 
        new_data: Dict[str, Any],
        update_type: str = "general"
    ) -> Dict[str, Any]:
        """更新用戶畫像到資料庫"""
        try:
            # 獲取或創建用戶畫像
            profile = db.query(UserProfile).filter(UserProfile.session_id == session_id).first()
            if not profile:
                profile = await self._create_user_profile(db, session_id)
            
            # 根據更新類型處理不同的數據
            if update_type == "interests":
                await self._update_interests_db(db, profile.id, new_data)
            elif update_type == "preferences":
                await self._update_preferences_db(db, profile.id, new_data)
            elif update_type == "behavior":
                await self._record_behavior(db, profile.id, new_data)
            elif update_type == "feedback":
                await self._record_feedback(db, profile.id, new_data)
            elif update_type == "personality":
                profile.personality_traits = {**(profile.personality_traits or {}), **new_data.get("personality_traits", {})}
                profile.communication_style = {**(profile.communication_style or {}), **new_data.get("communication_style", {})}
                profile.engagement_patterns = {**(profile.engagement_patterns or {}), **new_data.get("engagement_patterns", {})}
            else:
                # 一般性更新
                if "visit_count" in new_data:
                    profile.visit_count = new_data["visit_count"]
                if "total_interactions" in new_data:
                    profile.total_interactions = new_data["total_interactions"]
                if "satisfaction_score" in new_data:
                    profile.satisfaction_score = new_data["satisfaction_score"]
            
            # 更新最後活動時間
            profile.last_activity = datetime.utcnow()
            profile.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(profile)
            
            logger.info(f"Updated user profile in database for session {session_id}")
            return await self.get_user_profile(db, session_id)
            
        except Exception as e:
            logger.error(f"Error updating user profile in database: {str(e)}")
            db.rollback()
            return await self.get_user_profile(db, session_id)
    
    async def analyze_user_from_conversation(
        self, 
        db: Session,
        session_id: str, 
        chat_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """從對話歷史分析用戶特徵並存入資料庫"""
        try:
            if not chat_history:
                return await self.get_user_profile(db, session_id)
            
            # 提取用戶訊息
            user_messages = [
                msg.get("content", "") for msg in chat_history 
                if msg.get("role") == "user"
            ]
            
            if not user_messages:
                return await self.get_user_profile(db, session_id)
            
            # 嘗試使用GPT分析用戶特徵
            try:
                analysis_prompt = f"""
                請分析以下用戶對話，提取用戶的興趣、偏好和特徵：
                
                用戶訊息：{json.dumps(user_messages, ensure_ascii=False)}
                
                請分析並以JSON格式返回：
                {{
                    "interests": ["興趣1", "興趣2"],
                    "activity_preferences": {{
                        "preferred_categories": ["類別1", "類別2"],
                        "preferred_locations": ["地點1", "地點2"],
                        "preferred_times": ["時間偏好1", "時間偏好2"],
                        "group_preference": "個人/小團體/大團體",
                        "budget_sensitivity": "高/中/低"
                    }},
                    "personality_traits": {{
                        "openness": 0.8,
                        "social_level": 0.6,
                        "adventure_seeking": 0.7,
                        "planning_style": "spontaneous/planned"
                    }},
                    "communication_style": {{
                        "formality": "formal/casual",
                        "detail_preference": "brief/detailed",
                        "question_style": "direct/exploratory"
                    }},
                    "engagement_patterns": {{
                        "response_length": "short/medium/long",
                        "enthusiasm_level": "low/medium/high",
                        "decision_making": "quick/deliberate"
                    }}
                }}
                """
                
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "你是一個專業的用戶行為分析師，請準確分析用戶特徵。"},
                        {"role": "user", "content": analysis_prompt}
                    ],
                    temperature=0.3,
                    max_tokens=800,
                    timeout=15
                )
                
                analysis_result = json.loads(response.choices[0].message.content)
                
            except (openai.APIConnectionError, openai.APITimeoutError, json.JSONDecodeError) as e:
                logger.warning(f"OpenAI API error, using fallback analysis: {str(e)}")
                analysis_result = self._fallback_conversation_analysis(user_messages)
            except Exception as e:
                logger.error(f"Error in GPT analysis, using fallback: {str(e)}")
                analysis_result = self._fallback_conversation_analysis(user_messages)
            
            # 更新用戶畫像到資料庫
            await self.update_user_profile(db, session_id, {
                "interests": analysis_result.get("interests", []),
                "activity_preferences": analysis_result.get("activity_preferences", {}),
                "personality_traits": analysis_result.get("personality_traits", {}),
                "communication_style": analysis_result.get("communication_style", {}),
                "engagement_patterns": analysis_result.get("engagement_patterns", {})
            }, "personality")
            
            # 記錄分析行為
            await self._record_behavior(db, session_id, {
                "behavior_type": "conversation_analysis",
                "analysis_result": analysis_result,
                "message_count": len(user_messages)
            })
            
            return await self.get_user_profile(db, session_id)
            
        except Exception as e:
            logger.error(f"Error analyzing user from conversation: {str(e)}")
            return await self.get_user_profile(db, session_id)
    
    def _fallback_conversation_analysis(self, user_messages: List[str]) -> Dict[str, Any]:
        """備用對話分析（基於關鍵詞）"""
        combined_text = " ".join(user_messages).lower()
        
        # 分析興趣
        interests = []
        interest_keywords = {
            "藝術": ["藝術", "展覽", "美術", "畫展", "藝文", "博物館"],
            "音樂": ["音樂", "演唱會", "音樂會", "演出", "表演"],
            "運動": ["運動", "健身", "瑜伽", "跑步", "球類"],
            "美食": ["美食", "餐廳", "料理", "烹飪", "品酒"],
            "學習": ["學習", "課程", "講座", "工作坊", "研習"],
            "親子": ["親子", "兒童", "家庭", "小孩", "孩子"],
            "戶外": ["戶外", "野餐", "露營", "踏青", "自然"],
            "社交": ["社交", "聚會", "交友", "派對", "聯誼"]
        }
        
        for category, keywords in interest_keywords.items():
            if any(keyword in combined_text for keyword in keywords):
                interests.append(category)
        
        # 分析地點偏好
        locations = []
        location_keywords = ["台北", "新北", "桃園", "台中", "台南", "高雄"]
        for location in location_keywords:
            if location in combined_text:
                locations.append(location)
        
        # 分析社交傾向
        social_indicators = ["朋友", "一起", "團體", "大家", "聚會"]
        social_level = 0.7 if any(indicator in combined_text for indicator in social_indicators) else 0.4
        
        # 分析冒險精神
        adventure_indicators = ["新", "特別", "有趣", "刺激", "體驗"]
        adventure_seeking = 0.7 if any(indicator in combined_text for indicator in adventure_indicators) else 0.5
        
        return {
            "interests": interests[:3],  # 最多3個興趣
            "activity_preferences": {
                "preferred_categories": interests,
                "preferred_locations": locations,
                "preferred_times": [],
                "group_preference": "小團體" if social_level > 0.5 else "個人",
                "budget_sensitivity": "中"
            },
            "personality_traits": {
                "openness": 0.6,
                "social_level": social_level,
                "adventure_seeking": adventure_seeking,
                "planning_style": "planned"
            },
            "communication_style": {
                "formality": "casual",
                "detail_preference": "brief",
                "question_style": "direct"
            },
            "engagement_patterns": {
                "response_length": "medium",
                "enthusiasm_level": "medium",
                "decision_making": "deliberate"
            }
        }
    
    async def get_personalized_recommendations(
        self, 
        db: Session,
        session_id: str, 
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """基於資料庫中的用戶畫像生成個性化推薦"""
        try:
            profile_data = await self.get_user_profile(db, session_id)
            
            # 分析用戶偏好
            interests = profile_data.get("interests", [])
            preferences = profile_data.get("activity_preferences", {})
            personality = profile_data.get("personality_traits", {})
            
            recommendations = {
                "suggested_categories": [],
                "suggested_locations": [],
                "suggested_times": [],
                "personalized_message": "",
                "confidence": 0.0
            }
            
            # 基於興趣推薦類別
            if interests:
                # 按信心度排序，取前3個
                sorted_interests = sorted(interests, key=lambda x: x.get("confidence", 0.5), reverse=True)
                recommendations["suggested_categories"] = [item["interest"] for item in sorted_interests[:3]]
            
            # 基於偏好推薦地點和時間
            if preferences:
                recommendations["suggested_locations"] = preferences.get("preferred_locations", [])
                recommendations["suggested_times"] = preferences.get("preferred_times", [])
            
            # 生成個性化訊息
            social_level = personality.get("social_level", 0.5)
            adventure_seeking = personality.get("adventure_seeking", 0.5)
            
            if social_level > 0.7:
                recommendations["personalized_message"] = "我注意到您喜歡社交活動，為您推薦一些團體活動！"
            elif adventure_seeking > 0.7:
                recommendations["personalized_message"] = "看起來您喜歡冒險，這些新奇的活動可能很適合您！"
            else:
                recommendations["personalized_message"] = "根據您的偏好，這些活動應該很適合您！"
            
            # 計算推薦信心度
            data_completeness = sum([
                len(interests) > 0,
                len(preferences) > 0,
                len(personality) > 0,
                profile_data.get("visit_count", 0) > 1
            ]) / 4
            
            recommendations["confidence"] = data_completeness
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting personalized recommendations: {str(e)}")
            return {
                "suggested_categories": [],
                "suggested_locations": [],
                "suggested_times": [],
                "personalized_message": "讓我為您推薦一些活動！",
                "confidence": 0.0
            }
    
    async def record_user_interaction(
        self,
        db: Session,
        session_id: str,
        interaction_type: str,
        interaction_data: Dict[str, Any]
    ):
        """記錄用戶互動行為"""
        try:
            profile = db.query(UserProfile).filter(UserProfile.session_id == session_id).first()
            if not profile:
                profile = await self._create_user_profile(db, session_id)
            
            # 記錄行為
            await self._record_behavior(db, profile.id, {
                "behavior_type": interaction_type,
                **interaction_data
            })
            
            # 更新互動計數
            profile.total_interactions += 1
            profile.last_activity = datetime.utcnow()
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error recording user interaction: {str(e)}")
            db.rollback()
    
    async def _create_user_profile(self, db: Session, session_id: str) -> UserProfile:
        """創建新的用戶畫像"""
        # 獲取session信息以確定IP地址
        session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
        
        # 計算該IP的歷史session數量來確定visit_count
        visit_count = 1  # 默認為1（新用戶）
        if session and session.ip_address:
            # 查詢該IP在當前session創建之前的session數量
            earlier_sessions_count = (
                db.query(ChatSession)
                .filter(
                    ChatSession.ip_address == session.ip_address,
                    ChatSession.created_at < session.created_at
                )
                .count()
            )
            visit_count = earlier_sessions_count + 1  # 加上當前session
        
        profile = UserProfile(
            session_id=session_id,
            visit_count=visit_count,
            total_interactions=0,
            satisfaction_score=0.0,
            personality_traits={},
            communication_style={},
            engagement_patterns={}
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile
    
    async def _get_user_interests(self, db: Session, profile_id: int) -> List[Dict[str, Any]]:
        """獲取用戶興趣"""
        interests = db.query(UserInterest).filter(UserInterest.profile_id == profile_id).all()
        return [
            {
                "interest": interest.interest,
                "confidence": interest.confidence,
                "source": interest.source,
                "created_at": interest.created_at.isoformat()
            }
            for interest in interests
        ]
    
    async def _get_user_preferences(self, db: Session, profile_id: int) -> Dict[str, Any]:
        """獲取用戶偏好"""
        preferences = db.query(UserPreference).filter(UserPreference.profile_id == profile_id).all()
        
        result = {
            "preferred_categories": [],
            "preferred_locations": [],
            "preferred_times": [],
            "group_preference": None,
            "budget_sensitivity": None
        }
        
        for pref in preferences:
            if pref.preference_type == "category":
                result["preferred_categories"].append(pref.preference_value)
            elif pref.preference_type == "location":
                result["preferred_locations"].append(pref.preference_value)
            elif pref.preference_type == "time":
                result["preferred_times"].append(pref.preference_value)
            elif pref.preference_type == "group_size":
                result["group_preference"] = pref.preference_value
            elif pref.preference_type == "budget":
                result["budget_sensitivity"] = pref.preference_value
        
        return result
    
    async def _get_recent_behaviors(self, db: Session, profile_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """獲取最近的用戶行為"""
        behaviors = (
            db.query(UserBehavior)
            .filter(UserBehavior.profile_id == profile_id)
            .order_by(desc(UserBehavior.timestamp))
            .limit(limit)
            .all()
        )
        
        return [
            {
                "behavior_type": behavior.behavior_type,
                "behavior_data": behavior.behavior_data,
                "timestamp": behavior.timestamp.isoformat()
            }
            for behavior in behaviors
        ]
    
    async def _get_feedback_history(self, db: Session, profile_id: int) -> List[Dict[str, Any]]:
        """獲取用戶反饋歷史"""
        feedbacks = (
            db.query(UserFeedback)
            .filter(UserFeedback.profile_id == profile_id)
            .order_by(desc(UserFeedback.created_at))
            .all()
        )
        
        return [
            {
                "feedback_type": feedback.feedback_type,
                "feedback_value": feedback.feedback_value,
                "rating": feedback.rating,
                "context": feedback.context,
                "created_at": feedback.created_at.isoformat()
            }
            for feedback in feedbacks
        ]
    
    async def _update_interests_db(self, db: Session, profile_id: int, interests_data: Dict[str, Any]):
        """更新用戶興趣到資料庫"""
        interests = interests_data.get("interests", [])
        
        for interest_name in interests:
            # 檢查是否已存在
            existing = db.query(UserInterest).filter(
                and_(
                    UserInterest.profile_id == profile_id,
                    UserInterest.interest == interest_name
                )
            ).first()
            
            if existing:
                # 更新信心度
                existing.confidence = min(existing.confidence + 0.1, 1.0)
                existing.updated_at = datetime.utcnow()
            else:
                # 創建新興趣
                new_interest = UserInterest(
                    profile_id=profile_id,
                    interest=interest_name,
                    confidence=0.7,
                    source="conversation"
                )
                db.add(new_interest)
        
        db.commit()
    
    async def _update_preferences_db(self, db: Session, profile_id: int, preferences_data: Dict[str, Any]):
        """更新用戶偏好到資料庫"""
        activity_preferences = preferences_data.get("activity_preferences", {})
        
        preference_mappings = {
            "preferred_categories": "category",
            "preferred_locations": "location", 
            "preferred_times": "time",
            "group_preference": "group_size",
            "budget_sensitivity": "budget"
        }
        
        for key, pref_type in preference_mappings.items():
            values = activity_preferences.get(key, [])
            if not isinstance(values, list):
                values = [values] if values else []
            
            for value in values:
                if value:
                    # 檢查是否已存在
                    existing = db.query(UserPreference).filter(
                        and_(
                            UserPreference.profile_id == profile_id,
                            UserPreference.preference_type == pref_type,
                            UserPreference.preference_value == str(value)
                        )
                    ).first()
                    
                    if existing:
                        existing.confidence = min(existing.confidence + 0.1, 1.0)
                        existing.updated_at = datetime.utcnow()
                    else:
                        new_preference = UserPreference(
                            profile_id=profile_id,
                            preference_type=pref_type,
                            preference_value=str(value),
                            confidence=0.7
                        )
                        db.add(new_preference)
        
        db.commit()
    
    async def _record_behavior(self, db: Session, profile_id: int, behavior_data: Dict[str, Any]):
        """記錄用戶行為"""
        behavior = UserBehavior(
            profile_id=profile_id,
            behavior_type=behavior_data.get("behavior_type", "general"),
            behavior_data=behavior_data
        )
        db.add(behavior)
        db.commit()
    
    async def _record_feedback(self, db: Session, profile_id: int, feedback_data: Dict[str, Any]):
        """記錄用戶反饋"""
        feedback = UserFeedback(
            profile_id=profile_id,
            feedback_type=feedback_data.get("feedback_type", "general"),
            feedback_value=feedback_data.get("feedback_value", ""),
            rating=feedback_data.get("rating"),
            context=feedback_data.get("context", {})
        )
        db.add(feedback)
        db.commit()
    
    def _create_default_profile_data(self, session_id: str) -> Dict[str, Any]:
        """創建默認用戶畫像數據"""
        return {
            "session_id": session_id,
            "visit_count": 1,
            "total_interactions": 0,
            "satisfaction_score": 0.0,
            "last_activity": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat(),
            "personality_traits": {},
            "communication_style": {},
            "engagement_patterns": {},
            "interests": [],
            "activity_preferences": {
                "preferred_categories": [],
                "preferred_locations": [],
                "preferred_times": [],
                "group_preference": None,
                "budget_sensitivity": None
            },
            "recent_behaviors": [],
            "feedback_history": []
        }
    
    async def get_cross_session_profile(self, db: Session, ip_address: str) -> Dict[str, Any]:
        """獲取跨session的用戶畫像"""
        try:
            # 查找該IP地址的所有session
            profiles = db.query(UserProfile).filter(UserProfile.ip_address == ip_address).all()
            
            if not profiles:
                return self._create_default_profile_data("unknown")
            
            # 整合多個session的數據
            integrated_profile = await self._integrate_profiles(db, profiles)
            return integrated_profile
            
        except Exception as e:
            logger.error(f"Error getting cross-session profile: {str(e)}")
            return self._create_default_profile_data("unknown")

    async def update_user_interest(
        self, 
        db: Session, 
        session_id: str, 
        interest: str, 
        confidence: float = 0.7, 
        source: str = "conversation"
    ):
        """更新用戶興趣"""
        try:
            # 獲取或創建用戶畫像
            profile = db.query(UserProfile).filter(UserProfile.session_id == session_id).first()
            if not profile:
                profile = await self._create_user_profile(db, session_id)
            
            # 檢查是否已存在該興趣
            existing_interest = db.query(UserInterest).filter(
                and_(
                    UserInterest.profile_id == profile.id,
                    UserInterest.interest == interest
                )
            ).first()
            
            if existing_interest:
                # 更新現有興趣的信心度
                existing_interest.confidence = max(existing_interest.confidence, confidence)
                existing_interest.updated_at = datetime.utcnow()
            else:
                # 創建新的興趣記錄
                new_interest = UserInterest(
                    profile_id=profile.id,
                    interest=interest,
                    confidence=confidence,
                    source=source,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(new_interest)
            
            db.commit()
            logger.info(f"Updated user interest '{interest}' for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error updating user interest: {str(e)}")
            db.rollback()

    async def update_activity_preference(
        self, 
        db: Session, 
        session_id: str, 
        preference_type: str, 
        preference_values: List[str]
    ):
        """更新活動偏好"""
        try:
            # 獲取或創建用戶畫像
            profile = db.query(UserProfile).filter(UserProfile.session_id == session_id).first()
            if not profile:
                profile = await self._create_user_profile(db, session_id)
            
            # 檢查是否已存在該偏好類型
            existing_preference = db.query(UserPreference).filter(
                and_(
                    UserPreference.profile_id == profile.id,
                    UserPreference.preference_type == preference_type
                )
            ).first()
            
            if existing_preference:
                # 更新現有偏好值
                current_values = existing_preference.preference_value or []
                if isinstance(current_values, str):
                    current_values = [current_values]
                
                # 合併新值，避免重複
                updated_values = list(set(current_values + preference_values))
                existing_preference.preference_value = updated_values
                existing_preference.updated_at = datetime.utcnow()
            else:
                # 創建新的偏好記錄
                new_preference = UserPreference(
                    profile_id=profile.id,
                    preference_type=preference_type,
                    preference_value=preference_values,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(new_preference)
            
            db.commit()
            logger.info(f"Updated activity preference '{preference_type}' for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error updating activity preference: {str(e)}")
            db.rollback()

    async def update_interaction_stats(self, db: Session, session_id: str):
        """更新互動統計"""
        try:
            # 獲取或創建用戶畫像
            profile = db.query(UserProfile).filter(UserProfile.session_id == session_id).first()
            if not profile:
                profile = await self._create_user_profile(db, session_id)
            
            # 更新互動次數
            profile.total_interactions = (profile.total_interactions or 0) + 1
            profile.last_activity = datetime.utcnow()
            profile.updated_at = datetime.utcnow()
            
            db.commit()
            logger.info(f"Updated interaction stats for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error updating interaction stats: {str(e)}")
            db.rollback()

    async def _integrate_profiles(self, db: Session, profiles: List[UserProfile]) -> Dict[str, Any]:
        """整合多個session的用戶畫像數據"""
        try:
            if not profiles:
                return self._create_default_profile_data("unknown")
            
            # 計算總訪問次數（session數量）
            total_visit_count = len(profiles)
            
            # 計算總互動次數
            total_interactions = sum(profile.total_interactions or 0 for profile in profiles)
            
            # 計算平均滿意度
            satisfaction_scores = [profile.satisfaction_score for profile in profiles if profile.satisfaction_score is not None]
            avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else None
            
            # 獲取最新活動時間
            last_activity = max(profile.last_activity for profile in profiles if profile.last_activity)
            
            # 整合所有興趣
            all_interests = []
            for profile in profiles:
                interests = await self._get_user_interests(db, profile.id)
                all_interests.extend(interests)
            
            # 去重並按信心度排序
            unique_interests = {}
            for interest in all_interests:
                interest_name = interest.get("interest")
                if interest_name not in unique_interests or interest.get("confidence", 0) > unique_interests[interest_name].get("confidence", 0):
                    unique_interests[interest_name] = interest
            
            sorted_interests = sorted(unique_interests.values(), key=lambda x: x.get("confidence", 0), reverse=True)
            
            # 整合偏好
            all_preferences = {}
            for profile in profiles:
                preferences = await self._get_user_preferences(db, profile.id)
                for pref_type, pref_value in preferences.items():
                    if pref_type not in all_preferences:
                        all_preferences[pref_type] = []
                    if isinstance(pref_value, list):
                        all_preferences[pref_type].extend(pref_value)
                    else:
                        all_preferences[pref_type].append(pref_value)
            
            # 去重偏好值
            for pref_type in all_preferences:
                all_preferences[pref_type] = list(set(all_preferences[pref_type]))
            
            return {
                "session_id": "integrated",
                "visit_count": total_visit_count,
                "total_interactions": total_interactions,
                "satisfaction_score": avg_satisfaction,
                "last_activity": last_activity.isoformat() if last_activity else None,
                "interests": sorted_interests,
                "activity_preferences": all_preferences,
                "personality_traits": {},
                "communication_style": {},
                "engagement_patterns": {},
                "recent_behaviors": [],
                "feedback_history": []
            }
            
        except Exception as e:
            logger.error(f"Error integrating profiles: {str(e)}")
            return self._create_default_profile_data("unknown") 