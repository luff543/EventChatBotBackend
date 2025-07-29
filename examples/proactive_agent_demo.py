"""
主動式提問Agent示例
展示如何使用具有主動式提問功能的智能代理
"""

import asyncio
import json
from datetime import datetime
from core.agent import Agent
from utils.logger import logger

async def demo_proactive_agent():
    """演示主動式提問Agent的功能"""
    
    print("=== 主動式提問Agent演示 ===\n")
    
    # 初始化Agent
    agent = Agent(session_id="demo_session_001")
    
    # 模擬對話場景
    scenarios = [
        {
            "name": "新用戶開場",
            "chat_history": [],
            "user_message": "你好"
        },
        {
            "name": "模糊需求探索",
            "chat_history": [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "您好！我是活動推薦助手，很高興為您服務！"}
            ],
            "user_message": "我想找一些活動"
        },
        {
            "name": "興趣澄清",
            "chat_history": [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "您好！我是活動推薦助手，很高興為您服務！"},
                {"role": "user", "content": "我想找一些活動"},
                {"role": "assistant", "content": "您平常喜歡什麼樣的休閒活動？"}
            ],
            "user_message": "我喜歡音樂，但不確定要找什麼"
        },
        {
            "name": "搜尋結果引導",
            "chat_history": [
                {"role": "user", "content": "找台北的音樂活動"},
                {"role": "assistant", "content": "## 搜尋結果\n共找到 15 個活動..."}
            ],
            "user_message": "看起來不錯"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n--- 場景 {i}: {scenario['name']} ---")
        print(f"用戶訊息: {scenario['user_message']}")
        
        try:
            # 處理訊息
            response = await agent.process_message(
                message=scenario['user_message'],
                chat_history=scenario['chat_history']
            )
            
            print(f"Agent回應: {response.get('message', '')}")
            
            # 顯示主動式提問信息
            if response.get('proactive_questions'):
                proactive = response['proactive_questions']
                print(f"\n主動式提問:")
                print(f"  問題類型: {proactive.get('question_type', 'unknown')}")
                print(f"  信心度: {proactive.get('confidence', 0)}")
                
                if proactive.get('questions'):
                    print(f"  生成的問題:")
                    for j, question in enumerate(proactive['questions'], 1):
                        print(f"    {j}. {question}")
                
                if proactive.get('follow_up_suggestions'):
                    print(f"  後續建議: {', '.join(proactive['follow_up_suggestions'])}")
            
            # 顯示用戶畫像信息
            if response.get('user_profile_summary'):
                profile = response['user_profile_summary']
                print(f"\n用戶畫像:")
                print(f"  新用戶: {profile.get('is_new_user', 'unknown')}")
                if profile.get('interests'):
                    print(f"  興趣: {', '.join(profile['interests'])}")
            
            # 顯示對話階段
            if response.get('conversation_stage'):
                print(f"\n對話階段: {response['conversation_stage']}")
            
            print(f"處理成功: {response.get('success', False)}")
            
        except Exception as e:
            print(f"錯誤: {str(e)}")
        
        print("-" * 50)

async def demo_conversation_flow():
    """演示完整的對話流程"""
    
    print("\n\n=== 完整對話流程演示 ===\n")
    
    agent = Agent(session_id="demo_session_002")
    chat_history = []
    
    # 模擬完整對話
    conversation_turns = [
        "你好",
        "我想找一些活動",
        "我喜歡音樂和藝文",
        "台北的活動",
        "這週末的",
        "看起來不錯，想了解更多"
    ]
    
    for turn_num, user_message in enumerate(conversation_turns, 1):
        print(f"\n=== 對話輪次 {turn_num} ===")
        print(f"用戶: {user_message}")
        
        try:
            response = await agent.process_message(
                message=user_message,
                chat_history=chat_history
            )
            
            print(f"Agent: {response.get('message', '')}")
            
            # 更新對話歷史
            chat_history.append({"role": "user", "content": user_message})
            chat_history.append({"role": "assistant", "content": response.get('message', '')})
            
            # 顯示主動式提問信息
            if response.get('enhanced_with_questions'):
                print("✨ 此回應包含主動式提問")
            
            if response.get('proactive_questions'):
                proactive = response['proactive_questions']
                print(f"📊 問題分析: {proactive.get('question_type', 'unknown')} (信心度: {proactive.get('confidence', 0)})")
            
        except Exception as e:
            print(f"❌ 錯誤: {str(e)}")

async def demo_stage_analysis():
    """演示對話階段分析"""
    
    print("\n\n=== 對話階段分析演示 ===\n")
    
    from services.conversation_stage_service import ConversationStageService
    
    # 不同階段的對話歷史示例
    stage_examples = {
        "opening": [
            {"role": "user", "content": "你好"},
        ],
        "exploring": [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "您好！"},
            {"role": "user", "content": "我想找活動"},
            {"role": "assistant", "content": "您喜歡什麼類型的活動？"},
        ],
        "clarifying": [
            {"role": "user", "content": "我想找音樂活動"},
            {"role": "assistant", "content": "您指的是演唱會還是音樂課程？"},
            {"role": "user", "content": "嗯...不太確定"},
        ],
        "searching": [
            {"role": "user", "content": "找台北的演唱會"},
            {"role": "assistant", "content": "正在搜尋台北的演唱會..."},
        ],
        "recommending": [
            {"role": "user", "content": "找台北的演唱會"},
            {"role": "assistant", "content": "## 搜尋結果\n找到了5個演唱會活動..."},
            {"role": "user", "content": "看起來不錯"},
        ]
    }
    
    for expected_stage, history in stage_examples.items():
        try:
            analyzed_stage = await ConversationStageService.analyze_conversation_stage(history)
            status = "✅" if analyzed_stage == expected_stage else "❌"
            print(f"{status} 預期階段: {expected_stage}, 分析結果: {analyzed_stage}")
        except Exception as e:
            print(f"❌ 分析階段 {expected_stage} 時發生錯誤: {str(e)}")

async def main():
    """主函數"""
    try:
        await demo_proactive_agent()
        await demo_conversation_flow()
        await demo_stage_analysis()
        
        print("\n\n=== 演示完成 ===")
        print("主動式提問Agent的主要特色:")
        print("1. 🎯 智能對話階段識別")
        print("2. 🤖 個性化問題生成")
        print("3. 👤 動態用戶畫像建立")
        print("4. 💬 上下文感知的主動提問")
        print("5. 🔄 自適應對話流程管理")
        
    except Exception as e:
        logger.error(f"演示過程中發生錯誤: {str(e)}")
        print(f"❌ 演示失敗: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 