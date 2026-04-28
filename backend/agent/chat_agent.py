"""
智能对话 Agent 模块

基于 LangGraph 构建的对话系统，支持：
- 多轮对话：保持上下文记忆
- 意图识别：自动识别用户意图（创建任务/查询任务/闲聊）
- 槽位填充：提取关键信息（时间、优先级等）
- 知识库检索：基于 RAG 技术增强回答

对话工作流：
1. recognize_intent_node - 识别用户意图
2. retrieve_knowledge_node - 检索相关知识
3. generate_response_node - 生成回复

系统会保存对话历史，支持会话管理和导出功能。
"""
import json
import os
from typing import TypedDict, List, Annotated, Optional
from datetime import datetime
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from .llm_config import client, model
from ..db.db_handler import db

# 定义对话状态
class ChatState(TypedDict):
    session_id: str
    user_id: int
    messages: List[BaseMessage]
    intent: Optional[str]
    slots: dict
    knowledge: List[dict]
    response: str

# 意图识别与槽位填充系统提示词
INTENT_SYSTEM_PROMPT = """你是一个智能意图分析助手。
分析用户的最新消息，识别其意图和关键信息（槽位）。

目前支持的意图：
1. create_task: 创建新任务。槽位：task_name, deadline, priority
2. query_task: 查询任务。槽位：status, category, keyword
3. general_chat: 通用闲聊或咨询。
4. help: 获取使用帮助。

仅返回以下 JSON 格式：
{
    "intent": "意图名称",
    "slots": {"key": "value"},
    "confidence": 0.0-1.0
}"""

def recognize_intent_node(state: ChatState) -> dict:
    """意图识别节点"""
    last_message = state['messages'][-1].content

    # 构造提示词，让模型返回JSON格式
    prompt_with_format = INTENT_SYSTEM_PROMPT + "\n\n请直接返回JSON，不要包含任何其他文字。"

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt_with_format},
            {"role": "user", "content": last_message}
        ],
        temperature=0
    )

    # 解析JSON响应，处理可能的格式问题
    raw_content = response.choices[0].message.content
    try:
        # 尝试直接解析
        data = json.loads(raw_content)
    except json.JSONDecodeError:
        # 如果失败，尝试提取JSON对象
        import re
        json_match = re.search(r'\{[^{}]*\}', raw_content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
            except json.JSONDecodeError:
                # 返回默认值
                return {
                    "intent": "general_chat",
                    "slots": {}
                }
        else:
            return {
                "intent": "general_chat",
                "slots": {}
            }

    return {
        "intent": data.get("intent", "general_chat"),
        "slots": data.get("slots", {})
    }

def retrieve_knowledge_node(state: ChatState) -> dict:
    """知识检索节点"""
    last_message = state['messages'][-1].content
    results = db.search_knowledge(last_message)
    
    knowledge = [{"title": r[0], "content": r[1]} for r in results]
    return {"knowledge": knowledge}

def generate_response_node(state: ChatState) -> dict:
    """回复生成节点"""
    messages = []

    # 构建上下文
    system_msg = "你是一个名为 'Smart Planner' 的智能助手。你可以帮用户管理任务、日程，并回答相关问题。"
    if state['knowledge']:
        system_msg += "\n以下是相关的参考知识：\n"
        for k in state['knowledge']:
            system_msg += f"- {k['title']}: {k['content']}\n"

    messages.append({"role": "system", "content": system_msg})

    # 添加历史对话
    for msg in state['messages'][-6:]: # 最近 3 轮
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        messages.append({"role": role, "content": msg.content})

    # 调用 LLM
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7
        )
        content = response.choices[0].message.content

        # 检查content是否为None
        if content is None:
            content = "抱歉，我现在无法生成回复，请稍后再试。"

    except Exception as e:
        # 记录错误并返回友好的错误消息
        import logging
        logging.error(f"LLM调用失败: {str(e)}")
        content = "抱歉，AI服务暂时不可用，请稍后再试。"

    # 异步保存到数据库
    try:
        db.add_chat_message(
            state['session_id'],
            "assistant",
            content,
            state.get('intent'),
            state.get('slots', {})
        )
    except Exception as e:
        logging.error(f"保存聊天消息失败: {str(e)}")

    return {"response": content}

# 构建图
workflow = StateGraph(ChatState)

workflow.add_node("recognize_intent", recognize_intent_node)
workflow.add_node("retrieve_knowledge", retrieve_knowledge_node)
workflow.add_node("generate_response", generate_response_node)

workflow.set_entry_point("recognize_intent")
workflow.add_edge("recognize_intent", "retrieve_knowledge")
workflow.add_edge("retrieve_knowledge", "generate_response")
workflow.add_edge("generate_response", END)

chat_agent = workflow.compile()

def process_chat(session_id: str, user_id: int, message: str) -> str:
    """处理聊天请求"""
    # 1. 保存用户消息
    db.add_chat_message(session_id, "user", message)
    
    # 2. 加载历史消息
    history = db.get_session_messages(session_id, limit=10)
    messages = []
    for h in history:
        if h[0] == 'user':
            messages.append(HumanMessage(content=h[1]))
        else:
            messages.append(AIMessage(content=h[1]))
            
    # 3. 运行 Agent
    inputs = {
        "session_id": session_id,
        "user_id": user_id,
        "messages": messages,
        "intent": None,
        "slots": {},
        "knowledge": [],
        "response": ""
    }
    
    result = chat_agent.invoke(inputs)
    return result['response']
