"""
数据备份与恢复服务模块

提供数据库的备份、导出、导入和恢复功能，支持定时自动备份。
"""
import os
import json
import shutil
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
from zipfile import ZipFile
import logging

logger = logging.getLogger(__name__)

class BackupService:
    """数据备份与恢复服务类

    负责数据库的备份、导出、导入和恢复操作。
    """

    def __init__(self, db_path: str = "todo_agent.db", backup_dir: str = "backups"):
        """初始化备份服务

        Args:
            db_path: 数据库文件路径
            backup_dir: 备份文件存储目录
        """
        self.db_path = db_path
        self.backup_dir = backup_dir
        self._ensure_backup_dir()

    def _ensure_backup_dir(self):
        """确保备份目录存在"""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
            logger.info(f"创建备份目录: {self.backup_dir}")

    def _get_backup_filename(self, backup_type: str = "manual") -> str:
        """生成备份文件名

        Args:
            backup_type: 备份类型（manual手动/auto自动）

        Returns:
            str: 备份文件名
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"backup_{backup_type}_{timestamp}"

    def export_to_json(self, include_chat: bool = True) -> Dict[str, Any]:
        """导出所有数据为JSON格式

        Args:
            include_chat: 是否包含聊天记录

        Returns:
            dict: 导出的数据
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            data = {
                "export_time": datetime.now().isoformat(),
                "version": "2.0.0",
                "tasks": [],
                "categories": [],
                "knowledge_base": [],
                "chat_sessions": [],
                "chat_messages": []
            }

            cursor.execute("SELECT * FROM tasks ORDER BY create_time DESC")
            for row in cursor.fetchall():
                data["tasks"].append(dict(row))

            cursor.execute("SELECT * FROM categories ORDER BY id")
            for row in cursor.fetchall():
                data["categories"].append(dict(row))

            cursor.execute("SELECT * FROM knowledge_base ORDER BY id")
            for row in cursor.fetchall():
                data["knowledge_base"].append(dict(row))

            if include_chat:
                cursor.execute("SELECT * FROM chat_sessions ORDER BY created_at DESC")
                for row in cursor.fetchall():
                    data["chat_sessions"].append(dict(row))

                cursor.execute("SELECT * FROM chat_messages ORDER BY created_at ASC")
                for row in cursor.fetchall():
                    data["chat_messages"].append(dict(row))

            logger.info(f"数据导出成功，共导出 {len(data['tasks'])} 个任务")
            return data

        except Exception as e:
            logger.error(f"数据导出失败: {str(e)}")
            raise
        finally:
            conn.close()

    def export_to_csv(self) -> str:
        """导出任务为CSV格式

        Returns:
            str: CSV文件路径
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, raw_task, priority, deadline, schedule, status,
                       category, tags, progress, notes, create_time, update_time
                FROM tasks ORDER BY create_time DESC
            """)

            csv_path = os.path.join(self.backup_dir, f"tasks_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

            with open(csv_path, 'w', encoding='utf-8-sig') as f:
                headers = ['ID', '任务名称', '优先级', '截止日期', '日程安排', '状态',
                          '分类', '标签', '进度', '备注', '创建时间', '更新时间']
                f.write(','.join(headers) + '\n')

                for row in cursor.fetchall():
                    values = [
                        str(row['id']),
                        f'"{row["raw_task"]}"',
                        row['priority'] or '',
                        row['deadline'] or '',
                        f'"{row["schedule"]}"' if row['schedule'] else '',
                        row['status'] or '',
                        row['category'] or '',
                        row['tags'] or '[]',
                        str(row['progress'] or 0),
                        f'"{row["notes"]}"' if row['notes'] else '',
                        row['create_time'] or '',
                        row['update_time'] or ''
                    ]
                    f.write(','.join(values) + '\n')

            logger.info(f"CSV导出成功: {csv_path}")
            return csv_path

        except Exception as e:
            logger.error(f"CSV导出失败: {str(e)}")
            raise
        finally:
            conn.close()

    def backup_to_file(self, backup_type: str = "manual") -> str:
        """创建数据库备份文件

        Args:
            backup_type: 备份类型

        Returns:
            str: 备份文件路径
        """
        try:
            filename = self._get_backup_filename(backup_type)
            backup_path = os.path.join(self.backup_dir, f"{filename}.zip")

            data = self.export_to_json(include_chat=True)

            with ZipFile(backup_path, 'w') as zipf:
                zipf.writestr("data.json", json.dumps(data, ensure_ascii=False, indent=2))

            logger.info(f"数据库备份成功: {backup_path}")
            return backup_path

        except Exception as e:
            logger.error(f"数据库备份失败: {str(e)}")
            raise

    def restore_from_json(self, data: Dict[str, Any], clear_existing: bool = False) -> Dict[str, int]:
        """从JSON数据恢复数据库

        Args:
            data: JSON数据
            clear_existing: 是否清除现有数据

        Returns:
            dict: 恢复统计信息
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            stats = {
                "tasks_restored": 0,
                "categories_restored": 0,
                "knowledge_restored": 0,
                "chat_sessions_restored": 0,
                "chat_messages_restored": 0
            }

            if clear_existing:
                cursor.execute("DELETE FROM chat_messages")
                cursor.execute("DELETE FROM chat_sessions")
                cursor.execute("DELETE FROM tasks")
                cursor.execute("DELETE FROM categories")
                cursor.execute("DELETE FROM knowledge_base")
                conn.commit()
                logger.info("已清除现有数据")

            if "categories" in data:
                for cat in data["categories"]:
                    try:
                        cursor.execute(
                            "INSERT OR IGNORE INTO categories (name, color, icon) VALUES (?, ?, ?)",
                            (cat.get("name"), cat.get("color", "#3b82f6"), cat.get("icon", "📁"))
                        )
                        stats["categories_restored"] += 1
                    except:
                        pass

            if "tasks" in data:
                for task in data["tasks"]:
                    try:
                        cursor.execute("""
                            INSERT INTO tasks (raw_task, sub_tasks, priority, deadline, schedule,
                                             status, category, tags, progress, notes, create_time, update_time)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            task.get("raw_task"),
                            task.get("sub_tasks", "[]"),
                            task.get("priority", "中"),
                            task.get("deadline"),
                            task.get("schedule"),
                            task.get("status", "待执行"),
                            task.get("category", "默认"),
                            task.get("tags", "[]"),
                            task.get("progress", 0),
                            task.get("notes", ""),
                            task.get("create_time"),
                            task.get("update_time")
                        ))
                        stats["tasks_restored"] += 1
                    except:
                        pass

            if "knowledge_base" in data:
                for kb in data["knowledge_base"]:
                    try:
                        cursor.execute("""
                            INSERT OR IGNORE INTO knowledge_base (title, content, category, tags)
                            VALUES (?, ?, ?, ?)
                        """, (
                            kb.get("title"),
                            kb.get("content"),
                            kb.get("category"),
                            kb.get("tags", "")
                        ))
                        stats["knowledge_restored"] += 1
                    except:
                        pass

            if "chat_sessions" in data:
                for session in data["chat_sessions"]:
                    try:
                        cursor.execute("""
                            INSERT OR IGNORE INTO chat_sessions (id, user_id, title, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            session.get("id"),
                            session.get("user_id", 1),
                            session.get("title", "新对话"),
                            session.get("created_at"),
                            session.get("updated_at")
                        ))
                        stats["chat_sessions_restored"] += 1
                    except:
                        pass

            if "chat_messages" in data:
                for msg in data["chat_messages"]:
                    try:
                        cursor.execute("""
                            INSERT INTO chat_messages (session_id, role, content, intent, slots, created_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            msg.get("session_id"),
                            msg.get("role"),
                            msg.get("content"),
                            msg.get("intent"),
                            msg.get("slots"),
                            msg.get("created_at")
                        ))
                        stats["chat_messages_restored"] += 1
                    except:
                        pass

            conn.commit()
            logger.info(f"数据恢复成功: {stats}")
            return stats

        except Exception as e:
            conn.rollback()
            logger.error(f"数据恢复失败: {str(e)}")
            raise
        finally:
            conn.close()

    def restore_from_file(self, backup_path: str, clear_existing: bool = False) -> Dict[str, int]:
        """从备份文件恢复数据库

        Args:
            backup_path: 备份文件路径
            clear_existing: 是否清除现有数据

        Returns:
            dict: 恢复统计信息
        """
        try:
            with ZipFile(backup_path, 'r') as zipf:
                with zipf.open("data.json") as f:
                    data = json.load(f)

            return self.restore_from_json(data, clear_existing)

        except Exception as e:
            logger.error(f"从备份文件恢复失败: {str(e)}")
            raise

    def list_backups(self) -> List[Dict[str, Any]]:
        """列出所有备份文件

        Returns:
            list: 备份文件列表
        """
        backups = []
        try:
            if os.path.exists(self.backup_dir):
                for filename in os.listdir(self.backup_dir):
                    if filename.endswith('.zip'):
                        filepath = os.path.join(self.backup_dir, filename)
                        stat = os.stat(filepath)
                        backups.append({
                            "filename": filename,
                            "path": filepath,
                            "size": stat.st_size,
                            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                        })

            backups.sort(key=lambda x: x["modified_at"], reverse=True)
            return backups

        except Exception as e:
            logger.error(f"列出备份文件失败: {str(e)}")
            return []

    def delete_backup(self, filename: str) -> bool:
        """删除备份文件

        Args:
            filename: 备份文件名

        Returns:
            bool: 是否删除成功
        """
        try:
            filepath = os.path.join(self.backup_dir, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"删除备份文件: {filepath}")
                return True
            return False

        except Exception as e:
            logger.error(f"删除备份文件失败: {str(e)}")
            return False

    def get_backup_info(self, filename: str) -> Optional[Dict[str, Any]]:
        """获取备份文件信息

        Args:
            filename: 备份文件名

        Returns:
            dict: 备份文件信息
        """
        try:
            filepath = os.path.join(self.backup_dir, filename)
            if not os.path.exists(filepath):
                return None

            stat = os.stat(filepath)
            with ZipFile(filepath, 'r') as zipf:
                with zipf.open("data.json") as f:
                    data = json.load(f)

            return {
                "filename": filename,
                "path": filepath,
                "size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "data_info": {
                    "tasks_count": len(data.get("tasks", [])),
                    "categories_count": len(data.get("categories", [])),
                    "knowledge_count": len(data.get("knowledge_base", [])),
                    "chat_sessions_count": len(data.get("chat_sessions", [])),
                    "chat_messages_count": len(data.get("chat_messages", []))
                },
                "export_time": data.get("export_time"),
                "version": data.get("version")
            }

        except Exception as e:
            logger.error(f"获取备份文件信息失败: {str(e)}")
            return None


backup_service = BackupService()