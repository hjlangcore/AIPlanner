"""
Agent 工具系统

提供模块化的工具注册和执行机制，支持：
- 工具注册与发现
- 参数验证与类型检查
- 错误处理与重试机制
- 工具执行结果统一封装

工具包括：
- create_task: 创建任务
- query_tasks: 查询任务
- update_task_status: 更新任务状态
- search_knowledge: 搜索知识库
- get_weather: 获取天气
- calculate: 数学计算
- batch_create_tasks: 批量创建任务
- extract_tasks_from_text: 从文本提取任务
- 任务模板相关工具

所有工具都通过 ToolRegistry 统一管理，支持热插拔。
"""
import json
import time
import ast
import operator
import logging
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod

# 配置日志
logger = logging.getLogger(__name__)


@dataclass
class ToolMetadata:
    """工具元数据"""
    name: str
    description: str
    parameters: Dict[str, Dict[str, Any]]  # 参数名 -> 参数定义
    examples: Optional[List[Dict[str, Any]]] = None


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    message: str = ""
    execution_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "message": self.message,
            "execution_time": self.execution_time
        }


class BaseTool(ABC):
    """工具基类"""
    
    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        """返回工具元数据"""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """执行工具"""
        pass
    
    def validate_parameters(self, params: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """验证参数"""
        required = [k for k, v in self.metadata.parameters.items() if v.get("required", False)]
        for req in required:
            if req not in params:
                return False, f"缺少必需参数: {req}"
        return True, None


class ToolRegistry:
    """工具注册表
    
    提供工具的注册、发现、执行和管理功能。
    """
    
    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._tool_instances: Dict[str, BaseTool] = {}
    
    def register_function(
        self,
        name: str,
        description: str,
        func: Callable,
        parameters: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> None:
        """注册函数式工具
        
        Args:
            name: 工具名称
            description: 工具描述
            func: 工具函数
            parameters: 参数定义
        """
        self._tools[name] = {
            "type": "function",
            "description": description,
            "function": func,
            "parameters": parameters or {}
        }
        logger.info(f"注册工具: {name}")
    
    def register_tool(self, tool: BaseTool) -> None:
        """注册对象式工具
        
        Args:
            tool: 工具实例
        """
        self._tool_instances[tool.metadata.name] = tool
        logger.info(f"注册工具(对象): {tool.metadata.name}")
    
    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """获取工具定义"""
        if name in self._tools:
            return self._tools[name]
        if name in self._tool_instances:
            tool = self._tool_instances[name]
            return {
                "type": "tool",
                "description": tool.metadata.description,
                "function": tool.execute,
                "parameters": tool.metadata.parameters
            }
        return None
    
    def get_all_tools(self) -> Dict[str, Dict[str, Any]]:
        """获取所有工具"""
        result = {}
        for name, tool in self._tools.items():
            result[name] = {
                "description": tool["description"],
                "function": tool["function"]
            }
        for name, tool in self._tool_instances.items():
            result[name] = {
                "description": tool.metadata.description,
                "function": tool.execute
            }
        return result
    
    def get_tools_info(self) -> str:
        """生成工具信息描述"""
        tools_info = []
        for name, tool in self.get_all_tools().items():
            tools_info.append(f"- {name}: {tool['description']}")
        return "\n".join(tools_info)
    
    def execute_tool(
        self,
        name: str,
        parameters: Dict[str, Any],
        max_retries: int = 3
    ) -> ToolResult:
        """执行工具
        
        Args:
            name: 工具名称
            parameters: 工具参数
            max_retries: 最大重试次数
        
        Returns:
            ToolResult: 执行结果
        """
        tool_def = self.get_tool(name)
        if not tool_def:
            return ToolResult(
                success=False,
                error=f"工具 '{name}' 不存在",
                message=f"工具 '{name}' 未注册"
            )
        
        start_time = time.time()
        last_error = None
        
        for attempt in range(max_retries):
            try:
                result = tool_def["function"](**parameters)
                execution_time = time.time() - start_time
                
                # 处理不同格式的返回值
                if isinstance(result, ToolResult):
                    result.execution_time = execution_time
                    return result
                elif isinstance(result, dict):
                    return ToolResult(
                        success=result.get("success", True),
                        data=result,
                        message=result.get("message", ""),
                        execution_time=execution_time
                    )
                else:
                    return ToolResult(
                        success=True,
                        data=result,
                        execution_time=execution_time
                    )
                    
            except TypeError as e:
                # 参数错误，不重试
                logger.warning(f"工具 {name} 参数错误: {e}")
                return ToolResult(
                    success=False,
                    error=f"参数错误: {str(e)}",
                    message=f"工具参数不匹配: {str(e)}",
                    execution_time=time.time() - start_time
                )
            except Exception as e:
                last_error = str(e)
                logger.warning(f"工具 {name} 执行失败(尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(0.5)  # 重试前等待
        
        return ToolResult(
            success=False,
            error=last_error,
            message=f"工具执行失败，已重试 {max_retries} 次",
            execution_time=time.time() - start_time
        )


# 创建全局工具注册表
tool_registry = ToolRegistry()


# ==================== 工具实现 ====================

def _auto_generate_subtasks(task_name: str, deadline: Optional[str], priority: str) -> tuple[List[str], str, str]:
    """使用LLM自动生成子任务、优化任务名称和日程安排
    
    Returns:
        (sub_tasks, optimized_name, schedule) 元组
    """
    try:
        from .llm_config import agent_llm_config
        import json
        import re
        
        prompt = f"""你是智能任务助手，分析以下任务并生成执行计划：

任务信息：
- 名称：{task_name}
- 截止日期：{deadline or '未指定'}
- 优先级：{priority}

要求：
1. 优化任务名称（去掉"帮我创建"等辅助词，保留核心动作，简洁明了）
2. 将任务拆解为3-7个可执行的子任务
3. 生成简洁的日程安排建议

仅返回JSON格式，不要其他文字：
{{
    "optimized_name": "优化后的任务名称",
    "sub_tasks": ["子任务1", "子任务2", "子任务3"],
    "schedule": "日程安排建议"
}}"""

        response = agent_llm_config.client.chat.completions.create(
            model=agent_llm_config.model,
            messages=[
                {"role": "system", "content": "你是一个专业的任务规划助手。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            timeout=30
        )
        
        content = response.choices[0].message.content
        if not content:
            return [], task_name, ""
        
        # 尝试解析JSON
        content = content.strip()
        if content.startswith("```"):
            parts = content.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{"):
                    content = part
                    break
        
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                return [], task_name, ""
        
        optimized_name = data.get("optimized_name", task_name)
        sub_tasks = data.get("sub_tasks", [])
        schedule = data.get("schedule", "")
        
        # 确保子任务是字符串列表
        if sub_tasks and isinstance(sub_tasks, list):
            sub_tasks = [str(st) for st in sub_tasks if st]
        else:
            sub_tasks = []
        
        logger.info(f"LLM自动生成子任务: {optimized_name}, 子任务数={len(sub_tasks)}")
        return sub_tasks, optimized_name, schedule
        
    except Exception as e:
        logger.warning(f"自动生成子任务失败: {e}")
        return [], task_name, ""


def create_task_tool(
    task_name: str,
    deadline: Optional[str] = None,
    priority: str = "中",
    category: Optional[str] = None,
    description: Optional[str] = None,
    sub_tasks: Optional[List[str]] = None
) -> Dict[str, Any]:
    """创建任务工具
    
    Args:
        task_name: 任务名称
        deadline: 截止日期 (YYYY-MM-DD)
        priority: 优先级 (高/中/低)
        category: 任务分类
        description: 任务描述（可选，会合并到task_name中）
        sub_tasks: 子任务列表（可选）
    
    Returns:
        任务创建结果
    """
    from ..db.db_handler import db
    
    try:
        # 合并任务名称和描述
        full_task_name = task_name
        if description:
            full_task_name = f"{task_name} - {description}"
        
        # 处理子任务
        sub_tasks_list = sub_tasks or []
        schedule = ""
        
        # 如果没有提供子任务，自动调用LLM生成
        if not sub_tasks_list:
            generated_subtasks, optimized_name, generated_schedule = _auto_generate_subtasks(
                full_task_name, deadline, priority
            )
            if generated_subtasks:
                sub_tasks_list = generated_subtasks
                # 如果LLM优化了名称且不是默认的"未命名任务"，使用优化后的名称
                if optimized_name and optimized_name != task_name and "未命名" not in optimized_name:
                    full_task_name = optimized_name
                    task_name = optimized_name
                schedule = generated_schedule
                logger.info(f"自动生成的子任务: {sub_tasks_list}")
        
        task_id = db.save_task(
            raw_task=full_task_name,
            sub_tasks=sub_tasks_list,
            priority=priority,
            deadline=deadline,
            schedule=schedule,
            category=category or "默认",
            tags=[]
        )
        logger.info(f"创建任务成功: {full_task_name} (ID: {task_id}, 子任务: {len(sub_tasks_list)}个)")
        return {
            "success": True,
            "task_id": task_id,
            "message": f"任务 '{task_name}' 创建成功" + (f"，包含 {len(sub_tasks_list)} 个子任务" if sub_tasks_list else ""),
            "task_name": task_name,
            "deadline": deadline,
            "priority": priority,
            "sub_tasks_count": len(sub_tasks_list),
            "sub_tasks": sub_tasks_list,
            "schedule": schedule
        }
    except Exception as e:
        logger.error(f"创建任务失败: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"任务创建失败: {str(e)}"
        }


def query_tasks_tool(
    status: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """查询任务工具
    
    Args:
        status: 任务状态筛选
        category: 任务分类筛选
        priority: 任务优先级筛选
        limit: 返回结果数量限制
    
    Returns:
        任务列表
    """
    from ..db.db_handler import db
    
    try:
        tasks = db.get_all_tasks(
            status=status,
            category=category,
            priority=priority
        )
        
        # 限制结果数量
        tasks = tasks[:limit]
        
        task_list = []
        for task in tasks:
            try:
                sub_tasks = json.loads(task[2]) if task[2] else []
            except:
                sub_tasks = []
            
            task_list.append({
                "id": task[0],
                "raw_task": task[1],
                "sub_tasks": sub_tasks,
                "priority": task[3],
                "deadline": task[4],
                "status": task[6],
                "category": task[7] if len(task) > 7 else "默认"
            })
        
        logger.info(f"查询任务成功: 找到 {len(task_list)} 个任务")
        return {
            "success": True,
            "tasks": task_list,
            "count": len(task_list)
        }
    except Exception as e:
        logger.error(f"查询任务失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"查询任务失败: {str(e)}"
        }


def update_task_status_tool(
    task_id: int,
    status: str
) -> Dict[str, Any]:
    """更新任务状态工具
    
    Args:
        task_id: 任务ID
        status: 新状态 (pending/in_progress/completed/cancelled)
    
    Returns:
        更新结果
    """
    from ..db.db_handler import db
    
    try:
        db.update_task_status(task_id, status)
        logger.info(f"更新任务状态成功: ID={task_id}, status={status}")
        return {
            "success": True,
            "message": f"任务状态已更新为: {status}"
        }
    except Exception as e:
        logger.error(f"更新任务状态失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"更新任务状态失败: {str(e)}"
        }


def search_knowledge_tool(
    query: str,
    limit: int = 5
) -> Dict[str, Any]:
    """搜索知识库工具
    
    Args:
        query: 搜索关键词
        limit: 返回结果数量
    
    Returns:
        知识库搜索结果
    """
    from ..service.rag_service import rag_service
    
    try:
        results = rag_service.search_knowledge(query, limit=limit, use_semantic=True)
        logger.info(f"知识库搜索成功: query='{query}', 找到 {len(results)} 条结果")
        return {
            "success": True,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        logger.error(f"知识库搜索失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"搜索知识库失败: {str(e)}"
        }


def get_weather_tool(city: str) -> Dict[str, Any]:
    """获取天气工具
    
    Args:
        city: 城市名称
    
    Returns:
        天气信息
    """
    try:
        # 模拟天气数据
        # 实际应用中可替换为真实天气API
        time.sleep(0.1)
        logger.info(f"获取天气信息: {city}")
        return {
            "success": True,
            "weather": {
                "city": city,
                "temperature": "25°C",
                "description": "晴朗",
                "humidity": "60%",
                "wind": "微风"
            },
            "message": f"获取 {city} 天气成功"
        }
    except Exception as e:
        logger.error(f"获取天气失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"获取天气失败: {str(e)}"
        }


def batch_create_tasks_tool(
    tasks: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """批量创建任务工具
    
    从任务列表中批量创建多个任务，每个任务可以包含名称、截止日期、优先级等信息。
    
    Args:
        tasks: 任务列表，每个任务是包含任务信息的字典，例如：
            [
                {"task_name": "任务1", "priority": "高", "deadline": "2024-12-31"},
                {"task_name": "任务2", "priority": "中"}
            ]
    
    Returns:
        批量创建结果
    """
    from ..db.db_handler import db
    
    try:
        created_tasks = []
        failed_tasks = []
        
        for i, task_data in enumerate(tasks):
            try:
                task_name = task_data.get("task_name") or task_data.get("name", "")
                if not task_name:
                    failed_tasks.append({
                        "index": i,
                        "error": "缺少任务名称",
                        "data": task_data
                    })
                    continue
                
                # 合并任务名称和描述
                description = task_data.get("description", "")
                full_task_name = f"{task_name} - {description}" if description else task_name
                
                task_id = db.save_task(
                    raw_task=full_task_name,
                    sub_tasks=task_data.get("sub_tasks", []),
                    priority=task_data.get("priority", "中"),
                    deadline=task_data.get("deadline"),
                    schedule="",
                    category=task_data.get("category", "默认"),
                    tags=task_data.get("tags", [])
                )
                
                created_tasks.append({
                    "index": i,
                    "task_id": task_id,
                    "task_name": task_name,
                    "deadline": task_data.get("deadline"),
                    "priority": task_data.get("priority", "中")
                })
                
            except Exception as e:
                failed_tasks.append({
                    "index": i,
                    "error": str(e),
                    "data": task_data
                })
        
        success_count = len(created_tasks)
        failed_count = len(failed_tasks)
        
        logger.info(f"批量创建任务完成: 成功 {success_count} 个，失败 {failed_count} 个")
        
        return {
            "success": True,
            "message": f"批量创建任务完成：成功 {success_count} 个，失败 {failed_count} 个",
            "created_tasks": created_tasks,
            "failed_tasks": failed_tasks,
            "success_count": success_count,
            "failed_count": failed_count
        }
        
    except Exception as e:
        logger.error(f"批量创建任务失败: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"批量创建任务失败: {str(e)}"
        }


def extract_tasks_from_text_tool(
    text: str,
    default_priority: str = "中",
    default_category: Optional[str] = None
) -> Dict[str, Any]:
    """从文本中提取任务工具
    
    使用AI从一段自然语言文本中智能提取多个任务信息。
    
    Args:
        text: 包含任务信息的自然语言文本
        default_priority: 默认优先级（高/中/低）
        default_category: 默认分类
    
    Returns:
        提取的任务列表
    """
    try:
        from .llm_config import agent_llm_config
        
        # 构建提示词
        prompt = f"""从以下文本中提取所有任务信息，返回JSON格式。

规则：
1. 识别所有待办事项、行动项、任务
2. 为每个任务提取：名称、截止日期（如果有）、优先级（如果有明确提示）
3. 如果没有明确日期，deadline设为null
4. 如果没有明确优先级，使用"{default_priority}"
5. 只返回JSON数组，不要其他文字

文本：
{text}

输出格式（只返回这个JSON数组）：
[
    {{
        "task_name": "任务名称",
        "deadline": "YYYY-MM-DD 或 null",
        "priority": "高/中/低",
        "category": "分类（如果提到）"
    }}
]
"""
        
        # 调用LLM
        client = agent_llm_config.client
        model = agent_llm_config.model
        
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("LLM返回内容为空")
        
        # 解析JSON
        import json
        import re
        
        # 尝试直接解析
        try:
            tasks = json.loads(content)
        except json.JSONDecodeError:
            # 尝试从文本中提取JSON数组
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                tasks = json.loads(json_match.group())
            else:
                raise ValueError("无法解析LLM返回的JSON")
        
        if not isinstance(tasks, list):
            tasks = [tasks]
        
        logger.info(f"从文本中提取到 {len(tasks)} 个任务")
        
        return {
            "success": True,
            "tasks": tasks,
            "count": len(tasks),
            "message": f"从文本中提取到 {len(tasks)} 个任务"
        }
        
    except Exception as e:
        logger.error(f"从文本中提取任务失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"提取任务失败: {str(e)}",
            "tasks": []
        }


def create_task_template_tool(
    user_id: int,
    name: str,
    description: Optional[str] = None,
    priority: str = "中",
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    sub_tasks: Optional[List[str]] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """创建任务模板工具
    
    创建一个任务模板，可以用于快速创建类似的任务。
    
    Args:
        user_id: 用户ID
        name: 模板名称
        description: 模板描述
        priority: 默认优先级（高/中/低）
        category: 默认分类
        tags: 默认标签列表
        sub_tasks: 默认子任务列表
        notes: 默认备注
    
    Returns:
        创建结果
    """
    from ..db.db_handler import db
    
    try:
        template_id = db.create_task_template(
            user_id=user_id,
            name=name,
            description=description,
            priority=priority,
            category=category or "默认",
            tags=tags,
            sub_tasks=[{"text": st, "completed": False} for st in (sub_tasks or [])],
            notes=notes or ""
        )
        
        logger.info(f"创建任务模板成功: {name} (ID: {template_id})")
        
        return {
            "success": True,
            "template_id": template_id,
            "message": f"任务模板 '{name}' 创建成功",
            "name": name,
            "priority": priority,
            "category": category or "默认"
        }
        
    except Exception as e:
        logger.error(f"创建任务模板失败: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"创建任务模板失败: {str(e)}"
        }


def list_task_templates_tool(
    user_id: int
) -> Dict[str, Any]:
    """列出任务模板工具
    
    获取用户创建的所有任务模板。
    
    Args:
        user_id: 用户ID
    
    Returns:
        任务模板列表
    """
    from ..db.db_handler import db
    import json
    
    try:
        templates = db.get_user_task_templates(user_id)
        
        template_list = []
        for t in templates:
            try:
                tags = json.loads(t[5]) if t[5] else []
                sub_tasks = json.loads(t[6]) if t[6] else []
            except:
                tags = []
                sub_tasks = []
            
            template_list.append({
                "id": t[0],
                "name": t[1],
                "description": t[2],
                "priority": t[3],
                "category": t[4],
                "tags": tags,
                "sub_tasks": sub_tasks,
                "notes": t[7] if len(t) > 7 else "",
                "created_at": t[8] if len(t) > 8 else ""
            })
        
        logger.info(f"获取任务模板列表成功: 找到 {len(template_list)} 个模板")
        
        return {
            "success": True,
            "templates": template_list,
            "count": len(template_list),
            "message": f"找到 {len(template_list)} 个任务模板"
        }
        
    except Exception as e:
        logger.error(f"获取任务模板列表失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"获取任务模板列表失败: {str(e)}",
            "templates": []
        }


def use_task_template_tool(
    template_id: int,
    task_name: str,
    deadline: Optional[str] = None,
    user_id: Optional[int] = None
) -> Dict[str, Any]:
    """使用任务模板创建任务工具
    
    根据指定的任务模板快速创建一个新任务。
    
    Args:
        template_id: 模板ID
        task_name: 新任务的名称（会覆盖模板中的名称）
        deadline: 新任务的截止日期
        user_id: 用户ID（可选，用于记录）
    
    Returns:
        任务创建结果
    """
    from ..db.db_handler import db
    import json
    
    try:
        # 获取模板
        template = db.get_task_template(template_id)
        if not template:
            return {
                "success": False,
                "error": f"模板不存在: {template_id}",
                "message": f"任务模板 {template_id} 不存在"
            }
        
        # 解析模板数据
        try:
            tags = json.loads(template[6]) if template[6] else []
            sub_tasks = json.loads(template[7]) if template[7] else []
        except:
            tags = []
            sub_tasks = []
        
        # 创建任务
        task_id = db.save_task(
            raw_task=task_name,
            sub_tasks=[st.get("text", "") for st in sub_tasks] if isinstance(sub_tasks, list) and sub_tasks and isinstance(sub_tasks[0], dict) else sub_tasks,
            priority=template[4] if len(template) > 4 else "中",
            deadline=deadline,
            schedule="",
            category=template[5] if len(template) > 5 else "默认",
            tags=tags if isinstance(tags, list) else []
        )
        
        logger.info(f"使用模板创建任务成功: 模板={template[2] if len(template) > 2 else template_id}, 任务={task_name} (ID: {task_id})")
        
        return {
            "success": True,
            "task_id": task_id,
            "message": f"使用模板 '{template[2] if len(template) > 2 else template_id}' 创建任务 '{task_name}' 成功",
            "task_name": task_name,
            "deadline": deadline,
            "priority": template[4] if len(template) > 4 else "中",
            "category": template[5] if len(template) > 5 else "默认"
        }
        
    except Exception as e:
        logger.error(f"使用任务模板失败: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"使用任务模板失败: {str(e)}"
        }


def delete_task_template_tool(
    template_id: int
) -> Dict[str, Any]:
    """删除任务模板工具
    
    删除指定的任务模板。
    
    Args:
        template_id: 模板ID
    
    Returns:
        删除结果
    """
    from ..db.db_handler import db
    
    try:
        # 先获取模板信息（用于日志）
        template = db.get_task_template(template_id)
        template_name = template[2] if template and len(template) > 2 else str(template_id)
        
        # 删除模板
        success = db.delete_task_template(template_id)
        
        if success:
            logger.info(f"删除任务模板成功: {template_name} (ID: {template_id})")
            return {
                "success": True,
                "message": f"任务模板 '{template_name}' 删除成功"
            }
        else:
            return {
                "success": False,
                "error": f"模板不存在或删除失败: {template_id}",
                "message": f"任务模板 {template_id} 不存在或删除失败"
            }
        
    except Exception as e:
        logger.error(f"删除任务模板失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"删除任务模板失败: {str(e)}"
        }


def calculate_tool(expression: str) -> Dict[str, Any]:
    """数学计算工具
    
    使用 AST 安全解析和计算数学表达式。
    
    Args:
        expression: 数学表达式
    
    Returns:
        计算结果
    """
    allowed_operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.Mod: operator.mod,
        ast.FloorDiv: operator.floordiv,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }
    
    def safe_eval(node):
        """安全地评估 AST 节点"""
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
        elif isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.BinOp):
            left = safe_eval(node.left)
            right = safe_eval(node.right)
            op_type = type(node.op)
            if op_type in allowed_operators:
                return allowed_operators[op_type](left, right)
            raise ValueError(f"不支持的运算符: {type(node.op).__name__}")
        elif isinstance(node, ast.UnaryOp):
            operand = safe_eval(node.operand)
            op_type = type(node.op)
            if op_type in allowed_operators:
                return allowed_operators[op_type](operand)
            raise ValueError(f"不支持的一元运算符: {type(node.op).__name__}")
        raise ValueError(f"不支持的表达式节点: {ast.dump(node)}")
    
    try:
        tree = ast.parse(expression.strip(), mode='eval')
        result = safe_eval(tree.body)
        logger.info(f"计算成功: {expression} = {result}")
        return {
            "success": True,
            "expression": expression,
            "result": result
        }
    except ValueError as e:
        logger.warning(f"计算失败(值错误): {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"计算表达式无效: {str(e)}"
        }
    except Exception as e:
        logger.error(f"计算失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"计算失败: {str(e)}"
        }


# ==================== 注册工具 ====================

def register_all_tools():
    """注册所有工具"""
    tool_registry.register_function(
        "create_task",
        "创建新任务，需要提供任务名称，可选提供截止日期、优先级、分类和子任务",
        create_task_tool,
        parameters={
            "task_name": {"type": "string", "required": True, "description": "任务名称，简洁明了的核心任务描述"},
            "deadline": {"type": "string", "required": False, "description": "截止日期，必须是 YYYY-MM-DD 格式"},
            "priority": {"type": "string", "required": False, "description": "优先级，只能是 '高' / '中' / '低'"},
            "category": {"type": "string", "required": False, "description": "任务分类，如 '工作' / '学习' / '生活'"},
            "description": {"type": "string", "required": False, "description": "任务详细描述"},
            "sub_tasks": {"type": "array", "required": False, "description": "子任务列表，如 ['准备材料', '撰写报告']"}
        }
    )
    
    tool_registry.register_function(
        "query_tasks",
        "查询任务列表，支持按状态、分类、优先级筛选",
        query_tasks_tool,
        parameters={
            "status": {"type": "string", "required": False, "description": "任务状态"},
            "category": {"type": "string", "required": False, "description": "任务分类"},
            "priority": {"type": "string", "required": False, "description": "任务优先级"},
            "limit": {"type": "integer", "required": False, "description": "返回数量限制"}
        }
    )
    
    tool_registry.register_function(
        "update_task_status",
        "更新任务状态",
        update_task_status_tool,
        parameters={
            "task_id": {"type": "integer", "required": True, "description": "任务ID"},
            "status": {"type": "string", "required": True, "description": "新状态"}
        }
    )
    
    tool_registry.register_function(
        "search_knowledge",
        "搜索知识库，根据关键词查找相关信息",
        search_knowledge_tool,
        parameters={
            "query": {"type": "string", "required": True, "description": "搜索关键词"},
            "limit": {"type": "integer", "required": False, "description": "返回结果数量"}
        }
    )
    
    tool_registry.register_function(
        "get_weather",
        "获取指定城市的天气信息",
        get_weather_tool,
        parameters={
            "city": {"type": "string", "required": True, "description": "城市名称"}
        }
    )
    
    tool_registry.register_function(
        "calculate",
        "计算数学表达式的值",
        calculate_tool,
        parameters={
            "expression": {"type": "string", "required": True, "description": "数学表达式"}
        }
    )
    
    tool_registry.register_function(
        "batch_create_tasks",
        "批量创建多个任务，需要提供任务列表，每个任务包含名称、截止日期、优先级等信息",
        batch_create_tasks_tool,
        parameters={
            "tasks": {"type": "array", "required": True, "description": "任务列表，每个任务是包含任务信息的字典，例如：[{\"task_name\": \"任务1\", \"priority\": \"高\"}]"}
        }
    )
    
    tool_registry.register_function(
        "extract_tasks_from_text",
        "从一段自然语言文本中智能提取多个任务信息，自动识别任务名称、截止日期、优先级等",
        extract_tasks_from_text_tool,
        parameters={
            "text": {"type": "string", "required": True, "description": "包含任务信息的自然语言文本"},
            "default_priority": {"type": "string", "required": False, "description": "默认优先级（高/中/低），默认为'中'"},
            "default_category": {"type": "string", "required": False, "description": "默认分类"}
        }
    )
    
    # 任务模板相关工具
    tool_registry.register_function(
        "create_task_template",
        "创建任务模板，用于快速创建类似的任务",
        create_task_template_tool,
        parameters={
            "user_id": {"type": "integer", "required": True, "description": "用户ID"},
            "name": {"type": "string", "required": True, "description": "模板名称"},
            "description": {"type": "string", "required": False, "description": "模板描述"},
            "priority": {"type": "string", "required": False, "description": "默认优先级（高/中/低）"},
            "category": {"type": "string", "required": False, "description": "默认分类"},
            "tags": {"type": "array", "required": False, "description": "默认标签列表"},
            "sub_tasks": {"type": "array", "required": False, "description": "默认子任务列表"},
            "notes": {"type": "string", "required": False, "description": "默认备注"}
        }
    )
    
    tool_registry.register_function(
        "list_task_templates",
        "列出用户的所有任务模板",
        list_task_templates_tool,
        parameters={
            "user_id": {"type": "integer", "required": True, "description": "用户ID"}
        }
    )
    
    tool_registry.register_function(
        "use_task_template",
        "使用指定的任务模板创建新任务",
        use_task_template_tool,
        parameters={
            "template_id": {"type": "integer", "required": True, "description": "模板ID"},
            "task_name": {"type": "string", "required": True, "description": "新任务的名称"},
            "deadline": {"type": "string", "required": False, "description": "新任务的截止日期（YYYY-MM-DD）"},
            "user_id": {"type": "integer", "required": False, "description": "用户ID（可选）"}
        }
    )
    
    tool_registry.register_function(
        "delete_task_template",
        "删除指定的任务模板",
        delete_task_template_tool,
        parameters={
            "template_id": {"type": "integer", "required": True, "description": "模板ID"}
        }
    )
    
    logger.info(f"已注册 {len(tool_registry.get_all_tools())} 个工具")


# 注册所有工具
register_all_tools()
