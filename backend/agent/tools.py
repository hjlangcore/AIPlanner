"""
Agent 工具定义

定义AI Agent可以调用的各种工具，包括任务管理、知识库查询、外部API调用等。
"""
import json
import time
import requests
import ast
import operator
from typing import Dict, Any, Optional, List
from ..db.db_handler import db
from ..service.rag_service import rag_service


class ToolRegistry:
    """工具注册表"""
    def __init__(self):
        self.tools = {}
    
    def register(self, name: str, description: str, func):
        """注册工具"""
        self.tools[name] = {
            "description": description,
            "function": func
        }
    
    def get_tool(self, name: str):
        """获取工具"""
        return self.tools.get(name)
    
    def get_all_tools(self):
        """获取所有工具"""
        return self.tools


# 创建工具注册表
tool_registry = ToolRegistry()


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
    try:
        # 合并任务名称和描述
        full_task_name = task_name
        if description:
            full_task_name = f"{task_name} - {description}"
        
        sub_tasks_list = sub_tasks or []
        
        task_id = db.save_task(
            raw_task=full_task_name,
            sub_tasks=sub_tasks_list,
            priority=priority,
            deadline=deadline,
            schedule="",
            category=category or "默认",
            tags=[]
        )
        return {
            "success": True,
            "task_id": task_id,
            "message": f"任务 '{task_name}' 创建成功" + (f"，包含 {len(sub_tasks_list)} 个子任务" if sub_tasks_list else ""),
            "task_name": task_name,
            "deadline": deadline,
            "priority": priority,
            "sub_tasks_count": len(sub_tasks_list)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"任务创建失败: {str(e)}"
        }


def query_tasks_tool(status: Optional[str] = None, category: Optional[str] = None, priority: Optional[str] = None) -> Dict[str, Any]:
    """查询任务工具
    
    Args:
        status: 任务状态
        category: 任务分类
        priority: 任务优先级
    
    Returns:
        任务列表
    """
    try:
        tasks = db.get_all_tasks(status=status, category=category, priority=priority)
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
        return {
            "success": True,
            "tasks": task_list,
            "count": len(task_list)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"查询任务失败: {str(e)}"
        }


def search_knowledge_tool(query: str, limit: int = 5) -> Dict[str, Any]:
    """搜索知识库工具
    
    Args:
        query: 搜索关键词
        limit: 返回结果数量
    
    Returns:
        知识库搜索结果
    """
    try:
        results = rag_service.search_knowledge(query, limit=limit, use_semantic=True)
        return {
            "success": True,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
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
        # 这里使用一个模拟的天气API
        # 实际应用中可以替换为真实的天气API
        # 注意：如果此函数在async上下文中被调用，应使用 asyncio.sleep()
        # 由于此函数是同步的，这里使用短延迟模拟处理时间
        time.sleep(0.1)
        return {
            "success": True,
            "weather": {
                "city": city,
                "temperature": "25°C",
                "description": "晴天",
                "humidity": "60%",
                "wind": "微风"
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"获取天气失败: {str(e)}"
        }


def calculate_tool(expression: str) -> Dict[str, Any]:
    """计算工具

    Args:
        expression: 数学表达式

    Returns:
        计算结果
    """
    try:
        # 安全数学运算：只允许基本的算术运算符
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
            """安全地评估AST节点，防止代码注入"""
            # 处理常量（Python 3.8+）
            if isinstance(node, ast.Constant):
                if isinstance(node.value, (int, float)):
                    return node.value
            # 处理数字（Python 3.7兼容）
            elif isinstance(node, ast.Num):
                return node.n
            # 处理二元运算 (如 1+2, 3*4)
            elif isinstance(node, ast.BinOp):
                left = safe_eval(node.left)
                right = safe_eval(node.right)
                op_type = type(node.op)
                if op_type in allowed_operators:
                    return allowed_operators[op_type](left, right)
                raise ValueError(f"不支持的运算符: {type(node.op).__name__}")
            # 处理一元运算 (如 -5, +3)
            elif isinstance(node, ast.UnaryOp):
                operand = safe_eval(node.operand)
                op_type = type(node.op)
                if op_type in allowed_operators:
                    return allowed_operators[op_type](operand)
                raise ValueError(f"不支持的一元运算符: {type(node.op).__name__}")

            raise ValueError(f"不支持的表达式节点: {ast.dump(node)}")

        # 解析并计算表达式
        tree = ast.parse(expression.strip(), mode='eval')
        result = safe_eval(tree.body)

        return {
            "success": True,
            "expression": expression,
            "result": result
        }
    except ValueError as e:
        # ValueError表示表达式语法问题或不支持的操作
        return {
            "success": False,
            "error": str(e),
            "message": f"计算失败: {str(e)}"
        }
    except Exception as e:
        # 其他异常（解析错误等）
        return {
            "success": False,
            "error": str(e),
            "message": f"计算失败: {str(e)}"
        }


# 注册工具
tool_registry.register(
    "create_task",
    "创建新任务，需要提供任务名称，可选提供截止日期、优先级、分类和子任务",
    create_task_tool
)

tool_registry.register(
    "query_tasks",
    "查询任务列表，可按状态、分类、优先级筛选",
    query_tasks_tool
)

tool_registry.register(
    "search_knowledge",
    "搜索知识库，根据关键词查找相关信息",
    search_knowledge_tool
)

tool_registry.register(
    "get_weather",
    "获取指定城市的天气信息",
    get_weather_tool
)

tool_registry.register(
    "calculate",
    "计算数学表达式",
    calculate_tool
)