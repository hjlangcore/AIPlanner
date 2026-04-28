"""
数据库操作模块

提供 SQLite 数据库的创建、任务数据的增删改查、用户管理、聊天会话等功能。
使用单例模式管理数据库连接，确保线程安全。
"""

import sqlite3
import datetime
import json
from typing import List, Tuple, Optional


class TodoDatabase:
    """数据库操作类
    
    负责 SQLite 数据库的初始化和任务数据的 CRUD 操作。
    数据库包含以下表：
    - tasks: 任务表
    - categories: 分类表
    - task_stats: 任务统计表
    - users: 用户表
    - chat_sessions: 聊天会话表
    - chat_messages: 聊天消息表
    - knowledge_base: 知识库表
    - filter_presets: 筛选预设表
    - task_templates: 任务模板表
    """
    
    def __init__(self, db_name: str = "todo_agent.db"):
        """初始化数据库连接
        
        Args:
            db_name: 数据库文件名
        """
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        # 先创建所有必要的表
        self._migrate_if_needed()  # 执行数据库迁移和创建所有表
        self.create_table()  # 创建任务表并迁移数据

    def _migrate_if_needed(self):
        """检查并执行数据库迁移（添加新字段）"""
        # 检查是否需要添加新字段
        self.cursor.execute("PRAGMA table_info(tasks)")
        columns = [col[1] for col in self.cursor.fetchall()]
        
        # 添加分类字段
        if "category" not in columns:
            try:
                self.cursor.execute("ALTER TABLE tasks ADD COLUMN category TEXT DEFAULT '默认'")
                self.conn.commit()
            except:
                pass
        
        # 添加标签字段
        if "tags" not in columns:
            try:
                self.cursor.execute("ALTER TABLE tasks ADD COLUMN tags TEXT DEFAULT '[]'")
                self.conn.commit()
            except:
                pass
        
        # 添加进度字段
        if "progress" not in columns:
            try:
                self.cursor.execute("ALTER TABLE tasks ADD COLUMN progress INTEGER DEFAULT 0")
                self.conn.commit()
            except:
                pass
        
        # 添加备注字段
        if "notes" not in columns:
            try:
                self.cursor.execute("ALTER TABLE tasks ADD COLUMN notes TEXT DEFAULT ''")
                self.conn.commit()
            except:
                pass
        
        # 添加更新时间字段
        if "update_time" not in columns:
            try:
                self.cursor.execute("ALTER TABLE tasks ADD COLUMN update_time TEXT")
                self.conn.commit()
            except:
                pass
        
        # 添加分类表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                color TEXT DEFAULT '#3b82f6',
                icon TEXT DEFAULT '📁',
                created_time TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        
        # 插入默认分类
        default_categories = [
            ('工作', '#ef4444', '💼'),
            ('学习', '#3b82f6', '📚'),
            ('生活', '#22c55e', '🏠'),
            ('健康', '#f59e0b', '💪'),
            ('默认', '#64748b', '📋')
        ]
        for name, color, icon in default_categories:
            try:
                self.cursor.execute(
                    "INSERT OR IGNORE INTO categories (name, color, icon) VALUES (?, ?, ?)",
                    (name, color, icon)
                )
            except:
                pass
        self.conn.commit()
        
        # 添加统计表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                created_count INTEGER DEFAULT 0,
                completed_count INTEGER DEFAULT 0,
                UNIQUE(date)
            )
        """)

        # 添加用户表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                email TEXT,
                role TEXT DEFAULT 'user',
                created_at TEXT DEFAULT (datetime('now','localtime'))
            )
        """)

        # 添加聊天会话表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                title TEXT,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                updated_at TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        # 添加聊天消息表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL, -- 'user' or 'assistant'
                content TEXT NOT NULL,
                intent TEXT,
                slots TEXT, -- JSON string
                created_at TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (session_id) REFERENCES chat_sessions (id)
            )
        """)

        # 添加知识库表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_base (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT,
                tags TEXT,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        
        # 添加筛选预设表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS filter_presets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                filters TEXT NOT NULL, -- JSON string
                created_at TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # 添加任务模板表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                priority TEXT DEFAULT '中',
                category TEXT DEFAULT '默认',
                tags TEXT DEFAULT '[]', -- JSON string
                sub_tasks TEXT DEFAULT '[]', -- JSON string
                notes TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        self.conn.commit()
        
        # 初始化一些知识库数据
        self.init_knowledge_base()
        # 创建性能优化索引
        self._create_indexes()

    def _create_indexes(self):
        """创建性能优化索引"""
        # 任务表索引
        index_definitions = [
            # 状态和优先级筛选索引
            ("idx_tasks_status_priority", "tasks", "status, priority"),
            # 分类筛选索引
            ("idx_tasks_category", "tasks", "category"),
            # 截止日期和状态索引（用于今日任务和逾期任务查询）
            ("idx_tasks_deadline_status", "tasks", "deadline, status"),
            # 创建时间索引（用于排序）
            ("idx_tasks_create_time", "tasks", "create_time DESC"),
            # 用户筛选预设索引
            ("idx_filter_presets_user", "filter_presets", "user_id"),
            # 用户任务模板索引
            ("idx_task_templates_user", "task_templates", "user_id"),
            # 聊天会话索引
            ("idx_chat_sessions_user", "chat_sessions", "user_id"),
            ("idx_chat_sessions_updated", "chat_sessions", "updated_at DESC"),
            # 聊天消息索引
            ("idx_chat_messages_session", "chat_messages", "session_id, created_at"),
            # 统计数据日期索引
            ("idx_task_stats_date", "task_stats", "date")
        ]
        
        for index_name, table_name, columns in index_definitions:
            try:
                # 使用 CREATE INDEX IF NOT EXISTS (SQLite 3.35.0+)
                self.cursor.execute(f'CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({columns})')
            except Exception as e:
                # 如果索引已存在或SQLite版本不支持，继续执行
                pass
        
        self.conn.commit()

    def init_knowledge_base(self):
        """初始化知识库数据"""
        self.cursor.execute("SELECT count(*) FROM knowledge_base")
        if self.cursor.fetchone()[0] == 0:
            knowledge_data = [
                ("如何创建任务", "您可以在'创建任务'页面输入自然语言，例如'明天下午3点提醒我开会'，AI会自动识别时间并创建任务。", "使用说明", "创建,自然语言"),
                ("任务优先级说明", "任务优先级分为高、中、低。高优先级任务会在仪表盘和列表中突出显示，建议优先处理。", "功能介绍", "优先级,管理"),
                ("智能助手功能", "智能助手可以回答您的日程疑问，帮助您拆解复杂任务，甚至提供时间管理建议。", "核心功能", "AI,助手"),
                ("关于 Smart Planner", "Smart Planner 是一款基于 AI Agent 技术的现代化待办事项与日程管理系统，旨在提升个人生产力。", "关于项目", "介绍,愿景")
            ]
            self.cursor.executemany(
                "INSERT INTO knowledge_base (title, content, category, tags) VALUES (?, ?, ?, ?)",
                knowledge_data
            )
            self.conn.commit()

    def create_table(self):
        """创建任务表（包含扩展字段）
        
        如果表不存在，则创建包含必要字段的任务表。
        """
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_task TEXT NOT NULL,        -- 原始自然语言任务
                sub_tasks TEXT NOT NULL,       -- 拆解后的子任务（JSON数组，支持完成状态）
                priority TEXT NOT NULL,        -- 优先级（高/中/低）
                deadline TEXT,                 -- 截止日期（YYYY-MM-DD）
                schedule TEXT,                 -- 生成的日程安排
                status TEXT DEFAULT '待执行',  -- 任务状态（待执行/进行中/已完成）
                category TEXT DEFAULT '默认',   -- 任务分类
                tags TEXT DEFAULT '[]',        -- 标签列表（JSON数组）
                progress INTEGER DEFAULT 0,     -- 完成进度（0-100）
                notes TEXT DEFAULT '',         -- 备注信息
                update_time TEXT,              -- 更新时间
                create_time TEXT DEFAULT (datetime('now','localtime'))  -- 创建时间
            )
        ''')
        self.conn.commit()
        
        # 迁移旧数据：将字符串数组转换为对象数组
        try:
            self.cursor.execute("SELECT id, sub_tasks FROM tasks")
            rows = self.cursor.fetchall()
            for row in rows:
                task_id, sub_tasks_str = row
                try:
                    sub_tasks = json.loads(sub_tasks_str)
                    # 如果是字符串数组，转换为对象数组
                    if sub_tasks and isinstance(sub_tasks[0], str):
                        new_sub_tasks = [{"text": st, "completed": False} for st in sub_tasks]
                        self.cursor.execute(
                            "UPDATE tasks SET sub_tasks = ? WHERE id = ?",
                            (json.dumps(new_sub_tasks, ensure_ascii=False), task_id)
                        )
                except:
                    continue
            self.conn.commit()
        except:
            pass

    def save_task(self, raw_task: str, sub_tasks: List[str], priority: str, 
                  deadline: str, schedule: str, category: str = "默认", 
                  tags: List[str] = None) -> int:
        """保存任务到数据库
        
        Args:
            raw_task: 原始自然语言任务
            sub_tasks: 拆解后的子任务列表
            priority: 任务优先级
            deadline: 截止日期
            schedule: 生成的日程安排
            category: 任务分类
            tags: 标签列表
        
        Returns:
            int: 保存的任务ID
        """
        tags = tags or []
        # 将子任务转换为对象数组格式
        sub_tasks_obj = [{"text": st, "completed": False} for st in sub_tasks]
        self.cursor.execute('''
            INSERT INTO tasks (raw_task, sub_tasks, priority, deadline, schedule, category, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (raw_task, json.dumps(sub_tasks_obj, ensure_ascii=False), priority, deadline, schedule, category, json.dumps(tags, ensure_ascii=False)))
        self.conn.commit()
        
        # 更新今日统计
        today = datetime.date.today().strftime("%Y-%m-%d")
        self.cursor.execute('''
            INSERT INTO task_stats (date, created_count) VALUES (?, 1)
            ON CONFLICT(date) DO UPDATE SET created_count = created_count + 1
        ''', (today,))
        self.conn.commit()
        
        return self.cursor.lastrowid

    def get_all_tasks(self, status: str = None, priority: str = None, 
                      category: str = None, keyword: str = None) -> List[Tuple]:
        """获取任务列表（支持筛选）
        
        Args:
            status: 按状态筛选（可选）
            priority: 按优先级筛选（可选）
            category: 按分类筛选（可选）
            keyword: 按关键词搜索（可选）
        
        Returns:
            List[Tuple]: 任务列表，按创建时间降序排序
        """
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        if priority:
            query += " AND priority = ?"
            params.append(priority)
        if category:
            query += " AND category = ?"
            params.append(category)
        if keyword:
            query += " AND (raw_task LIKE ? OR schedule LIKE ?)"
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        
        query += " ORDER BY create_time DESC"
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def get_task_by_id(self, task_id: int) -> Optional[Tuple]:
        """根据ID获取任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            Optional[Tuple]: 任务数据，如果不存在则返回None
        """
        self.cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
        return self.cursor.fetchone()

    def get_urgent_tasks(self) -> List[Tuple]:
        """获取今日到期的任务
        
        Returns:
            List[Tuple]: 今日到期的任务列表
        """
        today = datetime.date.today().strftime("%Y-%m-%d")
        self.cursor.execute('''
            SELECT id, raw_task, deadline, priority, category FROM tasks
            WHERE status != '已完成' AND deadline = ?
        ''', (today,))
        return self.cursor.fetchall()

    def get_overdue_tasks(self) -> List[Tuple]:
        """获取已过期的任务
        
        Returns:
            List[Tuple]: 已过期任务列表
        """
        today = datetime.date.today().strftime("%Y-%m-%d")
        self.cursor.execute('''
            SELECT id, raw_task, deadline, priority, category FROM tasks
            WHERE status != '已完成' AND deadline < ?
        ''', (today,))
        return self.cursor.fetchall()

    def update_task_status(self, task_id: int, status: str) -> bool:
        """更新任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态
        
        Returns:
            bool: 更新是否成功
        """
        # 如果标记为完成，更新进度为100
        progress = 100 if status == "已完成" else 0
        self.cursor.execute(
            "UPDATE tasks SET status = ?, progress = ?, update_time = datetime('now','localtime') WHERE id = ?",
            (status, progress, task_id)
        )
        self.conn.commit()
        
        # 更新今日统计
        if status == "已完成":
            today = datetime.date.today().strftime("%Y-%m-%d")
            self.cursor.execute('''
                INSERT INTO task_stats (date, completed_count) VALUES (?, 1)
                ON CONFLICT(date) DO UPDATE SET completed_count = completed_count + 1
            ''', (today,))
            self.conn.commit()
        
        return self.cursor.rowcount > 0

    def update_task_progress(self, task_id: int, progress: int, status: str = None) -> bool:
        """更新任务进度
        
        Args:
            task_id: 任务ID
            progress: 进度值（0-100）
            status: 可选的新状态
        
        Returns:
            bool: 更新是否成功
        """
        if status:
            self.cursor.execute(
                "UPDATE tasks SET progress = ?, status = ?, update_time = datetime('now','localtime') WHERE id = ?",
                (progress, status, task_id)
            )
        else:
            # 根据进度自动判断状态
            if progress >= 100:
                new_status = "已完成"
            elif progress > 0:
                new_status = "进行中"
            else:
                new_status = "待执行"
            self.cursor.execute(
                "UPDATE tasks SET progress = ?, status = ?, update_time = datetime('now','localtime') WHERE id = ?",
                (progress, new_status, task_id)
            )
        self.conn.commit()
        return self.cursor.rowcount > 0

    def update_task(self, task_id: int, raw_task: str = None, sub_tasks: List[str] = None,
                   priority: str = None, deadline: str = None, schedule: str = None,
                   category: str = None, tags: List[str] = None, notes: str = None) -> bool:
        """更新任务信息
        
        Args:
            task_id: 任务ID
            raw_task: 任务描述
            sub_tasks: 子任务列表
            priority: 优先级
            deadline: 截止日期
            schedule: 日程安排
            category: 分类
            tags: 标签
            notes: 备注
        
        Returns:
            bool: 更新是否成功
        """
        updates = []
        params = []
        
        if raw_task is not None:
            updates.append("raw_task = ?")
            params.append(raw_task)
        if sub_tasks is not None:
            updates.append("sub_tasks = ?")
            params.append(json.dumps(sub_tasks, ensure_ascii=False))
        if priority is not None:
            updates.append("priority = ?")
            params.append(priority)
        if deadline is not None:
            updates.append("deadline = ?")
            params.append(deadline)
        if schedule is not None:
            updates.append("schedule = ?")
            params.append(schedule)
        if category is not None:
            updates.append("category = ?")
            params.append(category)
        if tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(tags, ensure_ascii=False))
        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)
        
        if updates:
            updates.append("update_time = datetime('now','localtime')")
            params.append(task_id)
            self.cursor.execute(
                f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?",
                params
            )
            self.conn.commit()
        
        return self.cursor.rowcount > 0

    def update_sub_task_status(self, task_id: int, sub_task_index: int, completed: bool) -> bool:
        """更新子任务完成状态
        
        Args:
            task_id: 任务ID
            sub_task_index: 子任务索引
            completed: 是否完成
        
        Returns:
            bool: 更新是否成功
        """
        try:
            self.cursor.execute("SELECT sub_tasks FROM tasks WHERE id = ?", (task_id,))
            row = self.cursor.fetchone()
            if not row:
                return False
            
            sub_tasks = json.loads(row[0])
            if sub_task_index < 0 or sub_task_index >= len(sub_tasks):
                return False
            
            sub_tasks[sub_task_index]["completed"] = completed
            self.cursor.execute(
                "UPDATE tasks SET sub_tasks = ?, update_time = datetime('now','localtime') WHERE id = ?",
                (json.dumps(sub_tasks, ensure_ascii=False), task_id)
            )
            self.conn.commit()
            
            # 自动计算进度
            completed_count = sum(1 for st in sub_tasks if st.get("completed", False))
            progress = int((completed_count / len(sub_tasks)) * 100) if sub_tasks else 0
            self.cursor.execute(
                "UPDATE tasks SET progress = ? WHERE id = ?",
                (progress, task_id)
            )
            self.conn.commit()
            
            return True
        except Exception as e:
            print(f"更新子任务状态失败: {e}")
            return False

    def delete_task(self, task_id: int) -> bool:
        """删除任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            bool: 删除是否成功
        """
        self.cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def get_categories(self) -> List[Tuple]:
        """获取所有分类
        
        Returns:
            List[Tuple]: 分类列表
        """
        self.cursor.execute('SELECT * FROM categories ORDER BY id')
        return self.cursor.fetchall()

    def add_category(self, name: str, color: str = "#3b82f6", icon: str = "📁") -> int:
        """添加分类
        
        Args:
            name: 分类名称
            color: 分类颜色
            icon: 分类图标
        
        Returns:
            int: 分类ID
        """
        self.cursor.execute(
            "INSERT INTO categories (name, color, icon) VALUES (?, ?, ?)",
            (name, color, icon)
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def update_category(self, category_id: int, name: str, color: str, icon: str) -> bool:
        """更新分类信息
        
        Args:
            category_id: 分类ID
            name: 分类名称
            color: 分类颜色
            icon: 分类图标
        
        Returns:
            bool: 更新是否成功
        """
        self.cursor.execute(
            "UPDATE categories SET name = ?, color = ?, icon = ? WHERE id = ?",
            (name, color, icon, category_id)
        )
        self.conn.commit()
        return self.cursor.rowcount > 0

    def delete_category(self, category_id: int) -> bool:
        """删除分类
        
        Args:
            category_id: 分类ID
        
        Returns:
            bool: 删除是否成功
        """
        self.cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def get_statistics(self, days: int = 7) -> dict:
        """获取任务统计信息
        
        Args:
            days: 统计天数
        
        Returns:
            dict: 统计信息
        """
        # 总任务数
        self.cursor.execute("SELECT COUNT(*) FROM tasks")
        total = self.cursor.fetchone()[0]
        
        # 已完成任务数
        self.cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = '已完成'")
        completed = self.cursor.fetchone()[0]
        
        # 进行中任务数
        self.cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = '进行中'")
        in_progress = self.cursor.fetchone()[0]
        
        # 待执行任务数
        self.cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = '待执行'")
        pending = self.cursor.fetchone()[0]
        
        # 高优先级任务数
        self.cursor.execute("SELECT COUNT(*) FROM tasks WHERE priority = '高' AND status != '已完成'")
        urgent = self.cursor.fetchone()[0]
        
        # 今日到期任务数
        today = datetime.date.today().strftime("%Y-%m-%d")
        self.cursor.execute("SELECT COUNT(*) FROM tasks WHERE deadline = ? AND status != '已完成'", (today,))
        today_deadline = self.cursor.fetchone()[0]
        
        # 逾期任务数
        self.cursor.execute("SELECT COUNT(*) FROM tasks WHERE deadline < ? AND status != '已完成'", (today,))
        overdue = self.cursor.fetchone()[0]
        
        # 近期统计
        recent_stats = []
        for i in range(days):
            date = (datetime.date.today() - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            self.cursor.execute("SELECT created_count, completed_count FROM task_stats WHERE date = ?", (date,))
            row = self.cursor.fetchone()
            recent_stats.append({
                "date": date,
                "created": row[0] if row else 0,
                "completed": row[1] if row else 0
            })
        
        # 计算完成率
        completion_rate = (completed / total * 100) if total > 0 else 0
        
        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "pending": pending,
            "urgent": urgent,
            "today_deadline": today_deadline,
            "overdue": overdue,
            "completion_rate": round(completion_rate, 1),
            "recent_stats": list(reversed(recent_stats))
        }

    def get_tasks_by_date_range(self, start_date: str, end_date: str) -> List[Tuple]:
        """按日期范围获取任务
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            List[Tuple]: 任务列表
        """
        self.cursor.execute('''
            SELECT * FROM tasks 
            WHERE deadline BETWEEN ? AND ?
            ORDER BY deadline ASC
        ''', (start_date, end_date))
        return self.cursor.fetchall()

    def check_task_conflicts(self, task_id: int = None, deadline: str = None, status: str = None) -> List[Tuple]:
        """检查任务冲突
        
        Args:
            task_id: 任务ID（用于排除自身）
            deadline: 任务截止日期
            status: 任务状态（可选，用于筛选特定状态的任务）
        
        Returns:
            List[Tuple]: 冲突的任务列表
        """
        if not deadline:
            return []
        
        query = "SELECT * FROM tasks WHERE deadline = ?"
        params = [deadline]
        
        if task_id:
            query += " AND id != ?"
            params.append(task_id)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        else:
            query += " AND status != '已完成'"
        
        query += " ORDER BY create_time DESC"
        
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    # ====================== 筛选预设管理 ======================
    def create_filter_preset(self, user_id: int, name: str, filters: dict) -> int:
        """创建筛选预设
        
        Args:
            user_id: 用户ID
            name: 预设名称
            filters: 筛选条件（JSON格式）
        
        Returns:
            int: 预设ID
        """
        import json
        filters_json = json.dumps(filters, ensure_ascii=False)
        self.cursor.execute(
            "INSERT INTO filter_presets (user_id, name, filters) VALUES (?, ?, ?)",
            (user_id, name, filters_json)
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def get_user_filter_presets(self, user_id: int) -> List[Tuple]:
        """获取用户的筛选预设
        
        Args:
            user_id: 用户ID
        
        Returns:
            List[Tuple]: 预设列表
        """
        self.cursor.execute(
            "SELECT id, name, filters, created_at FROM filter_presets WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
        return self.cursor.fetchall()

    def get_filter_preset(self, preset_id: int) -> Optional[Tuple]:
        """获取指定预设
        
        Args:
            preset_id: 预设ID
        
        Returns:
            Optional[Tuple]: 预设数据
        """
        self.cursor.execute(
            "SELECT id, user_id, name, filters, created_at FROM filter_presets WHERE id = ?",
            (preset_id,)
        )
        return self.cursor.fetchone()

    def update_filter_preset(self, preset_id: int, name: str, filters: dict) -> bool:
        """更新筛选预设
        
        Args:
            preset_id: 预设ID
            name: 新名称
            filters: 新筛选条件
        
        Returns:
            bool: 更新是否成功
        """
        import json
        filters_json = json.dumps(filters, ensure_ascii=False)
        self.cursor.execute(
            "UPDATE filter_presets SET name = ?, filters = ? WHERE id = ?",
            (name, filters_json, preset_id)
        )
        self.conn.commit()
        return self.cursor.rowcount > 0

    def delete_filter_preset(self, preset_id: int) -> bool:
        """删除筛选预设
        
        Args:
            preset_id: 预设ID
        
        Returns:
            bool: 删除是否成功
        """
        self.cursor.execute("DELETE FROM filter_presets WHERE id = ?", (preset_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0

    # ====================== 任务模板管理 ======================
    def create_task_template(self, user_id: int, name: str, description: str = None, 
                          priority: str = '中', category: str = '默认', 
                          tags: List[str] = None, sub_tasks: List[dict] = None, 
                          notes: str = '') -> int:
        """创建任务模板
        
        Args:
            user_id: 用户ID
            name: 模板名称
            description: 模板描述
            priority: 优先级
            category: 分类
            tags: 标签列表
            sub_tasks: 子任务列表
            notes: 备注
        
        Returns:
            int: 模板ID
        """
        import json
        tags_json = json.dumps(tags or [], ensure_ascii=False)
        sub_tasks_json = json.dumps(sub_tasks or [], ensure_ascii=False)
        
        self.cursor.execute(
            """
            INSERT INTO task_templates (user_id, name, description, priority, category, tags, sub_tasks, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, name, description, priority, category, tags_json, sub_tasks_json, notes)
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def get_user_task_templates(self, user_id: int) -> List[Tuple]:
        """获取用户的任务模板
        
        Args:
            user_id: 用户ID
        
        Returns:
            List[Tuple]: 模板列表
        """
        self.cursor.execute(
            "SELECT id, name, description, priority, category, tags, sub_tasks, notes, created_at FROM task_templates WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
        return self.cursor.fetchall()

    def get_task_template(self, template_id: int) -> Optional[Tuple]:
        """获取指定任务模板
        
        Args:
            template_id: 模板ID
        
        Returns:
            Optional[Tuple]: 模板数据
        """
        self.cursor.execute(
            "SELECT id, user_id, name, description, priority, category, tags, sub_tasks, notes, created_at FROM task_templates WHERE id = ?",
            (template_id,)
        )
        return self.cursor.fetchone()

    def update_task_template(self, template_id: int, name: str, description: str = None, 
                          priority: str = None, category: str = None, 
                          tags: List[str] = None, sub_tasks: List[dict] = None, 
                          notes: str = None) -> bool:
        """更新任务模板
        
        Args:
            template_id: 模板ID
            name: 模板名称
            description: 模板描述
            priority: 优先级
            category: 分类
            tags: 标签列表
            sub_tasks: 子任务列表
            notes: 备注
        
        Returns:
            bool: 更新是否成功
        """
        import json
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if priority is not None:
            updates.append("priority = ?")
            params.append(priority)
        if category is not None:
            updates.append("category = ?")
            params.append(category)
        if tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(tags, ensure_ascii=False))
        if sub_tasks is not None:
            updates.append("sub_tasks = ?")
            params.append(json.dumps(sub_tasks, ensure_ascii=False))
        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)
        
        if not updates:
            return False
        
        params.append(template_id)
        self.cursor.execute(
            f"UPDATE task_templates SET {', '.join(updates)} WHERE id = ?",
            params
        )
        self.conn.commit()
        return self.cursor.rowcount > 0

    def delete_task_template(self, template_id: int) -> bool:
        """删除任务模板
        
        Args:
            template_id: 模板ID
        
        Returns:
            bool: 删除是否成功
        """
        self.cursor.execute("DELETE FROM task_templates WHERE id = ?", (template_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0

    # ====================== 用户管理 ======================
    def get_user_by_username(self, username: str) -> Optional[Tuple]:
        self.cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        return self.cursor.fetchone()

    def create_user(self, username: str, password_hash: str, full_name: str = None, email: str = None) -> int:
        self.cursor.execute(
            "INSERT INTO users (username, password_hash, full_name, email) VALUES (?, ?, ?, ?)",
            (username, password_hash, full_name, email)
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def get_all_users(self) -> List[Tuple]:
        """获取所有用户
        
        Returns:
            List[Tuple]: 用户列表
        """
        self.cursor.execute("SELECT id, username, full_name, email, role, created_at FROM users ORDER BY id")
        return self.cursor.fetchall()

    def update_user_role(self, user_id: int, role: str) -> bool:
        """更新用户角色
        
        Args:
            user_id: 用户ID
            role: 新角色
        
        Returns:
            bool: 更新是否成功
        """
        self.cursor.execute(
            "UPDATE users SET role = ? WHERE id = ?",
            (role, user_id)
        )
        self.conn.commit()
        return self.cursor.rowcount > 0

    # ====================== 聊天会话管理 ======================
    def create_chat_session(self, session_id: str, user_id: int, title: str = "新对话") -> str:
        self.cursor.execute(
            "INSERT INTO chat_sessions (id, user_id, title) VALUES (?, ?, ?)",
            (session_id, user_id, title)
        )
        self.conn.commit()
        return session_id

    def get_user_sessions(self, user_id: int) -> List[Tuple]:
        self.cursor.execute(
            "SELECT * FROM chat_sessions WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,)
        )
        return self.cursor.fetchall()

    def update_session_time(self, session_id: str):
        self.cursor.execute(
            "UPDATE chat_sessions SET updated_at = datetime('now','localtime') WHERE id = ?",
            (session_id,)
        )
        self.conn.commit()

    def delete_chat_session(self, session_id: str):
        self.cursor.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
        self.cursor.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
        self.conn.commit()

    # ====================== 聊天消息管理 ======================
    def add_chat_message(self, session_id: str, role: str, content: str, intent: str = None, slots: dict = None):
        slots_json = json.dumps(slots, ensure_ascii=False) if slots else None
        self.cursor.execute(
            "INSERT INTO chat_messages (session_id, role, content, intent, slots) VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, intent, slots_json)
        )
        self.conn.commit()
        self.update_session_time(session_id)

    def get_session_messages(self, session_id: str, limit: int = 50) -> List[Tuple]:
        self.cursor.execute(
            "SELECT role, content, intent, slots, created_at FROM chat_messages WHERE session_id = ? ORDER BY created_at ASC LIMIT ?",
            (session_id, limit)
        )
        return self.cursor.fetchall()

    # ====================== 知识库管理 ======================
    def search_knowledge(self, query: str, limit: int = 3) -> List[Tuple]:
        # 简单实现：使用 LIKE 进行内容搜索。后续可升级为向量检索。
        self.cursor.execute(
            "SELECT title, content FROM knowledge_base WHERE content LIKE ? OR title LIKE ? LIMIT ?",
            (f"%{query}%", f"%{query}%", limit)
        )
        return self.cursor.fetchall()

    def add_knowledge(self, title: str, content: str, category: str = None, tags: List[str] = None):
        tags_str = ",".join(tags) if tags else ""
        self.cursor.execute(
            "INSERT INTO knowledge_base (title, content, category, tags) VALUES (?, ?, ?, ?)",
            (title, content, category, tags_str)
        )
        self.conn.commit()


# 全局数据库实例
db = TodoDatabase()
