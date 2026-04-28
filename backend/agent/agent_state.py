"""
AI Agent 状态定义

定义AI Agent系统的状态结构，包括对话历史、意图、槽位、知识库、任务状态、工具调用记录等。
"""
from typing import TypedDict, List, Optional, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage


class TaskState(TypedDict):
    """任务状态"""
    task_id: Optional[str]
    task_name: str
    status: str  # pending, in_progress, completed, failed
    steps: List[Dict[str, Any]]
    current_step: int
    result: Optional[str]
    error: Optional[str]


class ToolCall(TypedDict):
    """工具调用记录"""
    tool_name: str
    parameters: Dict[str, Any]
    result: Optional[str]
    timestamp: float
    success: bool


class AgentState(TypedDict):
    """AI Agent 状态"""
    # 对话相关
    session_id: str
    user_id: int
    messages: List[BaseMessage]
    intent: Optional[str]
    slots: Dict[str, Any]
    knowledge: List[Dict[str, Any]]
    response: str
    
    # 任务相关
    current_task: Optional[TaskState]
    task_history: List[TaskState]
    
    # 工具调用相关
    tool_calls: List[ToolCall]
    
    # Agent 状态
    agent_state: str  # idle, thinking, planning, executing, learning
    confidence: float  # 决策置信度
    
    # 学习相关
    learning_data: Dict[str, Any]
    
    # 执行计划
    plan: List[Dict[str, Any]]
    current_plan_index: int


class AgentConfig(TypedDict):
    """Agent 配置"""
    max_steps: int
    timeout: int
    tool_calls_enabled: bool
    learning_enabled: bool
    verbose: bool