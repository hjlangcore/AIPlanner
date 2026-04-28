"""
AI Agent 工作流

基于模块化架构的 AI Agent 工作流实现，支持：
- 任务处理（同步/流式）
- 状态管理（会话状态、执行计划）
- 工具调用跟踪
- 学习数据分析

工作流程：
1. 保存用户消息
2. 加载历史对话
3. 分析用户任务
4. 制定执行计划
5. 逐步执行工具
6. 生成回复
7. 学习与优化

支持 SSE 流式输出，实时返回处理进度。
"""
import json
import time
import logging
from typing import Dict, Any, List, Optional, Iterator, Generator
from dataclasses import dataclass

from langchain_core.messages import HumanMessage, AIMessage

from .agent_decision import AgentDecisionSystem, PlanStep
from .agent_tools import tool_registry
from .agent_config import config
from ..db.db_handler import db

# 配置日志
logger = logging.getLogger(__name__)


@dataclass
class WorkflowState:
    """工作流状态"""
    session_id: str
    user_id: int
    messages: List[Any]
    plan: List[Dict[str, Any]]
    current_plan_index: int
    tool_calls: List[Dict[str, Any]]
    agent_state: str
    confidence: float
    learning_data: Dict[str, Any]
    response: str
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "messages": self.messages,
            "plan": self.plan,
            "current_plan_index": self.current_plan_index,
            "tool_calls": self.tool_calls,
            "agent_state": self.agent_state,
            "confidence": self.confidence,
            "learning_data": self.learning_data,
            "response": self.response
        }


@dataclass
class StreamEvent:
    """流式事件"""
    step: str
    message: str
    progress: float
    data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "message": self.message,
            "progress": self.progress,
            "data": self.data
        }


class AgentWorkflow:
    """Agent 工作流管理器"""
    
    def __init__(self):
        self.decision_system = AgentDecisionSystem()
        logger.info("Agent Workflow 初始化完成")
    
    def process_message(
        self,
        session_id: str,
        user_id: int,
        message: str
    ) -> Dict[str, Any]:
        """处理消息（非流式）
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            message: 用户消息
        
        Returns:
            处理结果字典
        """
        try:
            # 1. 保存用户消息
            logger.info(f"处理消息: session={session_id}, message={message[:50]}...")
            db.add_chat_message(session_id, "user", message)
            
            # 2. 加载历史消息
            history = db.get_session_messages(session_id, limit=config.agent.history_limit)
            messages = self._convert_history(history)
            
            # 3. 分析任务
            state = {
                "session_id": session_id,
                "user_id": user_id,
                "messages": messages
            }
            
            decision_result = self.decision_system.analyze_task(state)
            plan = decision_result.plan
            
            logger.info(f"任务分析完成: {len(plan)} 个步骤")
            
            # 4. 执行计划
            tool_results = self.decision_system.execute_plan(plan)
            
            # 5. 生成响应
            plan_dicts = [p.to_dict() for p in plan]
            response = self.decision_system.generate_response(state, plan, tool_results)
            
            # 6. 学习
            learning_data = self.decision_system.learn_from_interaction(plan, tool_results)
            
            # 7. 保存助手消息
            db.add_chat_message(session_id, "assistant", response)
            
            # 8. 构建返回结果
            result = {
                "response": response,
                "agent_state": "idle",
                "tool_calls": [
                    {
                        "tool_name": r.get("tool_name"),
                        "parameters": r.get("parameters", {}),
                        "result": json.dumps(r.get("result", {})),
                        "timestamp": time.time(),
                        "success": r.get("success", False)
                    }
                    for r in tool_results if r.get("tool_name")
                ],
                "plan": plan_dicts,
                "learning_data": learning_data
            }
            
            logger.info(f"消息处理完成: response={response[:50]}...")
            return result
            
        except Exception as e:
            logger.error(f"处理消息失败: {e}", exc_info=True)
            return {
                "response": f"抱歉，处理您的请求时出现错误: {str(e)[:100]}",
                "agent_state": "error",
                "tool_calls": [],
                "plan": [],
                "learning_data": {"error": str(e)}
            }
    
    def process_message_stream(
        self,
        session_id: str,
        user_id: int,
        message: str
    ) -> Generator[StreamEvent, None, None]:
        """处理消息（流式）
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            message: 用户消息
        
        Yields:
            StreamEvent: 流式事件
        """
        try:
            # 1. 保存用户消息
            logger.info(f"[Stream] 处理消息: session={session_id}")
            db.add_chat_message(session_id, "user", message)
            
            yield StreamEvent(
                step="start",
                message="正在分析您的请求...",
                progress=10
            )
            
            # 2. 加载历史消息
            history = db.get_session_messages(session_id, limit=config.agent.history_limit)
            messages = self._convert_history(history)
            
            # 3. 分析任务
            state = {
                "session_id": session_id,
                "user_id": user_id,
                "messages": messages
            }
            
            yield StreamEvent(
                step="analyzing",
                message="正在分析任务...",
                progress=20
            )
            
            decision_result = self.decision_system.analyze_task(state)
            plan = decision_result.plan
            
            yield StreamEvent(
                step="planning",
                message=f"已制定执行计划，包含 {len(plan)} 个步骤",
                progress=30,
                data={"plan": [p.to_dict() for p in plan], "reasoning": decision_result.reasoning}
            )
            
            # 4. 执行计划
            tool_results = []
            for i, step in enumerate(plan):
                progress = 30 + (i / max(len(plan), 1)) * 40
                
                yield StreamEvent(
                    step="executing",
                    message=f"执行步骤 {i+1}/{len(plan)}: {step.description}",
                    progress=progress,
                    data={"step": step.to_dict()}
                )
                
                if step.tool:
                    # 修正参数，确保参数名与工具定义一致
                    fixed_params = self.decision_system._fix_parameters(step.tool, step.parameters or {})
                    result = tool_registry.execute_tool(
                        step.tool,
                        fixed_params,
                        max_retries=3
                    )
                    
                    tool_results.append({
                        "step": step.step,
                        "tool_name": step.tool,
                        "parameters": step.parameters,
                        "result": result.to_dict(),
                        "success": result.success
                    })
                    
                    yield StreamEvent(
                        step="tool_result",
                        message=f"步骤 {i+1} {'成功' if result.success else '失败'}",
                        progress=progress + 10,
                        data={
                            "tool_result": {
                                **result.to_dict(),
                                "tool_name": step.tool,
                                "parameters": fixed_params
                            }
                        }
                    )
            
            # 5. 生成响应
            yield StreamEvent(
                step="generating",
                message="正在生成回复...",
                progress=80
            )
            
            response = self.decision_system.generate_response(state, plan, tool_results)
            
            # 6. 学习
            learning_data = self.decision_system.learn_from_interaction(plan, tool_results)
            
            # 7. 保存助手消息
            db.add_chat_message(session_id, "assistant", response)
            
            # 8. 完成
            yield StreamEvent(
                step="completed",
                message="处理完成",
                progress=100,
                data={
                    "response": response,
                    "learning_data": learning_data
                }
            )
            
            logger.info(f"[Stream] 处理完成: response={response[:50]}...")
            
        except Exception as e:
            logger.error(f"[Stream] 处理失败: {e}", exc_info=True)
            yield StreamEvent(
                step="error",
                message=f"处理失败: {str(e)[:100]}",
                progress=0,
                data={"error": str(e)}
            )
    
    def _convert_history(self, history: List[tuple]) -> List[Any]:
        """转换历史消息为 LangChain 消息格式"""
        messages = []
        for h in history:
            role, content = h[0], h[1]
            if role == 'user':
                messages.append(HumanMessage(content=content))
            else:
                messages.append(AIMessage(content=content))
        return messages


# 创建全局工作流实例
agent_workflow = AgentWorkflow()


# ==================== 兼容旧接口 ====================

def process_agent_message(session_id: str, user_id: int, message: str) -> Dict[str, Any]:
    """处理 Agent 消息（兼容旧接口）
    
    Args:
        session_id: 会话ID
        user_id: 用户ID
        message: 用户消息
    
    Returns:
        处理结果字典
    """
    return agent_workflow.process_message(session_id, user_id, message)


def process_agent_message_stream(session_id: str, user_id: int, message: str) -> Generator[Dict[str, Any], None, None]:
    """流式处理 Agent 消息（兼容旧接口）
    
    Args:
        session_id: 会话ID
        user_id: 用户ID
        message: 用户消息
    
    Yields:
        处理状态字典
    """
    for event in agent_workflow.process_message_stream(session_id, user_id, message):
        yield event.to_dict()
