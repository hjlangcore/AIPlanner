"""
AIPlanner 后端 API 主入口文件

提供 RESTful API 接口，对接前端和后端 Agent 核心功能。

主要功能模块：
- 用户认证 (JWT)
- 任务管理 (CRUD)
- 智能对话 (Agent)
- 知识库管理 (RAG)
- 提醒服务 (定时任务)
- 数据备份与恢复

支持 SSE 流式输出，实时返回 AI 处理进度。

启动命令：uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
"""
from fastapi import FastAPI, Query, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Generic, TypeVar
import sys
import os
import logging
import json
import time
from functools import wraps

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agent.workflow import agent, process_task_stream
from backend.agent.chat_agent import process_chat
from backend.agent.agent_workflow import process_agent_message, process_agent_message_stream
from backend.db.db_handler import db
from backend.service.reminder_service import reminder_service
from backend.service.email_service import email_reminder_service
from backend.service.backup_service import backup_service
from backend.service.rag_service import rag_service
from backend.service.tag_service import tag_service
from backend.service.auth_service import get_password_hash, verify_password, create_access_token, get_current_user, get_current_user_async, require_role, require_permission, Role

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ====================== 通用响应模型 ======================
T = TypeVar('T')

class ApiResponse(BaseModel, Generic[T]):
    """统一API响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field("", description="响应消息")
    data: Optional[T] = Field(None, description="响应数据")
    error_code: Optional[int] = Field(None, description="错误码")
    timestamp: float = Field(default_factory=time.time, description="时间戳")

class ApiError(BaseModel):
    """API错误模型"""
    code: int
    message: str
    details: Optional[str] = None

# ====================== 自定义异常类 ======================
class AppException(Exception):
    """应用异常基类"""
    def __init__(self, message: str, error_code: int = 500, details: Optional[str] = None):
        self.message = message
        self.error_code = error_code
        self.details = details
        super().__init__(message)

class ValidationException(AppException):
    """验证异常"""
    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(message, 400, details)

class NotFoundException(AppException):
    """资源未找到异常"""
    def __init__(self, message: str = "资源未找到", details: Optional[str] = None):
        super().__init__(message, 404, details)

class UnauthorizedException(AppException):
    """未授权异常"""
    def __init__(self, message: str = "未授权", details: Optional[str] = None):
        super().__init__(message, 401, details)

class ConflictException(AppException):
    """资源冲突异常"""
    def __init__(self, message: str = "资源冲突", details: Optional[str] = None):
        super().__init__(message, 409, details)

# ====================== 装饰器 ======================
def with_retry(max_retries: int = 3, delay: float = 1.0):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs) if hasattr(func, '__await__') else func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(f"函数 {func.__name__} 执行失败，第 {attempt + 1} 次尝试: {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator

# 初始化FastAPI应用
app = FastAPI(
    title="智能待办与日程管理 Agent API",
    version="2.1.0",
    description="提供智能待办任务的管理接口，支持任务创建、筛选、统计等功能"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有源，开发环境建议
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====================== 统一异常处理器 ======================
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """处理HTTP异常"""
    logger.error(f"HTTP异常: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": str(exc.detail),
            "error_code": exc.status_code,
            "timestamp": time.time()
        }
    )

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """处理应用异常"""
    logger.error(f"应用异常: {exc.error_code} - {exc.message}")
    return JSONResponse(
        status_code=exc.error_code,
        content={
            "success": False,
            "message": exc.message,
            "error_code": exc.error_code,
            "details": exc.details,
            "timestamp": time.time()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """处理通用异常"""
    logger.error(f"未处理异常: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "服务器内部错误",
            "error_code": 500,
            "timestamp": time.time()
        }
    )


# ====================== 请求/响应模型 ======================
class UserRegister(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    email: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatSessionCreate(BaseModel):
    title: str = "新对话"

class TaskCreate(BaseModel):
    """创建任务请求模型（AI自动创建）"""
    raw_input: str  # 用户原始输入的自然语言任务


class TaskManualCreate(BaseModel):
    """手动创建任务请求模型"""
    raw_task: str
    sub_tasks: Optional[List[str]] = None
    priority: Optional[str] = "中"
    deadline: Optional[str] = None
    schedule: Optional[str] = ""
    category: Optional[str] = "默认"
    tags: Optional[List[str]] = None
    notes: Optional[str] = ""


class TaskUpdate(BaseModel):
    """更新任务请求模型"""
    raw_task: Optional[str] = None
    sub_tasks: Optional[List[str]] = None
    priority: Optional[str] = None
    deadline: Optional[str] = None
    schedule: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None


class TaskStatusUpdate(BaseModel):
    """任务状态更新模型"""
    status: str  # 新的任务状态


class TaskProgressUpdate(BaseModel):
    """任务进度更新模型"""
    progress: int  # 进度值 0-100


class CategoryCreate(BaseModel):
    """创建分类请求模型"""
    name: str
    color: str = "#3b82f6"
    icon: str = "📁"


# ====================== 辅助函数 ======================
def task_to_dict(task: tuple) -> dict:
    """将数据库任务元组转换为字典
    注意：数据库实际列顺序（因 ALTER TABLE 添加列到末尾）:
    0: id, 1: raw_task, 2: sub_tasks, 3: priority, 4: deadline, 5: schedule,
    6: status, 7: create_time, 8: category, 9: tags, 10: progress, 11: notes, 12: update_time
    为避免字段错位，按实际列顺序读取并解析JSON字段。"""
    import json
    if not task:
        return None
    
    # 尝试解析JSON字段，按实际列顺序读取
    try:
        sub_tasks = json.loads(task[2]) if task[2] else []
    except Exception:
        sub_tasks = [task[2]] if task[2] else []
    
    try:
        tags = json.loads(task[9]) if task[9] else []
    except Exception:
        tags = []
    
    # 结合数据库实际列顺序，映射字段
    idx = {
        "id": 0,
        "raw_task": 1,
        "sub_tasks": 2,
        "priority": 3,
        "deadline": 4,
        "schedule": 5,
        "status": 6,
        "create_time": 7,
        "category": 8,
        "tags": 9,
        "progress": 10,
        "notes": 11,
        "update_time": 12,
    }

    return {
        "id": task[0],
        "raw_task": task[1],
        "sub_tasks": sub_tasks,
        "priority": task[3],
        "deadline": task[4],
        "schedule": task[5],
        "status": task[6],
        "create_time": task[7] if len(task) > 7 else "",
        "category": task[8] if len(task) > 8 else "默认",
        "tags": tags,
        "progress": task[10] if len(task) > 10 else 0,
        "notes": task[11] if len(task) > 11 else "",
        "update_time": task[12] if len(task) > 12 else ""
    }


# ====================== 生命周期事件 ======================
@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    # 启动定时提醒服务 (APScheduler 内部会自动管理线程)
    reminder_service.start()
    
    # 设置邮件服务
    reminder_service.set_email_service(email_reminder_service)
    
    # 如果邮件服务已配置，则启动 (EmailReminderService 现在也使用 APScheduler 或同步检查)
    # 注意：我们的 reminder_service.check_deadline 已经包含了邮件逻辑
    
    logger.info("智能待办Agent服务已启动 v2.0")


# ====================== 用户认证接口 ======================
@app.post("/api/auth/register", summary="用户注册")
async def register(user: UserRegister):
    """用户注册接口
    
    Args:
        user: 用户注册信息（用户名、密码、姓名、邮箱）
    
    Returns:
        dict: 注册结果
    """
    # 注册接口对所有用户开放
    try:
        existing_user = db.get_user_by_username(user.username)
        if existing_user:
            raise HTTPException(status_code=400, detail="用户名已存在")
        
        password_hash = get_password_hash(user.password)
        user_id = db.create_user(
            username=user.username,
            password_hash=password_hash,
            full_name=user.full_name,
            email=user.email
        )
        
        logger.info(f"用户注册成功: {user.username}")
        return {
            "success": True,
            "message": "注册成功",
            "user_id": user_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"注册失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"注册失败: {str(e)}")


@app.post("/api/auth/login", summary="用户登录")
async def login(user: UserLogin):
    """用户登录接口
    
    Args:
        user: 用户登录信息（用户名、密码）
    
    Returns:
        dict: 登录结果（access_token、token_type、user信息）
    """
    try:
        db_user = db.get_user_by_username(user.username)
        if not db_user:
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        
        if not verify_password(user.password, db_user[2]):
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        
        access_token = create_access_token(data={"sub": db_user[1], "user_id": db_user[0]})
        
        logger.info(f"用户登录成功: {user.username}")
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "username": db_user[1],
                "full_name": db_user[3] or db_user[1],
                "role": db_user[5]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"登录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")


@app.get("/api/auth/me", summary="获取当前用户信息")
async def get_me(current_user: dict = Depends(get_current_user_async)):
    """获取当前登录用户信息
    
    Args:
        current_user: 当前用户（从JWT令牌解析）
    
    Returns:
        dict: 用户信息
    """
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "full_name": current_user.get("full_name"),
        "email": current_user.get("email"),
        "role": current_user.get("role", "user")
    }


# ====================== 用户管理接口 ======================
@app.get("/api/users", summary="获取所有用户")
@require_role(Role.ADMIN)
async def get_all_users(current_user: dict = Depends(get_current_user_async)):
    """获取所有用户列表（仅管理员）
    
    Returns:
        list: 用户列表
    """
    try:
        users = db.get_all_users()
        return [
            {
                "id": u[0],
                "username": u[1],
                "full_name": u[2],
                "email": u[3],
                "role": u[4],
                "created_at": u[5]
            }
            for u in users
        ]
    except Exception as e:
        logger.error(f"获取用户列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取用户列表失败: {str(e)}")


@app.put("/api/users/{user_id}/role", summary="更新用户角色")
@require_role(Role.ADMIN)
async def update_user_role(user_id: int, role: str, current_user: dict = Depends(get_current_user_async)):
    """更新用户角色（仅管理员）
    
    Args:
        user_id: 用户ID
        role: 新角色
    
    Returns:
        dict: 更新结果
    """
    try:
        if role not in [Role.ADMIN, Role.USER]:
            raise HTTPException(status_code=400, detail="无效的角色")
        
        success = db.update_user_role(user_id, role)
        if success:
            return {"success": True, "message": "角色更新成功"}
        else:
            raise HTTPException(status_code=404, detail="用户不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新用户角色失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新用户角色失败: {str(e)}")

# ====================== 智能对话接口 ======================
@app.post("/api/chat/sessions")
async def create_session(session: ChatSessionCreate, current_user: dict = Depends(get_current_user_async)):
    import uuid
    session_id = str(uuid.uuid4())
    db.create_chat_session(session_id, current_user['id'], session.title)
    return {"session_id": session_id}

@app.get("/api/chat/sessions")
async def get_sessions(current_user: dict = Depends(get_current_user_async)):
    sessions = db.get_user_sessions(current_user['id'])
    return [
        {"id": s[0], "title": s[2], "created_at": s[3], "updated_at": s[4]}
        for s in sessions
    ]

@app.delete("/api/chat/sessions/{session_id}")
async def delete_session(session_id: str, current_user: dict = Depends(get_current_user_async)):
    """删除指定会话"""
    try:
        db.delete_chat_session(session_id)
        return {"success": True}
    except Exception as e:
        logger.error(f"删除会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除会话失败")

@app.post("/api/chat/message")
async def chat_message(req: ChatRequest, current_user: dict = Depends(get_current_user_async)):
    try:
        response = process_chat(req.session_id, current_user['id'], req.message)
        return {"response": response}
    except Exception as e:
        logger.error(f"对话处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail="系统处理对话时出错")


@app.post("/api/agent/message")
async def agent_message(req: ChatRequest, current_user: dict = Depends(get_current_user_async)):
    """AI Agent消息处理接口
    
    Args:
        req: 聊天请求
        current_user: 当前用户
    
    Returns:
        Agent处理结果
    """
    try:
        result = process_agent_message(req.session_id, current_user['id'], req.message)
        return {
            "response": result["response"],
            "agent_state": result["agent_state"],
            "tool_calls": result["tool_calls"],
            "plan": result["plan"]
        }
    except Exception as e:
        logger.error(f"Agent处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail="系统处理Agent请求时出错")


async def agent_sse_event_generator(session_id: str, user_id: int, message: str):
    """Agent SSE事件生成器"""
    try:
        for event in process_agent_message_stream(session_id, user_id, message):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'step': 'error', 'message': str(e), 'progress': 0}, ensure_ascii=False)}\n\n"


@app.post("/api/agent/message/stream")
async def agent_message_stream(req: ChatRequest, current_user: dict = Depends(get_current_user_async)):
    """AI Agent流式消息处理接口
    
    Args:
        req: 聊天请求
        current_user: 当前用户
    
    Returns:
        SSE流式响应
    """
    logger.info(f"开始流式处理Agent请求: {req.message}")
    
    return StreamingResponse(
        agent_sse_event_generator(req.session_id, current_user['id'], req.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/agent/message/stream")
async def agent_message_stream_get(
    session_id: str = Query(..., description="会话ID"),
    message: str = Query(..., description="用户消息"),
    token: str = Query(None, description="JWT Token (EventSource无法设置Header)")
):
    """AI Agent流式消息处理接口 (GET版本 - 兼容EventSource)
    
    EventSource 只能发起 GET 请求且无法设置自定义 Headers，
    因此使用 Query 参数传递 session_id、message 和 token。
    
    Args:
        session_id: 会话ID
        message: 用户消息
        token: JWT Token
    
    Returns:
        SSE流式响应
    """
    # 验证 Token
    if not token:
        error_event = f"data: {json.dumps({'step': 'error', 'message': '缺少认证令牌', 'progress': 0}, ensure_ascii=False)}\n\n"
        return StreamingResponse(
            iter([error_event]),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    
    try:
        # 直接解析 JWT Token
        from backend.service.auth_service import SECRET_KEY, ALGORITHM
        import jwt as pyjwt
        
        # 清理 token (移除 "Bearer " 前缀如果有的话)
        clean_token = token.replace("Bearer ", "").strip()
        
        payload = pyjwt.decode(clean_token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            error_event = f"data: {json.dumps({'step': 'error', 'message': '无效的凭证', 'progress': 0}, ensure_ascii=False)}\n\n"
            return StreamingResponse(
                iter([error_event]),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        
        user = db.get_user_by_username(username)
        if not user:
            error_event = f"data: {json.dumps({'step': 'error', 'message': '用户不存在', 'progress': 0}, ensure_ascii=False)}\n\n"
            return StreamingResponse(
                iter([error_event]),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        
        user_id = user[0]
        logger.info(f"[GET SSE] 开始流式处理Agent请求: {message[:50]}..., user_id={user_id}")
        
        # 返回 StreamingResponse
        return StreamingResponse(
            agent_sse_event_generator(session_id, user_id, message),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
        
    except pyjwt.ExpiredSignatureError:
        logger.error(f"[GET SSE] Token已过期")
        error_event = f"data: {json.dumps({'step': 'error', 'message': '登录已过期，请重新登录', 'progress': 0}, ensure_ascii=False)}\n\n"
        return StreamingResponse(
            iter([error_event]),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    except Exception as e:
        logger.error(f"[GET SSE] Agent处理失败: {str(e)}", exc_info=True)
        error_event = f"data: {json.dumps({'step': 'error', 'message': str(e), 'progress': 0}, ensure_ascii=False)}\n\n"
        return StreamingResponse(
            iter([error_event]),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )


@app.get("/api/chat/messages/{session_id}")
async def get_messages(session_id: str, current_user: dict = Depends(get_current_user_async)):
    # 验证权限（简单检查，后续可加强）
    messages = db.get_session_messages(session_id)
    return [
        {"role": m[0], "content": m[1], "intent": m[2], "slots": json.loads(m[3]) if m[3] else {}, "created_at": m[4]}
        for m in messages
    ]

@app.get("/api/chat/export/{session_id}")
async def export_chat(session_id: str, current_user: dict = Depends(get_current_user_async)):
    messages = db.get_session_messages(session_id)
    content = "智能记录中心 - 对话历史导出\n"
    content += "="*30 + "\n\n"
    for m in messages:
        role = "用户" if m[0] == 'user' else "助手"
        content += f"[{m[4]}] {role}: {m[1]}\n"
        if m[2]:
            content += f" (识别意图: {m[2]})\n"
        content += "-"*20 + "\n"
    
    from fastapi.responses import Response
    return Response(
        content=content,
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename=chat_history_{session_id}.txt"}
    )


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    reminder_service.stop()
    logger.info("智能待办Agent服务已关闭")


# ====================== 健康检查 ======================
@app.get("/")
async def root():
    """健康检查接口"""
    return {
        "message": "智能待办与日程管理 Agent API",
        "version": "2.0.0",
        "status": "running"
    }


@app.get("/api/health")
async def health_check():
    """详细健康检查"""
    return {
        "status": "healthy",
        "database": "connected",
        "llm": "ready"
    }


# ====================== 任务管理接口 ======================
@app.post("/api/tasks/conflicts", response_model=dict)
async def check_task_conflicts(deadline: str, task_id: Optional[int] = None):
    """检查任务冲突
    
    Args:
        deadline: 任务截止日期
        task_id: 任务ID（用于排除自身）
    
    Returns:
        dict: 冲突检测结果
    """
    try:
        conflicts = db.check_task_conflicts(task_id, deadline)
        import json
        return {
            "success": True,
            "has_conflicts": len(conflicts) > 0,
            "conflicts": [
                {
                    "id": c[0],
                    "raw_task": c[1],
                    "priority": c[3],
                    "status": c[6],
                    "deadline": c[4],
                    "progress": c[10],
                    "category": c[8]
                }
                for c in conflicts
            ]
        }
    except Exception as e:
        logger.error(f"检查任务冲突失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/tasks", response_model=dict)
async def create_task(task: TaskCreate):
    """创建新任务（AI自动创建，非流式版本）
    
    Args:
        task: 任务创建请求
    
    Returns:
        dict: 创建结果
    """
    try:
        logger.info(f"开始处理创建任务请求: {task.raw_input}")
        result = agent.invoke({"raw_input": task.raw_input})
        logger.info(f"工作流执行完成: {result.get('save_status')}")
        
        return {
            "success": result.get("save_status", False),
            "task_info": {
                "raw_input": result.get("raw_input"),
                "task_name": result.get("task_info", {}).get("任务名称"),
                "deadline": result.get("task_info", {}).get("截止日期"),
                "sub_tasks": result.get("sub_tasks", []),
                "priority": result.get("priority"),
                "schedule_plan": result.get("schedule_plan")
            }
        }
    except Exception as e:
        logger.error(f"创建任务失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/tasks/manual", response_model=dict)
async def create_task_manual(task: TaskManualCreate):
    """手动创建新任务（不走AI分析，直接保存）
    
    Args:
        task: 手动任务创建请求
    
    Returns:
        dict: 创建结果
    """
    try:
        logger.info(f"手动创建任务: {task.raw_task}")
        task_id = db.save_task(
            raw_task=task.raw_task,
            sub_tasks=task.sub_tasks or [],
            priority=task.priority or "中",
            deadline=task.deadline,
            schedule=task.schedule or "",
            category=task.category or "默认",
            tags=task.tags or []
        )
        logger.info(f"手动创建任务成功: ID={task_id}")
        return {
            "success": True,
            "task_id": task_id,
            "message": f"任务 '{task.raw_task}' 创建成功"
        }
    except Exception as e:
        logger.error(f"手动创建任务失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


async def sse_event_generator(raw_input: str):
    """SSE事件生成器"""
    try:
        # 在新线程中运行同步的process_task_stream
        import threading
        import queue
        
        result_queue = queue.Queue()
        
        def run_stream():
            for event in process_task_stream(raw_input):
                result_queue.put(event)
        
        thread = threading.Thread(target=run_stream)
        thread.start()
        
        # 从队列中获取结果并发送
        while thread.is_alive() or not result_queue.empty():
            try:
                event = result_queue.get(timeout=0.5)
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            except queue.Empty:
                continue
        
        thread.join()
        
    except Exception as e:
        yield f"data: {json.dumps({'step': 'error', 'message': str(e), 'progress': 0}, ensure_ascii=False)}\n\n"


@app.post("/api/tasks/stream")
async def create_task_stream(task: TaskCreate):
    """创建新任务（流式版本）
    
    使用Server-Sent Events实时返回任务处理进度，
    让用户看到AI分析和子任务生成过程。
    
    Args:
        task: 任务创建请求
    
    Returns:
        StreamingResponse: SSE流式响应
    """
    logger.info(f"开始流式处理任务: {task.raw_input}")
    
    return StreamingResponse(
        sse_event_generator(task.raw_input),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/tasks", response_model=list)
async def get_all_tasks(
    status: Optional[str] = Query(None, description="按状态筛选"),
    priority: Optional[str] = Query(None, description="按优先级筛选"),
    category: Optional[str] = Query(None, description="按分类筛选"),
    keyword: Optional[str] = Query(None, description="关键词搜索")
):
    """获取任务列表（支持多条件筛选）
    
    Returns:
        list: 任务列表
    """
    tasks = db.get_all_tasks(status=status, priority=priority, category=category, keyword=keyword)
    return [task_to_dict(task) for task in tasks]


@app.get("/api/tasks/{task_id}", response_model=dict)
async def get_task(task_id: int):
    """获取指定任务详情
    
    Args:
        task_id: 任务ID
    
    Returns:
        dict: 任务详情
    """
    task = db.get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task_to_dict(task)


@app.put("/api/tasks/{task_id}", response_model=dict)
async def update_task(task_id: int, update: TaskUpdate):
    """更新任务信息
    
    Args:
        task_id: 任务ID
        update: 更新内容
    
    Returns:
        dict: 更新结果
    """
    success = db.update_task(
        task_id,
        raw_task=update.raw_task,
        sub_tasks=update.sub_tasks,
        priority=update.priority,
        deadline=update.deadline,
        schedule=update.schedule,
        category=update.category,
        tags=update.tags,
        notes=update.notes
    )
    return {"success": success}


@app.put("/api/tasks/{task_id}/status", response_model=dict)
async def update_task_status(task_id: int, update: TaskStatusUpdate):
    """更新任务状态
    
    Args:
        task_id: 任务ID
        update: 状态更新请求
    
    Returns:
        dict: 更新结果
    """
    success = db.update_task_status(task_id, update.status)
    return {"success": success}


@app.put("/api/tasks/{task_id}/progress", response_model=dict)
async def update_task_progress(task_id: int, update: TaskProgressUpdate):
    """更新任务进度
    
    Args:
        task_id: 任务ID
        update: 进度更新请求
    
    Returns:
        dict: 更新结果
    """
    if update.progress < 0 or update.progress > 100:
        raise HTTPException(status_code=400, detail="进度值必须在0-100之间")
    
    success = db.update_task_progress(task_id, update.progress)
    return {"success": success}


class SubTaskStatusUpdate(BaseModel):
    """子任务状态更新模型"""
    sub_task_index: int
    completed: bool


@app.put("/api/tasks/{task_id}/subtasks", response_model=dict)
async def update_sub_task_status(task_id: int, update: SubTaskStatusUpdate):
    """更新子任务完成状态
    
    Args:
        task_id: 任务ID
        update: 子任务状态更新请求
    
    Returns:
        dict: 更新结果
    """
    success = db.update_sub_task_status(task_id, update.sub_task_index, update.completed)
    return {"success": success}


@app.delete("/api/tasks/{task_id}", response_model=dict)
async def delete_task(task_id: int):
    """删除任务

    Args:
        task_id: 任务ID

    Returns:
        dict: 删除结果
    """
    success = db.delete_task(task_id)
    return {"success": success}


@app.get("/api/tasks/conflicts", summary="检查任务冲突")
async def check_task_conflicts(
    task_id: Optional[int] = Query(None, description="任务ID，用于排除自身"),
    deadline: str = Query(..., description="任务截止日期，格式：YYYY-MM-DD"),
    status: Optional[str] = Query(None, description="任务状态，可选")
):
    """检查指定日期的任务冲突

    Args:
        task_id: 任务ID，用于排除自身
        deadline: 任务截止日期
        status: 任务状态，可选

    Returns:
        list: 冲突的任务列表
    """
    try:
        conflicts = db.check_task_conflicts(task_id, deadline, status)
        import json
        return [
            {
                "id": t[0],
                "raw_task": t[1],
                "sub_tasks": json.loads(t[2]) if t[2] else [],
                "priority": t[3],
                "deadline": t[4],
                "schedule": t[5],
                "status": t[6],
                "create_time": t[7],
                "category": t[8],
                "tags": json.loads(t[9]) if t[9] else [],
                "progress": t[10],
                "notes": t[11],
                "update_time": t[12]
            }
            for t in conflicts
        ]
    except Exception as e:
        logger.error(f"检查任务冲突失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"检查任务冲突失败: {str(e)}")


# ====================== 知识库管理接口 ======================
class KnowledgeBaseRequest(BaseModel):
    """知识库请求模型"""
    title: str
    content: str
    category: Optional[str] = "默认"
    tags: Optional[str] = ""


class KnowledgeBaseUpdateRequest(BaseModel):
    """知识库更新请求模型"""
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None


@app.get("/api/knowledge", summary="获取知识库列表")
async def get_knowledge_list(category: Optional[str] = Query(None, description="按分类筛选")):
    """获取知识库列表

    Args:
        category: 分类筛选

    Returns:
        list: 知识库条目列表
    """
    try:
        knowledge_list = rag_service.get_all_knowledge(category)
        return {"success": True, "data": knowledge_list}
    except Exception as e:
        logger.error(f"获取知识库列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取知识库列表失败: {str(e)}")


@app.get("/api/knowledge/categories", summary="获取知识库分类")
async def get_knowledge_categories():
    """获取知识库所有分类

    Returns:
        list: 分类列表
    """
    try:
        categories = rag_service.get_categories()
        return {"success": True, "categories": categories}
    except Exception as e:
        logger.error(f"获取分类失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取分类失败: {str(e)}")


@app.get("/api/knowledge/search", summary="搜索知识库")
async def search_knowledge(
    q: str = Query(..., description="搜索关键词"),
    limit: int = Query(5, ge=1, le=20, description="返回结果数量"),
    use_semantic: bool = Query(True, description="是否使用语义检索")
):
    """搜索知识库

    Args:
        q: 搜索关键词
        limit: 返回结果数量
        use_semantic: 是否使用语义检索

    Returns:
        list: 匹配的知识库条目
    """
    try:
        results = rag_service.search_knowledge(q, limit=limit, use_semantic=use_semantic)
        return {"success": True, "results": results}
    except Exception as e:
        logger.error(f"搜索知识库失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"搜索知识库失败: {str(e)}")


@app.get("/api/knowledge/{kb_id}", summary="获取知识库条目")
async def get_knowledge(kb_id: int):
    """获取指定知识库条目详情

    Args:
        kb_id: 知识库ID

    Returns:
        dict: 知识库条目详情
    """
    try:
        kb = rag_service.get_knowledge_by_id(kb_id)
        if not kb:
            raise HTTPException(status_code=404, detail="知识库条目不存在")
        return {"success": True, "data": kb}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取知识库条目失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取知识库条目失败: {str(e)}")


@app.post("/api/knowledge", summary="添加知识库条目")
async def add_knowledge(request: KnowledgeBaseRequest):
    """添加新的知识库条目

    Args:
        request: 知识库条目信息

    Returns:
        dict: 添加结果
    """
    try:
        kb_id = rag_service.add_knowledge(
            title=request.title,
            content=request.content,
            category=request.category,
            tags=request.tags
        )
        return {"success": True, "message": "知识库条目添加成功", "kb_id": kb_id}
    except Exception as e:
        logger.error(f"添加知识库条目失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"添加知识库条目失败: {str(e)}")


@app.put("/api/knowledge/{kb_id}", summary="更新知识库条目")
async def update_knowledge(kb_id: int, request: KnowledgeBaseUpdateRequest):
    """更新知识库条目

    Args:
        kb_id: 知识库ID
        request: 更新信息

    Returns:
        dict: 更新结果
    """
    try:
        title = request.title if request.title is not None else ""
        content = request.content if request.content is not None else ""

        success = rag_service.update_knowledge(
            kb_id=kb_id,
            title=title,
            content=content,
            category=request.category,
            tags=request.tags
        )

        if success:
            return {"success": True, "message": "知识库条目更新成功"}
        else:
            raise HTTPException(status_code=404, detail="知识库条目不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新知识库条目失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新知识库条目失败: {str(e)}")


@app.delete("/api/knowledge/{kb_id}", summary="删除知识库条目")
async def delete_knowledge(kb_id: int):
    """删除知识库条目

    Args:
        kb_id: 知识库ID

    Returns:
        dict: 删除结果
    """
    try:
        success = rag_service.delete_knowledge(kb_id)
        if success:
            return {"success": True, "message": "知识库条目删除成功"}
        else:
            raise HTTPException(status_code=404, detail="知识库条目不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除知识库条目失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除知识库条目失败: {str(e)}")


@app.get("/api/knowledge/context", summary="获取增强上下文")
async def get_knowledge_context(
    q: str = Query(..., description="查询关键词"),
    max_contexts: int = Query(3, ge=1, le=10, description="最大上下文数量")
):
    """为AI查询获取增强上下文

    Args:
        q: 查询关键词
        max_contexts: 最大上下文数量

    Returns:
        dict: 上下文字符串
    """
    try:
        context = rag_service.get_context_for_query(q, max_contexts=max_contexts)
        return {"success": True, "context": context}
    except Exception as e:
        logger.error(f"获取增强上下文失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取增强上下文失败: {str(e)}")


# ====================== 筛选预设接口 ======================
class FilterPresetCreate(BaseModel):
    """创建筛选预设请求模型"""
    name: str
    filters: dict


class FilterPresetUpdate(BaseModel):
    """更新筛选预设请求模型"""
    name: str
    filters: dict


# ====================== 任务模板接口 ======================
class TaskTemplateCreate(BaseModel):
    """创建任务模板请求模型"""
    name: str
    description: Optional[str] = None
    priority: str = "中"
    category: str = "默认"
    tags: Optional[List[str]] = None
    sub_tasks: Optional[List[dict]] = None
    notes: Optional[str] = ""


class TaskTemplateUpdate(BaseModel):
    """更新任务模板请求模型"""
    name: str
    description: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    sub_tasks: Optional[List[dict]] = None
    notes: Optional[str] = None


# ====================== 分类管理接口 ======================
class CategoryCreateRequest(BaseModel):
    """创建分类请求模型"""
    name: str
    color: str = "#3b82f6"
    icon: str = "📁"


class CategoryUpdateRequest(BaseModel):
    """更新分类请求模型"""
    name: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None


@app.get("/api/categories", summary="获取所有分类")
async def get_all_categories():
    """获取所有分类列表

    Returns:
        list: 分类列表
    """
    try:
        categories = db.get_categories()
        return [
            {
                "id": c[0],
                "name": c[1],
                "color": c[2],
                "icon": c[3],
                "created_at": c[4]
            }
            for c in categories
        ]
    except Exception as e:
        logger.error(f"获取分类列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取分类列表失败: {str(e)}")


@app.post("/api/categories", summary="创建分类")
async def create_category(request: CategoryCreateRequest):
    """创建新分类

    Args:
        request: 分类信息

    Returns:
        dict: 创建结果
    """
    try:
        category_id = db.add_category(request.name, request.color, request.icon)
        return {"success": True, "message": "分类创建成功", "category_id": category_id}
    except Exception as e:
        logger.error(f"创建分类失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建分类失败: {str(e)}")


@app.put("/api/categories/{category_id}", summary="更新分类")
async def update_category(category_id: int, request: CategoryUpdateRequest):
    """更新分类

    Args:
        category_id: 分类ID
        request: 更新信息

    Returns:
        dict: 更新结果
    """
    try:
        # 获取现有分类信息
        categories = db.get_categories()
        existing_category = None
        for c in categories:
            if c[0] == category_id:
                existing_category = c
                break
        
        if not existing_category:
            raise HTTPException(status_code=404, detail="分类不存在")
        
        # 使用现有值作为默认值
        name = request.name if request.name is not None else existing_category[1]
        color = request.color if request.color is not None else existing_category[2]
        icon = request.icon if request.icon is not None else existing_category[3]
        
        success = db.update_category(category_id, name, color, icon)
        if success:
            return {"success": True, "message": "分类更新成功"}
        else:
            raise HTTPException(status_code=404, detail="分类不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新分类失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新分类失败: {str(e)}")


@app.delete("/api/categories/{category_id}", summary="删除分类")
async def delete_category(category_id: int):
    """删除分类

    Args:
        category_id: 分类ID

    Returns:
        dict: 删除结果
    """
    try:
        success = db.delete_category(category_id)
        if success:
            return {"success": True, "message": "分类删除成功"}
        else:
            raise HTTPException(status_code=404, detail="分类不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除分类失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除分类失败: {str(e)}")


# ====================== 标签管理接口 ======================
class TagCreateRequest(BaseModel):
    """创建标签请求模型"""
    name: str
    color: str = "#5b7cff"


class TagUpdateRequest(BaseModel):
    """更新标签请求模型"""
    name: Optional[str] = None
    color: Optional[str] = None


@app.get("/api/tags", summary="获取所有标签")
async def get_all_tags():
    """获取所有标签列表

    Returns:
        list: 标签列表
    """
    try:
        tags = tag_service.get_all_tags()
        return {"success": True, "tags": tags}
    except Exception as e:
        logger.error(f"获取标签列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取标签列表失败: {str(e)}")


@app.get("/api/tags/statistics", summary="获取标签统计")
async def get_tag_statistics():
    """获取标签统计信息

    Returns:
        dict: 统计信息
    """
    try:
        stats = tag_service.get_tag_statistics()
        return {"success": True, "statistics": stats}
    except Exception as e:
        logger.error(f"获取标签统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取标签统计失败: {str(e)}")


@app.get("/api/tags/search", summary="搜索标签")
async def search_tags(q: str = Query(..., description="搜索关键词")):
    """搜索标签

    Args:
        q: 搜索关键词

    Returns:
        list: 匹配的标签列表
    """
    try:
        tags = tag_service.search_tags(q)
        return {"success": True, "tags": tags}
    except Exception as e:
        logger.error(f"搜索标签失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"搜索标签失败: {str(e)}")


@app.get("/api/tags/{tag_id}", summary="获取标签详情")
async def get_tag(tag_id: int):
    """获取指定标签详情

    Args:
        tag_id: 标签ID

    Returns:
        dict: 标签信息
    """
    try:
        tag = tag_service.get_tag_by_id(tag_id)
        if not tag:
            raise HTTPException(status_code=404, detail="标签不存在")
        return {"success": True, "tag": tag}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取标签失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取标签失败: {str(e)}")


@app.post("/api/tags", summary="创建标签")
async def create_tag(request: TagCreateRequest):
    """创建新标签

    Args:
        request: 标签信息

    Returns:
        dict: 创建结果
    """
    try:
        tag_id = tag_service.create_tag(request.name, request.color)
        return {"success": True, "message": "标签创建成功", "tag_id": tag_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建标签失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建标签失败: {str(e)}")


@app.put("/api/tags/{tag_id}", summary="更新标签")
async def update_tag(tag_id: int, request: TagUpdateRequest):
    """更新标签

    Args:
        tag_id: 标签ID
        request: 更新信息

    Returns:
        dict: 更新结果
    """
    try:
        success = tag_service.update_tag(tag_id, request.name, request.color)
        if success:
            return {"success": True, "message": "标签更新成功"}
        else:
            raise HTTPException(status_code=404, detail="标签不存在")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新标签失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新标签失败: {str(e)}")


@app.delete("/api/tags/{tag_id}", summary="删除标签")
async def delete_tag(tag_id: int):
    """删除标签

    Args:
        tag_id: 标签ID

    Returns:
        dict: 删除结果
    """
    try:
        success = tag_service.delete_tag(tag_id)
        if success:
            return {"success": True, "message": "标签删除成功"}
        else:
            raise HTTPException(status_code=404, detail="标签不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除标签失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除标签失败: {str(e)}")


# ====================== 筛选预设接口 ======================
@app.get("/api/filter-presets", summary="获取用户筛选预设")
async def get_filter_presets(current_user: dict = Depends(get_current_user_async)):
    """获取当前用户的筛选预设

    Returns:
        list: 筛选预设列表
    """
    try:
        presets = db.get_user_filter_presets(current_user["id"])
        import json
        return [
            {
                "id": p[0],
                "name": p[1],
                "filters": json.loads(p[2]),
                "created_at": p[3]
            }
            for p in presets
        ]
    except Exception as e:
        logger.error(f"获取筛选预设失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取筛选预设失败: {str(e)}")


@app.post("/api/filter-presets", summary="创建筛选预设")
async def create_filter_preset(preset: FilterPresetCreate, current_user: dict = Depends(get_current_user_async)):
    """创建新的筛选预设

    Args:
        preset: 筛选预设信息

    Returns:
        dict: 创建结果
    """
    try:
        preset_id = db.create_filter_preset(
            user_id=current_user["id"],
            name=preset.name,
            filters=preset.filters
        )
        return {"success": True, "message": "筛选预设创建成功", "preset_id": preset_id}
    except Exception as e:
        logger.error(f"创建筛选预设失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建筛选预设失败: {str(e)}")


@app.get("/api/filter-presets/{preset_id}", summary="获取筛选预设详情")
async def get_filter_preset(preset_id: int, current_user: dict = Depends(get_current_user_async)):
    """获取指定筛选预设详情

    Args:
        preset_id: 预设ID

    Returns:
        dict: 筛选预设详情
    """
    try:
        preset = db.get_filter_preset(preset_id)
        if not preset:
            raise HTTPException(status_code=404, detail="筛选预设不存在")
        
        # 验证权限
        if preset[1] != current_user["id"]:
            raise HTTPException(status_code=403, detail="无权访问此筛选预设")
        
        import json
        return {
            "id": preset[0],
            "name": preset[2],
            "filters": json.loads(preset[3]),
            "created_at": preset[4]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取筛选预设失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取筛选预设失败: {str(e)}")


@app.put("/api/filter-presets/{preset_id}", summary="更新筛选预设")
async def update_filter_preset(preset_id: int, preset: FilterPresetUpdate, current_user: dict = Depends(get_current_user_async)):
    """更新筛选预设

    Args:
        preset_id: 预设ID
        preset: 更新信息

    Returns:
        dict: 更新结果
    """
    try:
        # 验证权限
        existing_preset = db.get_filter_preset(preset_id)
        if not existing_preset:
            raise HTTPException(status_code=404, detail="筛选预设不存在")
        if existing_preset[1] != current_user["id"]:
            raise HTTPException(status_code=403, detail="无权修改此筛选预设")
        
        success = db.update_filter_preset(
            preset_id=preset_id,
            name=preset.name,
            filters=preset.filters
        )
        
        if success:
            return {"success": True, "message": "筛选预设更新成功"}
        else:
            raise HTTPException(status_code=404, detail="筛选预设不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新筛选预设失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新筛选预设失败: {str(e)}")


@app.delete("/api/filter-presets/{preset_id}", summary="删除筛选预设")
async def delete_filter_preset(preset_id: int, current_user: dict = Depends(get_current_user_async)):
    """删除筛选预设

    Args:
        preset_id: 预设ID

    Returns:
        dict: 删除结果
    """
    try:
        # 验证权限
        existing_preset = db.get_filter_preset(preset_id)
        if not existing_preset:
            raise HTTPException(status_code=404, detail="筛选预设不存在")
        if existing_preset[1] != current_user["id"]:
            raise HTTPException(status_code=403, detail="无权删除此筛选预设")
        
        success = db.delete_filter_preset(preset_id)
        if success:
            return {"success": True, "message": "筛选预设删除成功"}
        else:
            raise HTTPException(status_code=404, detail="筛选预设不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除筛选预设失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除筛选预设失败: {str(e)}")


# ====================== 任务模板接口 ======================
@app.get("/api/task-templates", summary="获取用户任务模板")
async def get_task_templates(current_user: dict = Depends(get_current_user_async)):
    """获取当前用户的任务模板

    Returns:
        list: 任务模板列表
    """
    try:
        templates = db.get_user_task_templates(current_user["id"])
        import json
        return [
            {
                "id": t[0],
                "name": t[1],
                "description": t[2],
                "priority": t[3],
                "category": t[4],
                "tags": json.loads(t[5]) if t[5] else [],
                "sub_tasks": json.loads(t[6]) if t[6] else [],
                "notes": t[7],
                "created_at": t[8]
            }
            for t in templates
        ]
    except Exception as e:
        logger.error(f"获取任务模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取任务模板失败: {str(e)}")


@app.post("/api/task-templates", summary="创建任务模板")
async def create_task_template(template: TaskTemplateCreate, current_user: dict = Depends(get_current_user_async)):
    """创建新的任务模板

    Args:
        template: 任务模板信息

    Returns:
        dict: 创建结果
    """
    try:
        template_id = db.create_task_template(
            user_id=current_user["id"],
            name=template.name,
            description=template.description,
            priority=template.priority,
            category=template.category,
            tags=template.tags,
            sub_tasks=template.sub_tasks,
            notes=template.notes
        )
        return {"success": True, "message": "任务模板创建成功", "template_id": template_id}
    except Exception as e:
        logger.error(f"创建任务模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建任务模板失败: {str(e)}")


@app.get("/api/task-templates/{template_id}", summary="获取任务模板详情")
async def get_task_template(template_id: int, current_user: dict = Depends(get_current_user_async)):
    """获取指定任务模板详情

    Args:
        template_id: 模板ID

    Returns:
        dict: 任务模板详情
    """
    try:
        template = db.get_task_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="任务模板不存在")
        
        # 验证权限
        if template[1] != current_user["id"]:
            raise HTTPException(status_code=403, detail="无权访问此任务模板")
        
        import json
        return {
            "id": template[0],
            "name": template[2],
            "description": template[3],
            "priority": template[4],
            "category": template[5],
            "tags": json.loads(template[6]) if template[6] else [],
            "sub_tasks": json.loads(template[7]) if template[7] else [],
            "notes": template[8],
            "created_at": template[9]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取任务模板失败: {str(e)}")


@app.put("/api/task-templates/{template_id}", summary="更新任务模板")
async def update_task_template(template_id: int, template: TaskTemplateUpdate, current_user: dict = Depends(get_current_user_async)):
    """更新任务模板

    Args:
        template_id: 模板ID
        template: 更新信息

    Returns:
        dict: 更新结果
    """
    try:
        # 验证权限
        existing_template = db.get_task_template(template_id)
        if not existing_template:
            raise HTTPException(status_code=404, detail="任务模板不存在")
        if existing_template[1] != current_user["id"]:
            raise HTTPException(status_code=403, detail="无权修改此任务模板")
        
        success = db.update_task_template(
            template_id=template_id,
            name=template.name,
            description=template.description,
            priority=template.priority,
            category=template.category,
            tags=template.tags,
            sub_tasks=template.sub_tasks,
            notes=template.notes
        )
        
        if success:
            return {"success": True, "message": "任务模板更新成功"}
        else:
            raise HTTPException(status_code=404, detail="任务模板不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新任务模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新任务模板失败: {str(e)}")


@app.delete("/api/task-templates/{template_id}", summary="删除任务模板")
async def delete_task_template(template_id: int, current_user: dict = Depends(get_current_user_async)):
    """删除任务模板

    Args:
        template_id: 模板ID

    Returns:
        dict: 删除结果
    """
    try:
        # 验证权限
        existing_template = db.get_task_template(template_id)
        if not existing_template:
            raise HTTPException(status_code=404, detail="任务模板不存在")
        if existing_template[1] != current_user["id"]:
            raise HTTPException(status_code=403, detail="无权删除此任务模板")
        
        success = db.delete_task_template(template_id)
        if success:
            return {"success": True, "message": "任务模板删除成功"}
        else:
            raise HTTPException(status_code=404, detail="任务模板不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除任务模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除任务模板失败: {str(e)}")


# ====================== 提醒接口 ======================
@app.get("/api/reminders/today", response_model=list)
async def get_today_reminders():
    """获取今日到期任务
    
    Returns:
        list: 今日到期任务列表
    """
    urgent_tasks = db.get_urgent_tasks()
    return [
        {"id": task[0], "task": task[1], "deadline": task[2], "priority": task[3], "category": task[4]}
        for task in urgent_tasks
    ]


@app.get("/api/reminders/overdue", response_model=list)
async def get_overdue_reminders():
    """获取已逾期任务
    
    Returns:
        list: 逾期任务列表
    """
    overdue_tasks = db.get_overdue_tasks()
    return [
        {"id": task[0], "task": task[1], "deadline": task[2], "priority": task[3], "category": task[4]}
        for task in overdue_tasks
    ]


# ====================== 统计接口 ======================
@app.get("/api/statistics", response_model=dict)
async def get_statistics(days: int = Query(7, ge=1, le=90)):
    """获取任务统计信息
    
    Args:
        days: 统计天数，默认7天
    
    Returns:
        dict: 统计信息
    """
    return db.get_statistics(days)


@app.get("/api/statistics/weekly", response_model=dict)
async def get_weekly_statistics():
    """获取本周统计"""
    stats = db.get_statistics(7)
    return {
        "total_created": sum(s["created"] for s in stats["recent_stats"]),
        "total_completed": sum(s["completed"] for s in stats["recent_stats"]),
        "daily_stats": stats["recent_stats"],
        "completion_rate": stats["completion_rate"]
    }


# ====================== 分类管理接口 ======================
@app.get("/api/categories", response_model=list)
async def get_categories():
    """获取所有分类
    
    Returns:
        list: 分类列表
    """
    categories = db.get_categories()
    return [
        {"id": cat[0], "name": cat[1], "color": cat[2], "icon": cat[3]}
        for cat in categories
    ]


@app.post("/api/categories", response_model=dict)
async def create_category(category: CategoryCreate):
    """创建新分类
    
    Args:
        category: 分类信息
    
    Returns:
        dict: 创建结果
    """
    try:
        cat_id = db.add_category(category.name, category.color, category.icon)
        return {"success": True, "id": cat_id}
    except Exception as e:
        return {"success": False, "error": str(e)}


class CategoryUpdate(BaseModel):
    """更新分类请求模型"""
    name: str
    color: str = "#3b82f6"
    icon: str = "📁"


@app.put("/api/categories/{category_id}", response_model=dict)
async def update_category(category_id: int, category: CategoryUpdate):
    """更新分类信息
    
    Args:
        category_id: 分类ID
        category: 分类信息
    
    Returns:
        dict: 更新结果
    """
    try:
        success = db.update_category(category_id, category.name, category.color, category.icon)
        return {"success": success}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.delete("/api/categories/{category_id}", response_model=dict)
async def delete_category(category_id: int):
    """删除分类
    
    Args:
        category_id: 分类ID
    
    Returns:
        dict: 删除结果
    """
    try:
        success = db.delete_category(category_id)
        return {"success": success}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ====================== 任务统计看板 ======================
@app.get("/api/dashboard", response_model=dict)
async def get_dashboard():
    """获取仪表盘数据

    Returns:
        dict: 仪表盘数据
    """
    stats = db.get_statistics(7)
    today_tasks = db.get_urgent_tasks()
    overdue_tasks = db.get_overdue_tasks()
    categories = db.get_categories()

    return {
        "stats": stats,
        "today_tasks": [
            {"id": t[0], "task": t[1], "deadline": t[2], "priority": t[3], "category": t[4]}
            for t in today_tasks
        ],
        "overdue_tasks": [
            {"id": t[0], "task": t[1], "deadline": t[2], "priority": t[3], "category": t[4]}
            for t in overdue_tasks
        ],
        "categories": [
            {"id": c[0], "name": c[1], "color": c[2], "icon": c[3]}
            for c in categories
        ]
    }


# ====================== 邮件配置接口 ======================
class EmailConfigRequest(BaseModel):
    """邮件配置请求模型"""
    smtp_host: str
    smtp_port: int = 587
    smtp_user: str
    smtp_password: str
    sender_email: Optional[str] = None
    receiver_email: str


@app.get("/api/email/config", summary="获取邮件配置")
async def get_email_config():
    """获取当前邮件配置

    Returns:
        dict: 邮件配置信息（不包含密码）
    """
    try:
        config = email_reminder_service.get_config()
        return {"success": True, "config": config}
    except Exception as e:
        logger.error(f"获取邮件配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取邮件配置失败: {str(e)}")


@app.post("/api/email/config", summary="保存邮件配置")
async def save_email_config(request: EmailConfigRequest):
    """保存邮件配置

    Args:
        request: 邮件配置信息

    Returns:
        dict: 保存结果
    """
    try:
        config = {
            "smtp_host": request.smtp_host,
            "smtp_port": request.smtp_port,
            "smtp_user": request.smtp_user,
            "smtp_password": request.smtp_password,
            "sender_email": request.sender_email or request.smtp_user,
            "receiver_email": request.receiver_email
        }
        success = email_reminder_service.save_config(config)
        if success:
            return {"success": True, "message": "邮件配置保存成功"}
        else:
            raise HTTPException(status_code=500, detail="邮件配置保存失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"保存邮件配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"保存邮件配置失败: {str(e)}")


@app.post("/api/email/test", summary="发送测试邮件")
async def send_test_email():
    """发送测试邮件验证配置是否正确

    Returns:
        dict: 测试结果
    """
    try:
        result = email_reminder_service.send_test_email()
        return result
    except Exception as e:
        logger.error(f"发送测试邮件失败: {str(e)}")
        return {"success": False, "message": f"发送测试邮件失败: {str(e)}"}


# ====================== 数据备份与恢复接口 ======================
class BackupRestoreRequest(BaseModel):
    """备份恢复请求模型"""
    clear_existing: bool = False


@app.get("/api/backup/list", summary="列出所有备份")
async def list_backups():
    """列出所有可用的备份文件

    Returns:
        list: 备份文件列表
    """
    try:
        backups = backup_service.list_backups()
        return {"success": True, "backups": backups}
    except Exception as e:
        logger.error(f"列出备份失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"列出备份失败: {str(e)}")


@app.post("/api/backup/create", summary="创建备份")
async def create_backup(backup_type: str = "manual"):
    """创建新的数据库备份

    Args:
        backup_type: 备份类型（manual手动/auto自动）

    Returns:
        dict: 备份结果
    """
    try:
        backup_path = backup_service.backup_to_file(backup_type)
        return {
            "success": True,
            "message": "备份创建成功",
            "backup_path": backup_path
        }
    except Exception as e:
        logger.error(f"创建备份失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建备份失败: {str(e)}")


@app.get("/api/backup/info/{filename}", summary="获取备份信息")
async def get_backup_info(filename: str):
    """获取指定备份文件的详细信息

    Args:
        filename: 备份文件名

    Returns:
        dict: 备份文件信息
    """
    try:
        info = backup_service.get_backup_info(filename)
        if info is None:
            raise HTTPException(status_code=404, detail="备份文件不存在")
        return {"success": True, "info": info}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取备份信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取备份信息失败: {str(e)}")


@app.post("/api/backup/restore/{filename}", summary="恢复备份")
async def restore_backup(filename: str, request: BackupRestoreRequest):
    """从指定备份文件恢复数据库

    Args:
        filename: 备份文件名
        request: 恢复请求参数

    Returns:
        dict: 恢复结果统计
    """
    try:
        stats = backup_service.restore_from_file(filename, request.clear_existing)
        return {
            "success": True,
            "message": "数据恢复成功",
            "stats": stats
        }
    except Exception as e:
        logger.error(f"恢复备份失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"恢复备份失败: {str(e)}")


@app.delete("/api/backup/{filename}", summary="删除备份")
async def delete_backup(filename: str):
    """删除指定的备份文件

    Args:
        filename: 备份文件名

    Returns:
        dict: 删除结果
    """
    try:
        success = backup_service.delete_backup(filename)
        if not success:
            raise HTTPException(status_code=404, detail="备份文件不存在")
        return {"success": True, "message": "备份文件已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除备份失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除备份失败: {str(e)}")


@app.get("/api/export/json", summary="导出数据为JSON")
async def export_json():
    """导出所有数据为JSON格式

    Returns:
        dict: 导出的数据
    """
    try:
        data = backup_service.export_to_json(include_chat=True)
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"导出JSON失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"导出JSON失败: {str(e)}")


@app.get("/api/export/csv", summary="导出任务为CSV")
async def export_csv():
    """导出任务为CSV格式

    Returns:
        dict: CSV文件路径
    """
    try:
        csv_path = backup_service.export_to_csv()
        return {"success": True, "csv_path": csv_path}
    except Exception as e:
        logger.error(f"导出CSV失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"导出CSV失败: {str(e)}")


# ====================== 启动服务器 ======================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
