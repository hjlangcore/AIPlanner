"""
Agent 决策系统

实现 AI Agent 的核心决策逻辑，包括：
1. 任务分析 - 理解用户意图，识别关键信息
2. 计划生成 - 制定执行步骤和工具调用计划
3. 工具选择 - 根据任务需求选择合适的工具
4. 响应生成 - 基于执行结果生成自然语言回复
5. 交互学习 - 从每次交互中学习改进

该模块是 Agent 的"大脑"，协调其他模块完成智能对话和任务处理。
"""
import json
import re
import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from openai import OpenAI
from dotenv import load_dotenv
import os

# 加载环境变量
import os as _os
_current_dir = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_project_root = _os.path.dirname(_current_dir)
_env_path = _os.path.join(_project_root, ".env")
load_dotenv(_env_path)

from .agent_tools import tool_registry
from .agent_config import config, SystemPrompts
from .llm_config import agent_llm_config

# 配置日志
logger = logging.getLogger(__name__)


@dataclass
class PlanStep:
    """计划步骤"""
    step: int
    description: str
    tool: Optional[str] = None
    parameters: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "description": self.description,
            "tool": self.tool,
            "parameters": self.parameters
        }


@dataclass
class DecisionResult:
    """决策结果"""
    plan: List[PlanStep]
    reasoning: str
    success: bool = True
    error: Optional[str] = None


class LLMClient:
    """LLM 客户端封装"""
    
    _instance: Optional['LLMClient'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        # 使用 Agent 专用 LLM 配置（已在 agent_llm_config 中处理 fallback）
        self.client = agent_llm_config.client
        self.model = agent_llm_config.model
        logger.info(f"Agent LLM Client 初始化完成: model={self.model}")
    
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """发送聊天请求"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature
            )
            content = response.choices[0].message.content
            if content is None:
                raise ValueError("LLM 返回内容为空")
            return content
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise


# 全局 LLM 客户端
llm_client = LLMClient()


class AgentDecisionSystem:
    """Agent 决策系统
    
    核心决策逻辑：
    1. 分析用户意图
    2. 生成执行计划
    3. 选择合适工具
    4. 生成响应
    """
    
    def __init__(self):
        self.tools = tool_registry.get_all_tools()
        self.tools_info = tool_registry.get_tools_info()
        logger.info(f"Agent Decision System 初始化完成，共 {len(self.tools)} 个工具")
    
    def analyze_task(self, state: Dict[str, Any]) -> DecisionResult:
        """分析任务并生成执行计划
        
        Args:
            state: Agent 状态，包含 messages 等信息
        
        Returns:
            DecisionResult: 决策结果
        """
        try:
            # 获取用户最新消息
            messages = state.get('messages', [])
            if not messages:
                return DecisionResult(
                    plan=[],
                    reasoning="无用户消息",
                    success=False,
                    error="无用户消息"
                )
            
            last_message = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])
            
            # 检查是否只是闲聊/问候
            greeting_keywords = ['你好', 'hello', 'hi', '嗨', '在吗', '早上好', '晚上好', '再见', '拜拜']
            is_greeting = any(kw in last_message.lower() for kw in greeting_keywords)
            
            if is_greeting and len(last_message) < 20:
                return DecisionResult(
                    plan=[],
                    reasoning="用户只是问候，直接回复即可"
                )
            
            # 构建提示词（传入当前日期）
            current_date = datetime.now().strftime("%Y-%m-%d")
            prompt = SystemPrompts.DECISION_PROMPT.format(
                tools_info=self.tools_info,
                current_date=current_date
            )
            
            # 调用 LLM
            messages_to_send = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": last_message}
            ]
            
            response_content = llm_client.chat(messages_to_send)
            
            # 解析响应
            plan, reasoning = self._parse_llm_response(response_content)
            
            logger.info(f"任务分析完成: {len(plan)} 个步骤, reasoning={reasoning[:50]}...")
            
            return DecisionResult(
                plan=plan,
                reasoning=reasoning
            )
            
        except Exception as e:
            logger.error(f"任务分析失败: {e}")
            return DecisionResult(
                plan=[PlanStep(
                    step=1,
                    description="直接回答用户问题",
                    tool=None,
                    parameters={}
                )],
                reasoning=f"分析失败，使用默认响应: {str(e)[:50]}",
                success=False,
                error=str(e)
            )
    
    def _parse_llm_response(self, content: str) -> tuple[List[PlanStep], str]:
        """解析 LLM 响应
        
        Args:
            content: LLM 返回的原始内容
        
        Returns:
            (plan, reasoning) 元组
        """
        plan = []
        reasoning = ""
        
        # 尝试直接解析 JSON
        try:
            data = json.loads(content)
            reasoning = data.get("reasoning", "")
            plan_data = data.get("plan", [])
            
            for i, step_data in enumerate(plan_data):
                plan.append(PlanStep(
                    step=i + 1,
                    description=step_data.get("description", ""),
                    tool=step_data.get("tool"),
                    parameters=step_data.get("parameters", {})
                ))
            
            return plan, reasoning
            
        except json.JSONDecodeError:
            pass
        
        # 尝试正则提取 JSON
        json_patterns = [
            r'\{[^{}]*(?:\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}[^{}]*)*\}',  # 嵌套 JSON
            r'```json\s*(\{.*\})\s*```',  # 代码块中的 JSON
            r'```\s*(\{.*\})\s*```',  # 任意代码块
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            for match in matches:
                try:
                    data = json.loads(match if '(' not in pattern else match)
                    reasoning = data.get("reasoning", "")
                    plan_data = data.get("plan", [])
                    
                    for i, step_data in enumerate(plan_data):
                        plan.append(PlanStep(
                            step=i + 1,
                            description=step_data.get("description", ""),
                            tool=step_data.get("tool"),
                            parameters=step_data.get("parameters", {})
                        ))
                    
                    if plan:
                        return plan, reasoning
                        
                except (json.JSONDecodeError, KeyError):
                    continue
        
        # 解析失败，返回空计划
        logger.warning(f"无法解析 LLM 响应: {content[:100]}...")
        return plan, "无法解析计划，使用默认响应"
    
    def _parse_relative_date(self, date_str: str) -> Optional[datetime]:
        """解析相对日期表达
        
        Args:
            date_str: 日期字符串，可能包含"明天"、"下周二"等相对表达
            
        Returns:
            解析后的datetime对象，如果无法解析则返回None
        """
        now = datetime.now()
        date_str = date_str.strip()
        
        # 明天/后天/大后天
        if "明天" in date_str or "明日" in date_str:
            return now + timedelta(days=1)
        if "后天" in date_str:
            return now + timedelta(days=2)
        if "大后天" in date_str or "外后天" in date_str:
            return now + timedelta(days=3)
        
        # X天后/几天后
        days_match = re.search(r'(\d+)\s*天[后之]后?', date_str)
        if days_match:
            days = int(days_match.group(1))
            return now + timedelta(days=days)
        
        # 下周X
        next_week_match = re.search(r'下周([一二三四五六日天])', date_str)
        if next_week_match:
            weekday_map = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}
            target_weekday = weekday_map[next_week_match.group(1)]
            days_ahead = target_weekday - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7  # 下周
            days_ahead += 7  # 下周（再加7天）
            return now + timedelta(days=days_ahead)
        
        # 本周X
        this_week_match = re.search(r'本周([一二三四五六日天])', date_str)
        if this_week_match:
            weekday_map = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}
            target_weekday = weekday_map[this_week_match.group(1)]
            days_ahead = target_weekday - now.weekday()
            if days_ahead < 0:
                days_ahead += 7  # 已经是下周了
            return now + timedelta(days=days_ahead)
        
        # 下个月/本月
        if "下个月" in date_str or "下月" in date_str:
            # 简化：返回下个月同一天（如果可能）
            if now.month == 12:
                return now.replace(year=now.year+1, month=1)
            else:
                return now.replace(month=now.month+1)
        
        return None
    
    def _fix_parameters(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """修正工具参数名和值，确保与工具定义一致
        
        Args:
            tool_name: 工具名称
            parameters: 原始参数
            
        Returns:
            修正后的参数
        """
        if not parameters:
            return {}
        
        fixed = dict(parameters)
        
        if tool_name == "create_task":
            # 参数名映射：将常见的错误参数名修正为正确的参数名
            name_mapping = {
                "name": "task_name",
                "title": "task_name",
                "task": "task_name",
                "content": "task_name",
                "date": "deadline",
                "due_date": "deadline",
                "due": "deadline",
                "time": "deadline",
                "level": "priority",
                "urgency": "priority",
            }
            
            for old_key, new_key in name_mapping.items():
                if old_key in fixed and new_key not in fixed:
                    fixed[new_key] = fixed.pop(old_key)
                    logger.info(f"参数名修正: {old_key} -> {new_key}")
            
            # 优先级映射：将英文/别名映射为中文
            if "priority" in fixed and fixed["priority"] is not None:
                priority_map = {
                    "high": "高", "urgent": "高", "重要": "高", "紧急": "高",
                    "medium": "中", "normal": "中", "普通": "中", "一般": "中",
                    "low": "低", "minor": "低", "不重要": "低", "次要": "低",
                }
                p = str(fixed["priority"]).lower().strip()
                if p in priority_map:
                    fixed["priority"] = priority_map[p]
                    logger.info(f"优先级映射: {p} -> {fixed['priority']}")
                elif fixed["priority"] not in ["高", "中", "低"]:
                    logger.warning(f"未知优先级 '{fixed['priority']}'，使用默认值 '中'")
                    fixed["priority"] = "中"
            
            # 日期格式校验和修正
            if "deadline" in fixed and fixed["deadline"] is not None:
                date_str = str(fixed["deadline"]).strip()
                
                # 1. 尝试解析相对日期（如"明天"、"下周二"）
                relative_date = self._parse_relative_date(date_str)
                if relative_date:
                    fixed["deadline"] = relative_date.strftime("%Y-%m-%d")
                    logger.info(f"相对日期解析: {date_str} -> {fixed['deadline']}")
                # 2. 已经是标准格式
                elif re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
                    pass
                # 3. 尝试从其他常见格式转换
                else:
                    parsed_date = None
                    date_formats = [
                        "%Y/%m/%d", "%Y年%m月%d日",
                        "%m-%d", "%m/%d",
                        "%Y.%m.%d",
                    ]
                    for fmt in date_formats:
                        try:
                            parsed_date = datetime.strptime(date_str, fmt)
                            if fmt in ["%m-%d", "%m/%d"]:
                                # 缺少年份，使用当前年
                                parsed_date = parsed_date.replace(year=datetime.now().year)
                            break
                        except ValueError:
                            continue
                    
                    if parsed_date:
                        fixed["deadline"] = parsed_date.strftime("%Y-%m-%d")
                        logger.info(f"日期格式修正: {date_str} -> {fixed['deadline']}")
                    else:
                        # 尝试提取日期中的数字
                        date_match = re.search(r'(\d{4})\D(\d{1,2})\D(\d{1,2})', date_str)
                        if date_match:
                            y, m, d = date_match.groups()
                            try:
                                parsed_date = datetime(int(y), int(m), int(d))
                                fixed["deadline"] = parsed_date.strftime("%Y-%m-%d")
                                logger.info(f"日期格式修正(正则): {date_str} -> {fixed['deadline']}")
                            except ValueError:
                                logger.warning(f"无法解析日期: {date_str}，设为null")
                                fixed["deadline"] = None
                        else:
                            logger.warning(f"无法解析日期: {date_str}，设为null")
                            fixed["deadline"] = None
            
            # 确保 task_name 不为空
            if "task_name" not in fixed or not fixed["task_name"]:
                logger.error("缺少必需参数 task_name")
        
        elif tool_name == "query_tasks":
            # query_tasks 的参数修正
            if "priority" in fixed and fixed["priority"] is not None:
                priority_map = {
                    "high": "高", "urgent": "高", "重要": "高", "紧急": "高",
                    "medium": "中", "normal": "中", "普通": "中", "一般": "中",
                    "low": "低", "minor": "低", "不重要": "低", "次要": "低",
                }
                p = str(fixed["priority"]).lower().strip()
                if p in priority_map:
                    fixed["priority"] = priority_map[p]
        
        return fixed
    
    def execute_plan(self, plan: List[PlanStep]) -> List[Dict[str, Any]]:
        """执行计划
        
        Args:
            plan: 执行计划
        
        Returns:
            工具调用结果列表
        """
        results = []
        
        for step in plan:
            if step.tool:
                logger.info(f"执行步骤 {step.step}: {step.description}, tool={step.tool}")
                # 修正参数
                fixed_params = self._fix_parameters(step.tool, step.parameters or {})
                result = tool_registry.execute_tool(
                    step.tool,
                    fixed_params,
                    max_retries=3
                )
                results.append({
                    "step": step.step,
                    "tool_name": step.tool,
                    "parameters": fixed_params,
                    "result": result.to_dict(),
                    "success": result.success
                })
            else:
                logger.info(f"执行步骤 {step.step}: {step.description}, 无工具")
                results.append({
                    "step": step.step,
                    "tool_name": None,
                    "parameters": {},
                    "result": {"message": step.description},
                    "success": True
                })
        
        return results
    
    def generate_response(
        self,
        state: Dict[str, Any],
        plan: List[PlanStep],
        tool_results: List[Dict[str, Any]]
    ) -> str:
        """生成最终响应
        
        Args:
            state: Agent 状态
            plan: 执行计划
            tool_results: 工具执行结果
        
        Returns:
            生成的响应内容
        """
        try:
            messages = []
            
            # 构建上下文信息
            context_parts = []
            
            if plan:
                context_parts.append("执行计划:")
                for step in plan:
                    context_parts.append(f"- {step.description}")
            
            if tool_results:
                context_parts.append("\n执行结果:")
                for result in tool_results:
                    tool_name = result.get("tool_name", "N/A")
                    success = result.get("success", False)
                    res_data = result.get("result", {})
                    
                    if success and isinstance(res_data, dict):
                        message = res_data.get("message", "")
                        if message:
                            context_parts.append(f"- {tool_name}: {message}")
                        else:
                            context_parts.append(f"- {tool_name}: 执行成功")
                    else:
                        error = res_data.get("error", "未知错误") if isinstance(res_data, dict) else str(res_data)
                        context_parts.append(f"- {tool_name}: 执行失败 - {error}")
            
            context_str = "\n".join(context_parts) if context_parts else "无"
            
            # 构建系统提示词
            system_msg = SystemPrompts.RESPONSE_PROMPT.format(context=context_str)
            
            messages.append({"role": "system", "content": system_msg})
            
            # 添加历史消息
            history = state.get('messages', [])[-6:]  # 最近3轮对话
            for msg in history:
                role = "user" if isinstance(msg, HumanMessage) else "assistant"
                content = msg.content if hasattr(msg, 'content') else str(msg)
                messages.append({"role": role, "content": content})
            
            # 添加用户最新消息
            if history:
                last_msg = history[-1].content if hasattr(history[-1], 'content') else str(history[-1])
            else:
                last_msg = "你好"
            messages.append({"role": "user", "content": last_msg})
            
            # 调用 LLM 生成响应
            response_content = llm_client.chat(messages)
            
            logger.info(f"生成响应成功: {response_content[:50]}...")
            return response_content
            
        except Exception as e:
            logger.error(f"生成响应失败: {e}")
            return f"抱歉，我现在无法生成回复。问题: {str(e)[:100]}"
    
    def learn_from_interaction(
        self,
        plan: List[PlanStep],
        tool_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """从交互中学习
        
        Args:
            plan: 执行计划
            tool_results: 工具执行结果
        
        Returns:
            学习数据
        """
        successful_calls = sum(1 for r in tool_results if r.get('success', False))
        total_calls = len([r for r in tool_results if r.get('tool_name')])
        
        learning_data = {
            "timestamp": time.time(),
            "plan_steps": len(plan),
            "tool_calls": total_calls,
            "successful_calls": successful_calls,
            "success_rate": successful_calls / total_calls if total_calls > 0 else 0,
            "execution_summary": f"执行了 {total_calls} 个工具调用，成功 {successful_calls} 个"
        }
        
        logger.info(f"学习数据: {learning_data['execution_summary']}")
        return learning_data


# 创建全局决策系统实例
decision_system = AgentDecisionSystem()
