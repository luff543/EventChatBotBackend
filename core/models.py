from typing import List, Dict, Any, Optional, Callable, Awaitable
from pydantic import BaseModel

class ConversationContext(BaseModel):
    """對話上下文管理"""
    user_preferences: Dict[str, Any] = {}
    conversation_history: List[Dict[str, Any]] = []
    current_topic: Optional[str] = None
    user_intent: Optional[str] = None
    entities_mentioned: List[Dict[str, Any]] = []
    follow_up_questions: List[str] = []

class Tool(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Optional[Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]] = None
    priority: int = 1  # 工具優先級
    category: str = "general"  # 工具分類

    def dict(self, *args, **kwargs):
        """
        重寫 dict 方法，排除方法屬性
        """
        d = super().dict(*args, **kwargs)
        # 移除方法屬性
        d.pop('handler', None)
        return d 