"""
任务标签管理服务模块

提供任务标签的增删改查、统计和任务关联功能。
"""
import os
import json
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class TagService:
    """任务标签管理服务类

    负责管理所有任务标签，支持标签的增删改查、统计和颜色自定义。
    """

    def __init__(self, db_path: str = "todo_agent.db"):
        """初始化标签服务

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._ensure_tags_table()

    def _get_db_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_tags_table(self):
        """确保标签表存在"""
        conn = self._get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    color TEXT DEFAULT '#5b7cff',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    usage_count INTEGER DEFAULT 0
                )
            """)

            existing_tags = self.get_all_tags()
            if not existing_tags:
                default_tags = [
                    ("工作", "#ef4444"),
                    ("学习", "#22c55e"),
                    ("生活", "#3b82f6"),
                    ("紧急", "#f59e0b"),
                    ("重要", "#8b5cf6"),
                    ("日常", "#06b6d4")
                ]
                for name, color in default_tags:
                    try:
                        cursor.execute(
                            "INSERT INTO tags (name, color) VALUES (?, ?)",
                            (name, color)
                        )
                    except:
                        pass

            conn.commit()

        except Exception as e:
            logger.error(f"确保标签表存在失败: {str(e)}")
        finally:
            conn.close()

    def create_tag(self, name: str, color: str = "#5b7cff") -> int:
        """创建新标签

        Args:
            name: 标签名称
            color: 标签颜色（十六进制）

        Returns:
            int: 新标签ID
        """
        conn = self._get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO tags (name, color) VALUES (?, ?)",
                (name, color)
            )
            conn.commit()
            tag_id = cursor.lastrowid
            logger.info(f"创建标签成功: {name}")
            return tag_id

        except sqlite3.IntegrityError:
            logger.warning(f"标签已存在: {name}")
            raise ValueError(f"标签 '{name}' 已存在")
        except Exception as e:
            logger.error(f"创建标签失败: {str(e)}")
            raise
        finally:
            conn.close()

    def update_tag(self, tag_id: int, name: str = None, color: str = None) -> bool:
        """更新标签

        Args:
            tag_id: 标签ID
            name: 新名称（可选）
            color: 新颜色（可选）

        Returns:
            bool: 更新是否成功
        """
        conn = self._get_db_connection()
        cursor = conn.cursor()

        try:
            updates = []
            values = []

            if name is not None:
                updates.append("name = ?")
                values.append(name)

            if color is not None:
                updates.append("color = ?")
                values.append(color)

            if not updates:
                return False

            values.append(tag_id)

            cursor.execute(
                f"UPDATE tags SET {', '.join(updates)} WHERE id = ?",
                values
            )
            conn.commit()

            if cursor.rowcount > 0:
                logger.info(f"更新标签成功: {tag_id}")
                return True

            return False

        except sqlite3.IntegrityError:
            logger.warning(f"标签名称已存在")
            raise ValueError("标签名称已存在")
        except Exception as e:
            logger.error(f"更新标签失败: {str(e)}")
            return False
        finally:
            conn.close()

    def delete_tag(self, tag_id: int) -> bool:
        """删除标签

        Args:
            tag_id: 标签ID

        Returns:
            bool: 删除是否成功
        """
        conn = self._get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
            conn.commit()

            if cursor.rowcount > 0:
                logger.info(f"删除标签成功: {tag_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"删除标签失败: {str(e)}")
            return False
        finally:
            conn.close()

    def get_tag_by_id(self, tag_id: int) -> Optional[Dict[str, Any]]:
        """获取标签详情

        Args:
            tag_id: 标签ID

        Returns:
            dict: 标签信息
        """
        conn = self._get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM tags WHERE id = ?", (tag_id,))
            row = cursor.fetchone()

            if row:
                return dict(row)

            return None

        except Exception as e:
            logger.error(f"获取标签失败: {str(e)}")
            return None
        finally:
            conn.close()

    def get_tag_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取标签

        Args:
            name: 标签名称

        Returns:
            dict: 标签信息
        """
        conn = self._get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM tags WHERE name = ?", (name,))
            row = cursor.fetchone()

            if row:
                return dict(row)

            return None

        except Exception as e:
            logger.error(f"获取标签失败: {str(e)}")
            return None
        finally:
            conn.close()

    def get_all_tags(self) -> List[Dict[str, Any]]:
        """获取所有标签

        Returns:
            list: 标签列表
        """
        conn = self._get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM tags ORDER BY usage_count DESC, name ASC")
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"获取标签列表失败: {str(e)}")
            return []
        finally:
            conn.close()

    def increment_usage(self, tag_name: str) -> bool:
        """增加标签使用次数

        Args:
            tag_name: 标签名称

        Returns:
            bool: 操作是否成功
        """
        conn = self._get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "UPDATE tags SET usage_count = usage_count + 1 WHERE name = ?",
                (tag_name,)
            )
            conn.commit()
            return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"增加标签使用次数失败: {str(e)}")
            return False
        finally:
            conn.close()

    def decrement_usage(self, tag_name: str) -> bool:
        """减少标签使用次数

        Args:
            tag_name: 标签名称

        Returns:
            bool: 操作是否成功
        """
        conn = self._get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "UPDATE tags SET usage_count = MAX(0, usage_count - 1) WHERE name = ?",
                (tag_name,)
            )
            conn.commit()
            return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"减少标签使用次数失败: {str(e)}")
            return False
        finally:
            conn.close()

    def get_tag_statistics(self) -> Dict[str, Any]:
        """获取标签统计信息

        Returns:
            dict: 统计信息
        """
        conn = self._get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT COUNT(*) as total_tags FROM tags")
            total_tags = cursor.fetchone()["total_tags"]

            cursor.execute("SELECT SUM(usage_count) as total_usage FROM tags")
            total_usage = cursor.fetchone()["total_usage"] or 0

            cursor.execute("SELECT * FROM tags ORDER BY usage_count DESC LIMIT 10")
            top_tags = [dict(row) for row in cursor.fetchall()]

            cursor.execute("SELECT usage_count, COUNT(*) as count FROM tags GROUP BY usage_count")
            distribution = [dict(row) for row in cursor.fetchall()]

            return {
                "total_tags": total_tags,
                "total_usage": total_usage,
                "top_tags": top_tags,
                "distribution": distribution
            }

        except Exception as e:
            logger.error(f"获取标签统计失败: {str(e)}")
            return {
                "total_tags": 0,
                "total_usage": 0,
                "top_tags": [],
                "distribution": []
            }
        finally:
            conn.close()

    def search_tags(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索标签

        Args:
            keyword: 搜索关键词

        Returns:
            list: 匹配的标签列表
        """
        conn = self._get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT * FROM tags WHERE name LIKE ? ORDER BY usage_count DESC",
                (f"%{keyword}%",)
            )
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"搜索标签失败: {str(e)}")
            return []
        finally:
            conn.close()

    def sync_task_tags(self, task_id: int, tags: List[str]) -> bool:
        """同步任务的标签使用统计

        Args:
            task_id: 任务ID
            tags: 任务的标签列表

        Returns:
            bool: 操作是否成功
        """
        try:
            for tag_name in tags:
                self.increment_usage(tag_name.strip())
            return True

        except Exception as e:
            logger.error(f"同步任务标签失败: {str(e)}")
            return False


tag_service = TagService()