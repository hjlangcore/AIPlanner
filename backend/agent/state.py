"""
状态定义模块

定义Agent的全局状态结构，用于在工作流节点之间传递数据。
"""
from typing import TypedDict, List


class TodoState(TypedDict):
    """Agent状态字典
    
    用于存储任务处理过程中的所有数据，
    在LangGraph工作流的各个节点之间共享。
    """
    raw_input: str  # 用户原始输入的自然语言任务
    task_info: dict  # 解析后的任务信息，包含任务名称和截止日期
    sub_tasks: List[str]  # 拆解后的子任务列表
    priority: str  # 任务优先级（高/中/低）
    schedule_plan: str  # 生成的日程安排
    save_status: bool  # 数据库保存状态
