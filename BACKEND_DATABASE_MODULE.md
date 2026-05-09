# 后端数据库操作处理模块

## 文件位置: backend/db/db_handler.py

```python
"""
数据库处理模块

提供 SQLite3 的数据库操作接口，包括：
- 用户管理
- 任务管理
- 数据库初始化和迁移
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import threading

class DatabaseHandler:
    def __init__(self, db_path: str = "backend/todo_agent.db"):
        self.db_path = db_path
        self.local = threading.local()
    
    def get_connection(self):
        """获取数据库连接 (线程本地存储)"""
        if not hasattr(self.local, 'connection') or self.local.connection is None:
            self.local.connection = sqlite3.connect(self.db_path)
            self.local.connection.row_factory = sqlite3.Row
        return self.local.connection
    
    def close(self):
        """关闭数据库连接"""
        if hasattr(self.local, 'connection') and self.local.connection:
            self.local.connection.close()
            self.local.connection = None
    
    # ============================================
    # 数据库初始化
    # ============================================
    
    def initialize_db(self):
        """初始化数据库，创建所有表"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 用户表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    full_name TEXT,
                    email TEXT,
                    role TEXT DEFAULT 'user',
                    created_at TEXT
                )
            """)
            
            # 任务表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    raw_task TEXT NOT NULL,
                    sub_tasks TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    deadline TEXT,
                    schedule TEXT,
                    status TEXT DEFAULT '待执行',
                    category TEXT DEFAULT '默认',
                    tags TEXT DEFAULT '[]',
                    progress INTEGER DEFAULT 0,
                    notes TEXT DEFAULT '',
                    update_time TEXT,
                    create_time TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            # 分类表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    color TEXT DEFAULT '#3b82f6',
                    icon TEXT DEFAULT '📁',
                    created_time TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            # 聊天会话表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    title TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            # 聊天消息表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    intent TEXT,
                    slots TEXT,
                    created_at TEXT,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions (id)
                )
            """)
            
            # 知识库表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_base (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    category TEXT,
                    tags TEXT,
                    created_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status_priority ON tasks(status, priority)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_category ON tasks(category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_deadline_status ON tasks(deadline, status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_create_time ON tasks(create_time DESC)")
            
            conn.commit()
            print("✓ 数据库初始化成功")
            
        except Exception as e:
            print(f"✗ 数据库初始化失败: {e}")
            conn.rollback()
            raise
    
    # ============================================
    # 用户相关操作
    # ============================================
    
    def create_user(self, username: str, password_hash: str, full_name: str = "", email: str = "") -> Dict[str, Any]:
        """创建用户"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO users (username, password_hash, full_name, email, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (username, password_hash, full_name, email, datetime.now().isoformat()))
            
            conn.commit()
            user_id = cursor.lastrowid
            
            return {
                "id": user_id,
                "username": username,
                "full_name": full_name,
                "email": email
            }
        except sqlite3.IntegrityError:
            raise Exception("Username already exists")
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """通过用户名获取用户"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """通过ID获取用户"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, username, full_name, email, role FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    # ============================================
    # 任务相关操作
    # ============================================
    
    def create_task(self, user_id: int, raw_task: str, sub_tasks: List[str], 
                   priority: str, deadline: str = None, category: str = "默认") -> Dict[str, Any]:
        """创建任务"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO tasks (user_id, raw_task, sub_tasks, priority, deadline, category, create_time, update_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, raw_task, json.dumps(sub_tasks), priority, deadline, category, now, now))
            
            conn.commit()
            task_id = cursor.lastrowid
            
            return {
                "id": task_id,
                "user_id": user_id,
                "raw_task": raw_task,
                "sub_tasks": sub_tasks,
                "priority": priority,
                "deadline": deadline,
                "category": category,
                "status": "待执行",
                "progress": 0,
                "create_time": now
            }
        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to create task: {str(e)}")
    
    def get_tasks(self, user_id: int = None, status: str = None, 
                 priority: str = None, category: str = None) -> List[Dict[str, Any]]:
        """获取任务列表"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        if priority:
            query += " AND priority = ?"
            params.append(priority)
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        query += " ORDER BY create_time DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        tasks = []
        for row in rows:
            task = dict(row)
            task['sub_tasks'] = json.loads(task['sub_tasks']) if task['sub_tasks'] else []
            task['tags'] = json.loads(task['tags']) if task['tags'] else []
            tasks.append(task)
        
        return tasks
    
    def get_task_by_id(self, task_id: int) -> Optional[Dict[str, Any]]:
        """通过ID获取任务"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        
        if row:
            task = dict(row)
            task['sub_tasks'] = json.loads(task['sub_tasks']) if task['sub_tasks'] else []
            task['tags'] = json.loads(task['tags']) if task['tags'] else []
            return task
        return None
    
    def update_task(self, task_id: int, updates: Dict[str, Any]) -> bool:
        """更新任务"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 构建 SET 子句
            set_clauses = []
            params = []
            
            for key, value in updates.items():
                if key in ['sub_tasks', 'tags']:
                    value = json.dumps(value) if isinstance(value, list) else value
                
                set_clauses.append(f"{key} = ?")
                params.append(value)
            
            set_clauses.append("update_time = ?")
            params.append(datetime.now().isoformat())
            params.append(task_id)
            
            query = f"UPDATE tasks SET {', '.join(set_clauses)} WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()
            
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to update task: {str(e)}")
    
    def delete_task(self, task_id: int) -> bool:
        """删除任务"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to delete task: {str(e)}")
    
    # ============================================
    # 任务统计
    # ============================================
    
    def get_task_statistics(self, user_id: int = None) -> Dict[str, Any]:
        """获取任务统计"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = "SELECT status, COUNT(*) as count FROM tasks WHERE 1=1"
        params = []
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        query += " GROUP BY status"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        stats = {
            "总任务": 0,
            "待执行": 0,
            "进行中": 0,
            "已完成": 0
        }
        
        for row in rows:
            status, count = dict(row)['status'], dict(row)['count']
            stats[status] = count
            stats["总任务"] += count
        
        return stats
    
    def get_tasks_due_today(self, user_id: int = None) -> List[Dict[str, Any]]:
        """获取今日到期任务"""
        from datetime import date
        
        today = date.today().isoformat()
        
        query = "SELECT * FROM tasks WHERE deadline = ? AND status != '已完成'"
        params = [today]
        
        if user_id:
            query = "SELECT * FROM tasks WHERE user_id = ? AND deadline = ? AND status != '已完成'"
            params = [user_id, today]
        
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        tasks = []
        for row in rows:
            task = dict(row)
            task['sub_tasks'] = json.loads(task['sub_tasks']) if task['sub_tasks'] else []
            tasks.append(task)
        
        return tasks
```
