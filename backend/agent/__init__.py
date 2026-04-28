"""
Agent模块初始化文件

本模块包含智能待办与日程管理Agent的核心组件：
- agent_state: 状态定义
- agent_config: 配置管理
- agent_decision: 决策系统
- agent_tools: 工具系统
- agent_workflow: 工作流管理
- workflow: 简单任务工作流（兼容）
- llm_config: LLM配置（兼容）
"""
from .agent_state import AgentState, TaskState, ToolCall
from .agent_config import config, ConfigManager, LLMConfig, AgentConfig
from .agent_decision import AgentDecisionSystem, decision_system, llm_client, PlanStep, DecisionResult
from .agent_tools import tool_registry, ToolRegistry, ToolResult, register_all_tools
from .agent_workflow import AgentWorkflow, agent_workflow, process_agent_message, process_agent_message_stream, StreamEvent

# 兼容旧接口
from .llm_config import client, model
from .workflow import workflow, agent

__all__ = [
    # 状态和配置
    "AgentState", "TaskState", "ToolCall",
    "config", "ConfigManager", "LLMConfig", "AgentConfig",
    
    # 决策系统
    "AgentDecisionSystem", "decision_system", "llm_client",
    "PlanStep", "DecisionResult",
    
    # 工具系统
    "tool_registry", "ToolRegistry", "ToolResult", "register_all_tools",
    
    # 工作流
    "AgentWorkflow", "agent_workflow", "process_agent_message", "process_agent_message_stream",
    "StreamEvent",
    
    # 兼容
    "client", "model", "workflow", "agent"
]
