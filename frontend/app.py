"""
智能待办与日程管理 Agent - Streamlit 前端应用

功能特性:
- 自然语言任务输入，AI智能解析
- 任务列表管理（创建/查看/筛选/删除）
- 子任务勾选与进度追踪
- 多维度筛选（状态/优先级/分类）
- 今日到期/逾期任务提醒
- 统计信息可视化
- 分类管理

API接口对接后端FastAPI服务
"""

import streamlit as st
import requests
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Generator
import time
import random

# ====================== 全局常量 ======================
BACKEND_URL = "http://localhost:8000"
API_TIMEOUT = 60  # API请求超时时间（秒）

# ====================== 工具函数 ======================
def call_api(endpoint: str, method: str = "GET", data: dict = None) -> dict:
    """调用后端API
    
    Args:
        endpoint: API端点
        method: 请求方法
        data: 请求数据
    
    Returns:
        dict: API响应结果
    """
    url = f"{BACKEND_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=API_TIMEOUT)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=API_TIMEOUT)
        elif method == "PUT":
            response = requests.put(url, json=data, timeout=API_TIMEOUT)
        elif method == "DELETE":
            response = requests.delete(url, timeout=API_TIMEOUT)
        else:
            return {"success": False, "error": "不支持的请求方法"}
        
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"success": False, "error": str(e)}

def call_api_stream(endpoint: str, data: dict = None) -> Generator[dict, None, None]:
    """流式调用后端API
    
    Args:
        endpoint: API端点
        data: 请求数据
    
    Yields:
        dict: 流式响应数据
    """
    url = f"{BACKEND_URL}{endpoint}"
    try:
        with requests.post(url, json=data, stream=True, timeout=API_TIMEOUT) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])
                            yield data
                        except json.JSONDecodeError:
                            pass
    except requests.RequestException as e:
        yield {"step": "error", "message": str(e), "progress": 0}

# ====================== 页面配置 ======================
st.set_page_config(
    page_title="智能待办与日程管理 Agent",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ====================== 侧边栏 ======================
with st.sidebar:
    st.title("智能待办与日程管理")
    st.markdown("基于 LangGraph + FastAPI + Streamlit 实现")
    
    # 导航菜单
    page = st.selectbox(
        "选择功能",
        ["📋 任务管理", "📊 统计分析", "📁 分类管理", "⚙️ 系统设置"]
    )
    
    # 系统状态
    st.markdown("---")
    st.subheader("系统状态")
    try:
        health = call_api("/api/health")
        if health.get("status") == "healthy":
            st.success("✅ 系统运行正常")
        else:
            st.error("❌ 系统状态异常")
    except:
        st.error("❌ 无法连接后端服务")

# ====================== 主页面 ======================
if page == "📋 任务管理":
    st.title("任务管理")
    
    # 任务创建
    with st.expander("📝 创建新任务", expanded=True):
        task_input = st.text_area(
            "输入任务描述（支持自然语言，例如：'明天完成项目报告'）",
            height=100
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("创建任务", use_container_width=True):
                if task_input.strip():
                    with st.spinner("AI正在分析任务..."):
                        result = call_api("/api/tasks", method="POST", data={"raw_input": task_input})
                        if result.get("success"):
                            st.success("任务创建成功！")
                            st.json(result.get("task_info", {}))
                        else:
                            st.error(f"任务创建失败: {result.get('error')}")
                else:
                    st.warning("请输入任务描述")
        
        with col2:
            if st.button("创建任务（流式）", use_container_width=True):
                if task_input.strip():
                    st.markdown("### AI分析过程")
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for event in call_api_stream("/api/tasks/stream", data={"raw_input": task_input}):
                        step = event.get("step")
                        message = event.get("message")
                        progress = event.get("progress", 0)
                        data = event.get("data")
                        
                        status_text.text(message)
                        progress_bar.progress(progress)
                        
                        if step == "subtask" and data:
                            st.markdown(f"- {data.get('subtask')}")
                        elif step == "completed" and data:
                            st.success("任务创建完成！")
                            st.json(data)
                        elif step == "error":
                            st.error(message)
                            break
                else:
                    st.warning("请输入任务描述")
    
    # 任务列表
    st.markdown("---")
    st.subheader("任务列表")
    
    # 筛选条件
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        status_filter = st.selectbox("状态", ["全部", "待执行", "进行中", "已完成"])
    with col2:
        priority_filter = st.selectbox("优先级", ["全部", "高", "中", "低"])
    with col3:
        category_filter = st.selectbox("分类", ["全部"] + ["工作", "生活", "学习"])
    with col4:
        keyword = st.text_input("关键词搜索")
    
    # 获取任务列表
    if st.button("刷新任务列表"):
        params = {}
        if status_filter != "全部":
            params["status"] = status_filter
        if priority_filter != "全部":
            params["priority"] = priority_filter
        if category_filter != "全部":
            params["category"] = category_filter
        if keyword:
            params["keyword"] = keyword
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        tasks = call_api(f"/api/tasks?{query_string}")
        
        if isinstance(tasks, list):
            for task in tasks:
                with st.expander(f"{task.get('raw_task')} (优先级: {task.get('priority')})"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**任务ID**: {task.get('id')}")
                        st.markdown(f"**截止日期**: {task.get('deadline')}")
                        st.markdown(f"**状态**: {task.get('status')}")
                        st.markdown(f"**分类**: {task.get('category')}")
                    with col2:
                        st.markdown(f"**创建时间**: {task.get('create_time')}")
                        st.markdown(f"**进度**: {task.get('progress', 0)}%")
                        st.markdown(f"**标签**: {', '.join(task.get('tags', []))}")
                    
                    st.markdown("**子任务**:")
                    for i, subtask in enumerate(task.get('sub_tasks', [])):
                        st.checkbox(f"{i+1}. {subtask}")
                    
                    st.markdown("**日程安排**:")
                    st.info(task.get('schedule', '无'))
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button(f"标记为完成", key=f"complete_{task.get('id')}"):
                            result = call_api(f"/api/tasks/{task.get('id')}/status", method="PUT", data={"status": "已完成"})
                            if result.get("success"):
                                st.success("任务状态已更新")
                            else:
                                st.error("更新失败")
                    with col2:
                        if st.button(f"删除任务", key=f"delete_{task.get('id')}"):
                            result = call_api(f"/api/tasks/{task.get('id')}", method="DELETE")
                            if result.get("success"):
                                st.success("任务已删除")
                            else:
                                st.error("删除失败")
                    with col3:
                        raw_progress = task.get('progress', 0)
                        try:
                            current_progress = int(float(raw_progress)) if raw_progress not in (None, [], '', 'null') else 0
                        except (ValueError, TypeError):
                            current_progress = 0
                        progress = st.slider(f"更新进度", 0, 100, current_progress, key=f"progress_{task.get('id')}")
                        if st.button(f"保存进度", key=f"save_progress_{task.get('id')}"):
                            result = call_api(f"/api/tasks/{task.get('id')}/progress", method="PUT", data={"progress": progress})
                            if result.get("success"):
                                st.success("进度已更新")
                            else:
                                st.error("更新失败")
        else:
            st.error("获取任务列表失败")

elif page == "📊 统计分析":
    st.title("统计分析")
    
    # 仪表盘数据
    with st.spinner("加载统计数据..."):
        dashboard = call_api("/api/dashboard")
        if isinstance(dashboard, dict):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("总任务数", len(dashboard.get("today_tasks", [])) + len(dashboard.get("overdue_tasks", [])))
            with col2:
                st.metric("今日到期", len(dashboard.get("today_tasks", [])))
            with col3:
                st.metric("已逾期", len(dashboard.get("overdue_tasks", [])))
            with col4:
                st.metric("完成率", f"{dashboard.get('stats', {}).get('completion_rate', 0)}%")
            
            # 今日任务
            st.subheader("今日到期任务")
            for task in dashboard.get("today_tasks", []):
                st.warning(f"{task.get('task')} (截止日期: {task.get('deadline')}, 优先级: {task.get('priority')})")
            
            # 逾期任务
            st.subheader("已逾期任务")
            for task in dashboard.get("overdue_tasks", []):
                st.error(f"{task.get('task')} (截止日期: {task.get('deadline')}, 优先级: {task.get('priority')})")
            
            # 最近7天统计
            st.subheader("最近7天任务统计")
            recent_stats = dashboard.get('stats', {}).get('recent_stats', [])
            if recent_stats:
                dates = [stat.get('date') for stat in recent_stats]
                created = [stat.get('created') for stat in recent_stats]
                completed = [stat.get('completed') for stat in recent_stats]
                
                # 创建 DataFrame 用于图表
                import pandas as pd
                chart_df = pd.DataFrame({
                    "日期": dates,
                    "创建任务": created,
                    "完成任务": completed
                }).set_index("日期")
                st.line_chart(chart_df)
        else:
            st.error("获取统计数据失败")

elif page == "📁 分类管理":
    st.title("分类管理")
    
    # 获取分类列表
    categories = call_api("/api/categories")
    if isinstance(categories, list):
        st.subheader("现有分类")
        for cat in categories:
            st.markdown(f"- {cat.get('icon')} {cat.get('name')} (颜色: {cat.get('color')})")
    
    # 创建新分类
    st.subheader("创建新分类")
    col1, col2, col3 = st.columns(3)
    with col1:
        cat_name = st.text_input("分类名称")
    with col2:
        cat_color = st.color_picker("分类颜色", "#3b82f6")
    with col3:
        cat_icon = st.text_input("分类图标", "📁")
    
    if st.button("创建分类"):
        if cat_name:
            result = call_api("/api/categories", method="POST", data={"name": cat_name, "color": cat_color, "icon": cat_icon})
            if result.get("success"):
                st.success("分类创建成功！")
            else:
                st.error(f"创建失败: {result.get('error')}")
        else:
            st.warning("请输入分类名称")

elif page == "⚙️ 系统设置":
    st.title("系统设置")
    
    # API配置
    st.subheader("API配置")
    if 'backend_url' not in st.session_state:
        st.session_state.backend_url = BACKEND_URL
    backend_url_input = st.text_input("后端服务地址", value=st.session_state.backend_url)
    if st.button("保存配置"):
        st.session_state.backend_url = backend_url_input
        st.success("配置已保存，请刷新页面使配置生效")
    
    # 系统信息
    st.subheader("系统信息")
    try:
        health = call_api("/api/health")
        st.json(health)
    except:
        st.error("无法获取系统信息")

# ====================== 页脚 ======================
st.markdown("---")
st.markdown("智能待办与日程管理 Agent v2.0 | 基于 LangGraph + FastAPI + Streamlit 实现")
