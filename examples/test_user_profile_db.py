#!/usr/bin/env python3
"""
測試資料庫版本的用戶畫像服務
演示完整的用戶畫像管理功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from sqlalchemy.orm import sessionmaker
from database import engine, UserProfile, UserInterest, UserPreference, UserBehavior, UserFeedback
from services.user_profile_db_service import UserProfileDBService
from utils.logger import logger
import json
from datetime import datetime

# 創建資料庫會話
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

async def test_basic_profile_operations():
    """測試基本的用戶畫像操作"""
    print("\n=== 測試基本用戶畫像操作 ===")
    
    service = UserProfileDBService()
    db = SessionLocal()
    
    try:
        test_session_id = "test_session_123"
        
        # 1. 獲取用戶畫像（應該創建新的）
        print("1. 獲取用戶畫像...")
        profile = await service.get_user_profile(db, test_session_id)
        print(f"   用戶畫像: {json.dumps(profile, indent=2, ensure_ascii=False)}")
        
        # 2. 更新用戶興趣
        print("\n2. 更新用戶興趣...")
        interests_data = {
            "interests": ["音樂會", "藝術展覽", "戶外活動"]
        }
        await service.update_user_profile(db, test_session_id, interests_data, "interests")
        
        # 3. 更新用戶偏好
        print("\n3. 更新用戶偏好...")
        preferences_data = {
            "activity_preferences": {
                "preferred_categories": ["音樂", "藝術"],
                "preferred_locations": ["台北", "新北"],
                "preferred_times": ["週末", "晚上"],
                "group_preference": "小團體",
                "budget_sensitivity": "中"
            }
        }
        await service.update_user_profile(db, test_session_id, preferences_data, "preferences")
        
        # 4. 更新個性特徵
        print("\n4. 更新個性特徵...")
        personality_data = {
            "personality_traits": {
                "openness": 0.8,
                "social_level": 0.7,
                "adventure_seeking": 0.6,
                "planning_style": "planned"
            },
            "communication_style": {
                "formality": "casual",
                "detail_preference": "detailed",
                "question_style": "exploratory"
            },
            "engagement_patterns": {
                "response_length": "medium",
                "enthusiasm_level": "high",
                "decision_making": "deliberate"
            }
        }
        await service.update_user_profile(db, test_session_id, personality_data, "personality")
        
        # 5. 記錄用戶行為
        print("\n5. 記錄用戶行為...")
        await service.record_user_interaction(db, test_session_id, "search", {
            "search_query": "台北音樂會",
            "results_count": 15,
            "clicked_events": ["event_1", "event_2"]
        })
        
        # 6. 記錄用戶反饋
        print("\n6. 記錄用戶反饋...")
        feedback_data = {
            "feedback_type": "satisfaction",
            "feedback_value": "很滿意推薦的活動",
            "rating": 4.5,
            "context": {"event_id": "event_1", "recommendation_type": "personalized"}
        }
        await service.update_user_profile(db, test_session_id, feedback_data, "feedback")
        
        # 7. 獲取更新後的完整畫像
        print("\n7. 獲取更新後的完整用戶畫像...")
        updated_profile = await service.get_user_profile(db, test_session_id)
        print(f"   更新後的用戶畫像:")
        print(f"   - 訪問次數: {updated_profile['visit_count']}")
        print(f"   - 總互動次數: {updated_profile['total_interactions']}")
        print(f"   - 興趣數量: {len(updated_profile['interests'])}")
        print(f"   - 偏好類別: {updated_profile['activity_preferences']['preferred_categories']}")
        print(f"   - 個性特徵: {updated_profile['personality_traits']}")
        print(f"   - 最近行為數量: {len(updated_profile['recent_behaviors'])}")
        print(f"   - 反饋歷史數量: {len(updated_profile['feedback_history'])}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in basic profile operations test: {str(e)}")
        return False
    finally:
        db.close()

async def test_conversation_analysis():
    """測試對話分析功能"""
    print("\n=== 測試對話分析功能 ===")
    
    service = UserProfileDBService()
    db = SessionLocal()
    
    try:
        test_session_id = "test_conversation_456"
        
        # 模擬對話歷史
        chat_history = [
            {"role": "user", "content": "你好，我想找一些音樂活動"},
            {"role": "assistant", "content": "您好！我可以幫您找音樂活動。您偏好什麼類型的音樂呢？"},
            {"role": "user", "content": "我喜歡古典音樂和爵士樂，最好是在台北的室內場地"},
            {"role": "assistant", "content": "好的，我為您搜尋台北的古典音樂和爵士樂活動..."},
            {"role": "user", "content": "謝謝！我比較喜歡小型的演出，人不要太多"},
            {"role": "assistant", "content": "了解，我會為您篩選較小型的音樂會..."}
        ]
        
        print("1. 分析對話歷史...")
        analyzed_profile = await service.analyze_user_from_conversation(
            db, test_session_id, chat_history
        )
        
        print("2. 分析結果:")
        print(f"   - 提取的興趣: {[item['interest'] for item in analyzed_profile['interests']]}")
        print(f"   - 偏好地點: {analyzed_profile['activity_preferences']['preferred_locations']}")
        print(f"   - 個性特徵: {analyzed_profile['personality_traits']}")
        print(f"   - 溝通風格: {analyzed_profile['communication_style']}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in conversation analysis test: {str(e)}")
        return False
    finally:
        db.close()

async def test_personalized_recommendations():
    """測試個性化推薦功能"""
    print("\n=== 測試個性化推薦功能 ===")
    
    service = UserProfileDBService()
    db = SessionLocal()
    
    try:
        test_session_id = "test_recommendations_789"
        
        # 先建立一個有豐富數據的用戶畫像
        print("1. 建立用戶畫像...")
        
        # 添加興趣
        interests_data = {"interests": ["古典音樂", "爵士樂", "藝術展覽", "戶外音樂節"]}
        await service.update_user_profile(db, test_session_id, interests_data, "interests")
        
        # 添加偏好
        preferences_data = {
            "activity_preferences": {
                "preferred_categories": ["音樂", "藝術"],
                "preferred_locations": ["台北", "新北", "桃園"],
                "preferred_times": ["週末", "晚上"],
                "group_preference": "小團體",
                "budget_sensitivity": "中"
            }
        }
        await service.update_user_profile(db, test_session_id, preferences_data, "preferences")
        
        # 添加個性特徵
        personality_data = {
            "personality_traits": {
                "openness": 0.9,
                "social_level": 0.6,
                "adventure_seeking": 0.7,
                "planning_style": "planned"
            }
        }
        await service.update_user_profile(db, test_session_id, personality_data, "personality")
        
        print("2. 生成個性化推薦...")
        recommendations = await service.get_personalized_recommendations(
            db, test_session_id, {"current_location": "台北"}
        )
        
        print("3. 推薦結果:")
        print(f"   - 建議類別: {recommendations['suggested_categories']}")
        print(f"   - 建議地點: {recommendations['suggested_locations']}")
        print(f"   - 建議時間: {recommendations['suggested_times']}")
        print(f"   - 個性化訊息: {recommendations['personalized_message']}")
        print(f"   - 信心度: {recommendations['confidence']:.2f}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in personalized recommendations test: {str(e)}")
        return False
    finally:
        db.close()

async def test_data_persistence():
    """測試數據持久化"""
    print("\n=== 測試數據持久化 ===")
    
    service = UserProfileDBService()
    
    try:
        test_session_id = "test_persistence_999"
        
        # 第一次會話：創建數據
        print("1. 第一次會話 - 創建數據...")
        db1 = SessionLocal()
        
        interests_data = {"interests": ["電影", "音樂", "運動"]}
        await service.update_user_profile(db1, test_session_id, interests_data, "interests")
        
        profile1 = await service.get_user_profile(db1, test_session_id)
        print(f"   第一次會話的興趣: {[item['interest'] for item in profile1['interests']]}")
        print(f"   訪問次數: {profile1['visit_count']}")
        
        db1.close()
        
        # 第二次會話：讀取數據
        print("\n2. 第二次會話 - 讀取數據...")
        db2 = SessionLocal()
        
        profile2 = await service.get_user_profile(db2, test_session_id)
        print(f"   第二次會話的興趣: {[item['interest'] for item in profile2['interests']]}")
        print(f"   訪問次數: {profile2['visit_count']}")
        
        # 添加更多興趣
        more_interests = {"interests": ["旅遊", "美食"]}
        await service.update_user_profile(db2, test_session_id, more_interests, "interests")
        
        profile2_updated = await service.get_user_profile(db2, test_session_id)
        print(f"   更新後的興趣: {[item['interest'] for item in profile2_updated['interests']]}")
        
        db2.close()
        
        # 第三次會話：驗證持久化
        print("\n3. 第三次會話 - 驗證持久化...")
        db3 = SessionLocal()
        
        profile3 = await service.get_user_profile(db3, test_session_id)
        print(f"   第三次會話的興趣: {[item['interest'] for item in profile3['interests']]}")
        print(f"   訪問次數: {profile3['visit_count']}")
        
        db3.close()
        
        return True
        
    except Exception as e:
        logger.error(f"Error in data persistence test: {str(e)}")
        return False

async def main():
    """主測試流程"""
    print("🚀 開始測試資料庫版本的用戶畫像服務...")
    
    tests = [
        ("基本用戶畫像操作", test_basic_profile_operations),
        ("對話分析功能", test_conversation_analysis),
        ("個性化推薦功能", test_personalized_recommendations),
        ("數據持久化", test_data_persistence)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"執行測試: {test_name}")
        print(f"{'='*50}")
        
        try:
            result = await test_func()
            results.append((test_name, result))
            
            if result:
                print(f"✅ {test_name} - 測試通過")
            else:
                print(f"❌ {test_name} - 測試失敗")
                
        except Exception as e:
            print(f"❌ {test_name} - 測試異常: {str(e)}")
            results.append((test_name, False))
    
    # 總結
    print(f"\n{'='*50}")
    print("測試總結")
    print(f"{'='*50}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{test_name}: {status}")
    
    print(f"\n總計: {passed}/{total} 測試通過")
    
    if passed == total:
        print("🎉 所有測試都通過了！資料庫用戶畫像服務運行正常。")
        return True
    else:
        print("⚠️  部分測試失敗，請檢查錯誤日誌。")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 