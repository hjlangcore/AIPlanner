"""
认证服务模块

处理用户注册、登录、JWT 签发与验证。
"""
import os
import datetime
from typing import Optional, List, Callable
import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from functools import wraps
from ..db.db_handler import db

# 配置加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "smart-planner-secret-key-2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 天

security = HTTPBearer()

# 角色定义
class Role:
    ADMIN = "admin"
    USER = "user"

# 角色权限映射
ROLE_PERMISSIONS = {
    Role.ADMIN: ["manage_users", "manage_all_tasks", "manage_system"],
    Role.USER: ["manage_own_tasks", "manage_own_templates", "manage_own_filters"]
}

def get_password_hash(password: str) -> str:
    # bcrypt has a maximum password length of 72 bytes
    # Truncate password to 72 bytes to avoid error
    password = password[:72]
    # Use bcrypt directly to hash the password
    import bcrypt
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Use bcrypt directly to verify the password
    # Truncate password to 72 bytes to match the hashing process
    import bcrypt
    plain_password = plain_password[:72]
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user_async(auth: HTTPAuthorizationCredentials = Security(security)):
    """异步获取当前用户信息（用于FastAPI异步依赖注入）

    Args:
        auth: HTTP认证凭证（Bearer Token）

    Returns:
        dict: 用户信息（id、username、role）

    Raises:
        HTTPException: 当令牌无效或用户不存在时抛出401异常
    """
    try:
        payload = jwt.decode(auth.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        if username is None:
            raise HTTPException(status_code=401, detail="无效的凭证")

        user = db.get_user_by_username(username)
        if user is None:
            raise HTTPException(status_code=401, detail="用户不存在")

        return {
            "id": user[0],
            "username": user[1],
            "full_name": user[3],
            "email": user[4],
            "role": user[5]
        }
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="凭证已过期或无效")


def get_current_user(auth: HTTPAuthorizationCredentials = Security(security)):
    """获取当前用户信息（同步版本，用于非异步场景）

    Args:
        auth: HTTP认证凭证（Bearer Token）

    Returns:
        dict: 用户信息（id、username、role）

    Raises:
        HTTPException: 当令牌无效或用户不存在时抛出401异常
    """
    try:
        payload = jwt.decode(auth.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        if username is None:
            raise HTTPException(status_code=401, detail="无效的凭证")

        user = db.get_user_by_username(username)
        if user is None:
            raise HTTPException(status_code=401, detail="用户不存在")

        return {
            "id": user[0],
            "username": user[1],
            "full_name": user[3],
            "email": user[4],
            "role": user[5]
        }
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="凭证已过期或无效")


def require_role(required_role: str):
    """角色权限检查装饰器

    Args:
        required_role: 要求的角色

    Returns:
        Callable: 装饰器函数
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(status_code=401, detail="未认证")
            
            user_role = current_user.get("role", Role.USER)
            if user_role != required_role and user_role != Role.ADMIN:
                raise HTTPException(status_code=403, detail="权限不足")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_permission(required_permission: str):
    """权限检查装饰器

    Args:
        required_permission: 要求的权限

    Returns:
        Callable: 装饰器函数
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(status_code=401, detail="未认证")
            
            user_role = current_user.get("role", Role.USER)
            user_permissions = ROLE_PERMISSIONS.get(user_role, [])
            
            if required_permission not in user_permissions and user_role != Role.ADMIN:
                raise HTTPException(status_code=403, detail="权限不足")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
