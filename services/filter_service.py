from typing import List, Dict, Any
import re
from utils.logger import logger

class ChatHistoryFilterService:
    """聊天歷史過濾服務"""
    
    @staticmethod
    def filter_markdown_from_chat_history(chat_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        過濾聊天歷史中的 markdown 搜尋結果，避免超過模型 prompt 長度限制
        """
        logger.info(f"=== CHAT HISTORY STRUCTURE DEBUG ===")
        logger.info(f"chat_history type: {type(chat_history)}")
        logger.info(f"chat_history length: {len(chat_history) if chat_history else 0}")
        
        if chat_history:
            for i, entry in enumerate(chat_history[:3]):  # 只打印前3個條目
                logger.info(f"Entry {i}: type={type(entry)}")
                logger.info(f"Entry {i}: keys={list(entry.keys()) if isinstance(entry, dict) else 'Not a dict'}")
                if isinstance(entry, dict):
                    for key, value in entry.items():
                        if isinstance(value, str) and len(value) > 100:
                            logger.info(f"Entry {i}[{key}]: {type(value)} (length: {len(value)}) - {value[:100]}...")
                        else:
                            logger.info(f"Entry {i}[{key}]: {type(value)} - {value}")
                logger.info(f"--- End of Entry {i} ---")
        
        logger.info(f"=== END CHAT HISTORY DEBUG ===")
        
        if not chat_history:
            return chat_history
        
        filtered_history = []
        
        for entry in chat_history:
            if isinstance(entry, dict):
                # 處理標準的聊天格式：{'role': 'user/assistant', 'content': '...'}
                if 'role' in entry and 'content' in entry:
                    content = entry['content']
                    role = entry['role']
                    
                    # 只對 assistant 的回應進行搜尋結果過濾
                    if role == 'assistant' and ChatHistoryFilterService._is_search_result_markdown(content):
                        # 提取搜尋結果的摘要信息
                        summary = ChatHistoryFilterService._extract_search_result_summary(content)
                        filtered_entry = entry.copy()
                        filtered_entry['content'] = summary
                        filtered_history.append(filtered_entry)
                        logger.info(f"Filtered assistant response: {len(content)} chars -> {len(summary)} chars")
                    else:
                        # 保留用戶訊息和非搜尋結果的 assistant 回應
                        filtered_history.append(entry)
                        logger.info(f"Kept {role} message: {len(content)} chars")
                
                # 處理舊格式：{'content': '...'}（向後兼容）
                elif 'content' in entry:
                    content = entry['content']
                    
                    # 檢查是否包含搜尋結果的 markdown 格式
                    if ChatHistoryFilterService._is_search_result_markdown(content):
                        # 提取搜尋結果的摘要信息
                        summary = ChatHistoryFilterService._extract_search_result_summary(content)
                        filtered_entry = entry.copy()
                        filtered_entry['content'] = summary
                        filtered_history.append(filtered_entry)
                        logger.info(f"Filtered legacy format: {len(content)} chars -> {len(summary)} chars")
                    else:
                        # 保留非搜尋結果的內容
                        filtered_history.append(entry)
                        logger.info(f"Kept legacy format: {len(content)} chars")
                else:
                    # 保留沒有 content 字段的條目
                    filtered_history.append(entry)
                    logger.info(f"Kept entry without content field")
            else:
                # 保留非字典格式的條目
                filtered_history.append(entry)
                logger.info(f"Kept non-dict entry: {type(entry)}")
        
        logger.info(f"Filtering complete: {len(chat_history)} -> {len(filtered_history)} entries")
        return filtered_history
    
    @staticmethod
    def _is_search_result_markdown(content: str) -> bool:
        """
        檢查內容是否為搜尋結果的 markdown 格式
        """
        if not isinstance(content, str):
            return False
        
        # 檢查是否包含搜尋結果的特徵標記
        search_indicators = [
            "## 搜尋結果",
            "### 活動列表", 
            "### 搜尋條件",
            "共找到",
            "個活動",
            "本頁顯示",
            "- 活動日期：",
            "- 活動地點：",
            "- 城市：",
            "- 區域：",
            "- 類別：",
            "- 適合年齡：",
            "🔍 關鍵字：",
            "📍 城市：",
            "📅 開始日期：",
            "📅 結束日期：",
            "↕️ 排序方式：",
            "以下是其中的幾個選擇：",
            "為您找到一些",
            "活動推薦"
        ]
        
        # 如果包含多個搜尋結果特徵，則認為是搜尋結果
        indicator_count = sum(1 for indicator in search_indicators if indicator in content)
        
        # 檢查是否包含大量的 markdown 連結格式 [text](url)
        markdown_links = re.findall(r'\[([^\]]+)\]\([^)]+\)', content)
        
        # 檢查是否包含編號列表格式的活動 (1. [活動名稱](連結))
        numbered_activity_pattern = re.findall(r'\d+\.\s*\[([^\]]+)\]\([^)]+\)', content)
        
        # 檢查是否包含活動相關的關鍵字
        activity_keywords = [
            "活動名稱", "活動日期", "活動地點", "活動時間", 
            "報名", "參加", "舉辦", "展覽", "演出", "課程"
        ]
        activity_keyword_count = sum(1 for keyword in activity_keywords if keyword in content)
        
        # 判斷標準：
        # 1. 包含3個以上的特徵標記，或者
        # 2. 包含5個以上的 markdown 連結，或者
        # 3. 包含3個以上的編號活動列表，或者
        # 4. 包含多個活動關鍵字且有 markdown 連結
        is_search_result = (
            indicator_count >= 3 or 
            len(markdown_links) >= 5 or 
            len(numbered_activity_pattern) >= 3 or
            (activity_keyword_count >= 3 and len(markdown_links) >= 2)
        )
        
        if is_search_result:
            logger.info(f"Detected search result: indicators={indicator_count}, links={len(markdown_links)}, numbered_activities={len(numbered_activity_pattern)}, activity_keywords={activity_keyword_count}")
        
        return is_search_result
    
    @staticmethod
    def _extract_search_result_summary(content: str) -> str:
        """
        從搜尋結果中提取摘要信息
        """
        try:
            lines = content.split('\n')
            summary_parts = []
            
            # 提取搜尋結果統計信息
            for line in lines:
                if "共找到" in line and "個活動" in line:
                    summary_parts.append(line.strip())
                    break
                elif "為您找到" in line or "以下是其中的" in line:
                    summary_parts.append(line.strip())
                    break
            
            # 提取搜尋條件
            in_search_conditions = False
            search_conditions = []
            for line in lines:
                if "### 搜尋條件" in line:
                    in_search_conditions = True
                    continue
                elif in_search_conditions and line.strip():
                    if line.startswith("🔍") or line.startswith("📍") or line.startswith("📅"):
                        search_conditions.append(line.strip())
                    elif not line.startswith(" ") and "###" in line:
                        break
            
            if search_conditions:
                summary_parts.append("搜尋條件：" + "，".join(search_conditions))
            
            # 提取活動名稱（支援多種格式）
            activity_names = []
            
            # 格式1: 編號列表 markdown 連結 (1. [活動名稱](連結))
            numbered_links = re.findall(r'\d+\.\s*\[([^\]]+)\]', content)
            activity_names.extend(numbered_links[:3])
            
            # 格式2: 如果沒有編號列表，嘗試提取所有 markdown 連結
            if not activity_names:
                all_links = re.findall(r'\[([^\]]+)\]\([^)]+\)', content)
                # 過濾掉可能不是活動名稱的連結（如地點連結）
                filtered_links = [link for link in all_links if not any(keyword in link for keyword in ['maps', 'google', 'gps'])]
                activity_names.extend(filtered_links[:3])
            
            # 格式3: 如果還是沒有，嘗試提取活動相關的關鍵句子
            if not activity_names:
                for line in lines:
                    if any(keyword in line for keyword in ['活動', '展覽', '演出', '課程', '講座']):
                        # 提取可能的活動名稱
                        clean_line = line.strip().replace('*', '').replace('#', '').replace('-', '').strip()
                        if len(clean_line) > 5 and len(clean_line) < 50:
                            activity_names.append(clean_line)
                            if len(activity_names) >= 3:
                                break
            
            if activity_names:
                summary_parts.append(f"主要活動：{', '.join(activity_names)}")
            
            # 提取地點信息
            location_info = []
            for line in lines:
                if "高雄" in line or "台北" in line or "台中" in line or "台南" in line:
                    if any(keyword in line for keyword in ['城市', '地點', '位於']):
                        location_info.append(line.strip())
                        break
            
            if location_info:
                summary_parts.append(f"地點信息：{location_info[0]}")
            
            # 提取活動類型信息
            activity_types = []
            type_keywords = ['親子', '戶外', '展覽', '音樂', '藝術', '運動', '教育', '文化']
            for keyword in type_keywords:
                if keyword in content:
                    activity_types.append(keyword)
            
            if activity_types:
                summary_parts.append(f"活動類型：{', '.join(activity_types[:3])}")
            
            # 組合摘要
            if summary_parts:
                summary = "搜尋結果摘要：" + "；".join(summary_parts)
                logger.info(f"Generated summary: {summary}")
                return summary
            else:
                return "搜尋結果（已簡化）"
                
        except Exception as e:
            logger.error(f"Error extracting search result summary: {str(e)}")
            return "搜尋結果（已簡化）" 