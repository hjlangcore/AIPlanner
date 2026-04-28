"""
工作流模块

定义 LangGraph 工作流，用于处理用户输入的自然语言任务。

工作流程：
1. process_task_node - 一次性调用 LLM 完成：
   - 任务名称提取
   - 截止日期识别
   - 子任务智能拆解
   - 优先级自动评估
   - 日程安排生成

2. save_to_db_node - 保存任务到数据库

支持流式输出 (process_task_stream)，通过 SSE 实时返回：
- AI 分析进度
- 子任务生成过程
- 保存状态

使用 LLM 一次性完成所有分析，减少 API 调用次数，提高响应速度。
"""
import json
import re
import sys
import os
from datetime import datetime, timedelta
from typing import Generator, AsyncGenerator
import asyncio

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from langgraph.graph import StateGraph, END
from backend.agent.state import TodoState
from backend.agent.llm_config import client, model
from backend.db.db_handler import db


# 共享的系统提示词
TASK_ANALYSIS_SYSTEM_PROMPT = """你是智能任务助手，用户输入一个任务，你需要一次性完成以下分析：
1. 提取任务名称和截止日期（YYYY-MM-DD格式，无则返回null）
2. 将任务拆解为适量且可执行的子任务（根据任务复杂度自适应拆解，不限制数量）
3. 根据截止日期判断优先级（1天内=高，3天内=中，7天内=低）
4. 生成简洁的日程安排

仅返回以下JSON格式，无其他文字：
{
    "任务名称": "xxx",
    "截止日期": "YYYY-MM-DD"或null,
    "子任务": ["任务1", "任务2", "任务3"],
    "优先级": "高/中/低",
    "日程安排": "简要日程说明"
}"""


def call_llm(system_prompt: str, user_prompt: str) -> str:
    """调用大模型
    
    Args:
        system_prompt: 系统提示词，定义大模型的角色
        user_prompt: 用户提示词，包含具体任务内容
    
    Returns:
        str: 大模型的回复内容
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.1,
            timeout=60
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"大模型调用失败: {str(e)}")
        raise


def call_llm_stream(system_prompt: str, user_prompt: str) -> Generator[str, None, None]:
    """流式调用大模型，逐词返回响应
    
    Args:
        system_prompt: 系统提示词
        user_prompt: 用户提示词
    
    Yields:
        str: 增量响应内容
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.1,
            timeout=60,
            stream=True  # 启用流式输出
        )
        
        full_content = ""
        for chunk in completion:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_content += content
                yield content
                
    except Exception as e:
        print(f"大模型流式调用失败: {str(e)}")
        raise


def parse_json_from_stream(full_content: str) -> dict:
    """从流式响应中解析JSON"""
    # 清理markdown格式
    content = full_content.strip()
    if content.startswith("```"):
        parts = content.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            content = part
            break
    
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
    return None


def process_task_node(state: TodoState) -> dict:
    """一次性处理任务节点（合并4次LLM调用为1次）
    
    从用户输入中提取任务信息、拆解子任务、设置优先级、生成日程。
    
    Args:
        state: 当前Agent状态
    
    Returns:
        dict: 更新后的状态
    """
    print(f"[process_task_node] 开始处理任务: {state['raw_input']}")
    
    result = call_llm(TASK_ANALYSIS_SYSTEM_PROMPT, state['raw_input'])
    print(f"[process_task_node] LLM响应: {result[:200]}...")
    
    # 解析JSON
    result = result.strip()
    if result.startswith("```"):
        parts = result.split("```")
        for part in parts:
            if part.strip() and not part.startswith("json"):
                continue
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            result = part
            break
    
    try:
        task_data = json.loads(result)
    except json.JSONDecodeError:
        # 尝试正则提取JSON
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            try:
                task_data = json.loads(json_match.group())
            except:
                task_data = None
        else:
            task_data = None
    
    if not task_data:
        task_data = {
            "任务名称": state['raw_input'],
            "截止日期": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
            "子任务": ["完成任务"],
            "优先级": "中",
            "日程安排": "按计划执行"
        }
    
    print(f"[process_task_node] 处理完成: {task_data}")
    
    return {
        "task_info": {
            "任务名称": task_data.get("任务名称", state['raw_input']),
            "截止日期": task_data.get("截止日期", (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"))
        },
        "sub_tasks": task_data.get("子任务", ["完成任务"]),
        "priority": task_data.get("优先级", "中"),
        "schedule_plan": task_data.get("日程安排", "按计划执行")
    }


def process_task_stream(raw_input: str) -> Generator[dict, None, dict]:
    """流式处理任务，逐个返回子任务
    
    让用户实时看到AI分析过程和子任务生成进度。
    
    Args:
        raw_input: 用户原始输入
    
    Yields:
        dict: 实时处理状态
        - step: 当前步骤 (analyzing, subtask, completed)
        - message: 步骤消息
        - data: 相关数据
    """
    print(f"[process_task_stream] 开始流式处理: {raw_input}")
    
    # 步骤1: 开始分析
    yield {
        "step": "analyzing",
        "message": "🔍 AI正在分析任务...",
        "progress": 10,
        "data": None
    }
    
    # 流式调用LLM
    try:
        full_content = ""
        for chunk in call_llm_stream(TASK_ANALYSIS_SYSTEM_PROMPT, raw_input):
            full_content += chunk
            # 每收到一些内容就更新
            if len(full_content) > 20:
                yield {
                    "step": "analyzing",
                    "message": f"🤔 AI正在思考... (已接收{len(full_content)}字符)",
                    "progress": 30,
                    "data": {"partial": full_content[:100] + "..." if len(full_content) > 100 else full_content}
                }
    except Exception as e:
        yield {
            "step": "error",
            "message": f"❌ AI调用失败: {str(e)}",
            "progress": 0,
            "data": None
        }
        return
    
    # 步骤2: 解析结果
    yield {
        "step": "parsing",
        "message": "📝 正在解析AI响应...",
        "progress": 60,
        "data": None
    }
    
    task_data = parse_json_from_stream(full_content)
    
    if not task_data:
        task_data = {
            "任务名称": raw_input,
            "截止日期": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
            "子任务": ["完成任务"],
            "优先级": "中",
            "日程安排": "按计划执行"
        }
    
    # 步骤3: 逐个展示子任务
    sub_tasks = task_data.get("子任务", ["完成任务"])
    task_name = task_data.get("任务名称", raw_input)
    deadline = task_data.get("截止日期")
    priority = task_data.get("优先级", "中")
    schedule = task_data.get("日程安排", "按计划执行")
    
    # 提取子任务数量
    total_tasks = len(sub_tasks)
    
    for i, subtask in enumerate(sub_tasks):
        progress = 70 + int((i / total_tasks) * 20)
        yield {
            "step": "subtask",
            "message": f"✅ 生成子任务 {i+1}/{total_tasks}",
            "progress": progress,
            "data": {
                "subtask_index": i + 1,
                "subtask_total": total_tasks,
                "subtask": subtask,
                "all_subtasks": sub_tasks[:i+1]
            }
        }
        # 模拟小延迟让用户能感受到过程
        import time
        time.sleep(0.3)
    
    # 步骤4: 保存到数据库
    yield {
        "step": "saving",
        "message": "💾 正在保存任务...",
        "progress": 95,
        "data": None
    }
    
    try:
        db.save_task(
            raw_task=raw_input,
            sub_tasks=sub_tasks,
            priority=priority,
            deadline=deadline,
            schedule=schedule
        )
    except Exception as e:
        print(f"[process_task_stream] 保存失败: {str(e)}")
    
    # 步骤5: 完成
    yield {
        "step": "completed",
        "message": "🎉 任务创建完成！",
        "progress": 100,
        "data": {
            "task_name": task_name,
            "deadline": deadline,
            "sub_tasks": sub_tasks,
            "priority": priority,
            "schedule": schedule
        }
    }


def save_to_db_node(state: TodoState) -> dict:
    """数据库保存节点"""
    print(f"[save_to_db_node] 开始保存到数据库")
    db.save_task(
        raw_task=state["raw_input"],
        sub_tasks=state["sub_tasks"],
        priority=state["priority"],
        deadline=state["task_info"]["截止日期"],
        schedule=state["schedule_plan"]
    )
    print(f"[save_to_db_node] 保存完成")
    return {"save_status": True}


# 初始化状态图
workflow = StateGraph(TodoState)

# 添加工作流节点（简化流程）
workflow.add_node("process_task", process_task_node)  # 一次性处理所有任务
workflow.add_node("save_to_db", save_to_db_node)  # 数据库保存节点

# 定义节点执行顺序
workflow.set_entry_point("process_task")
workflow.add_edge("process_task", "save_to_db")
workflow.add_edge("save_to_db", END)

# 编译工作流
agent = workflow.compile()
