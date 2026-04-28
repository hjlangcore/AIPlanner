"""
知识库RAG增强服务模块

提供基于向量检索的增强知识库功能，支持语义搜索和上下文增强。
"""
import os
import json
import sqlite3
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class RAGService:
    """知识库增强检索服务类

    提供基于关键词和相似度的知识库检索功能。
    """

    def __init__(self, db_path: str = "todo_agent.db"):
        """初始化RAG服务

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._embedding_cache: Dict[str, List[float]] = {}

    def _get_db_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _simple_embed(self, text: str) -> List[float]:
        """简单的文本向量化方法

        使用词频TF作为向量化方法，适合没有向量数据库的环境。

        Args:
            text: 输入文本

        Returns:
            list: 向量表示
        """
        text = text.lower()
        words = text.split()

        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1

        total_words = len(words) if words else 1
        vector = []
        for word in sorted(set(words)):
            vector.append(word_freq[word] / total_words)

        return vector

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度

        Args:
            vec1: 向量1
            vec2: 向量2

        Returns:
            float: 相似度分数
        """
        if not vec1 or not vec2:
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def _get_keywords(self, text: str) -> set:
        """提取关键词

        Args:
            text: 输入文本

        Returns:
            set: 关键词集合
        """
        stop_words = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人',
            '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去',
            '你', '会', '着', '没有', '看', '好', '自己', '这', '什么',
            'how', 'the', 'is', 'to', 'and', 'a', 'of', 'in', 'for',
            'on', 'with', 'that', 'this', 'it', 'as', 'be', 'are', 'was'
        }

        text = text.lower()
        words = []
        current_word = ""

        for char in text:
            if char.isalnum():
                current_word += char
            else:
                if current_word:
                    words.append(current_word)
                current_word = ""

        if current_word:
            words.append(current_word)

        return {w for w in words if w not in stop_words and len(w) > 1}

    def add_knowledge(self, title: str, content: str, category: str = "默认", tags: str = "") -> int:
        """添加知识库条目

        Args:
            title: 标题
            content: 内容
            category: 分类
            tags: 标签（逗号分隔）

        Returns:
            int: 新增条目的ID
        """
        conn = self._get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO knowledge_base (title, content, category, tags) VALUES (?, ?, ?, ?)",
                (title, content, category, tags)
            )
            conn.commit()
            kb_id = cursor.lastrowid

            embedding = self._simple_embed(f"{title} {content}")
            self._embedding_cache[str(kb_id)] = embedding

            logger.info(f"添加知识库条目成功: {title}")
            return kb_id

        except Exception as e:
            logger.error(f"添加知识库条目失败: {str(e)}")
            raise
        finally:
            conn.close()

    def update_knowledge(self, kb_id: int, title: str, content: str, category: str = None, tags: str = None) -> bool:
        """更新知识库条目

        Args:
            kb_id: 知识库ID
            title: 标题
            content: 内容
            category: 分类（可选）
            tags: 标签（可选）

        Returns:
            bool: 更新是否成功
        """
        conn = self._get_db_connection()
        cursor = conn.cursor()

        try:
            updates = ["title = ?", "content = ?"]
            values = [title, content]

            if category is not None:
                updates.append("category = ?")
                values.append(category)

            if tags is not None:
                updates.append("tags = ?")
                values.append(tags)

            values.append(kb_id)

            cursor.execute(
                f"UPDATE knowledge_base SET {', '.join(updates)} WHERE id = ?",
                values
            )
            conn.commit()

            if cursor.rowcount > 0:
                embedding = self._simple_embed(f"{title} {content}")
                self._embedding_cache[str(kb_id)] = embedding
                logger.info(f"更新知识库条目成功: {kb_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"更新知识库条目失败: {str(e)}")
            return False
        finally:
            conn.close()

    def delete_knowledge(self, kb_id: int) -> bool:
        """删除知识库条目

        Args:
            kb_id: 知识库ID

        Returns:
            bool: 删除是否成功
        """
        conn = self._get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM knowledge_base WHERE id = ?", (kb_id,))
            conn.commit()

            if cursor.rowcount > 0:
                self._embedding_cache.pop(str(kb_id), None)
                logger.info(f"删除知识库条目成功: {kb_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"删除知识库条目失败: {str(e)}")
            return False
        finally:
            conn.close()

    def get_knowledge_by_id(self, kb_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取知识库条目

        Args:
            kb_id: 知识库ID

        Returns:
            dict: 知识库条目信息
        """
        conn = self._get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM knowledge_base WHERE id = ?", (kb_id,))
            row = cursor.fetchone()

            if row:
                return dict(row)

            return None

        except Exception as e:
            logger.error(f"获取知识库条目失败: {str(e)}")
            return None
        finally:
            conn.close()

    def search_knowledge(self, query: str, limit: int = 5, use_semantic: bool = True) -> List[Dict[str, Any]]:
        """搜索知识库

        Args:
            query: 查询文本
            limit: 返回结果数量
            use_semantic: 是否使用语义检索

        Returns:
            list: 匹配的知识库条目列表
        """
        conn = self._get_db_connection()
        cursor = conn.cursor()

        try:
            if not use_semantic:
                cursor.execute(
                    """SELECT * FROM knowledge_base
                       WHERE content LIKE ? OR title LIKE ? OR tags LIKE ?
                       ORDER BY id DESC LIMIT ?""",
                    (f"%{query}%", f"%{query}%", f"%{query}%", limit)
                )
                results = [dict(row) for row in cursor.fetchall()]
                return results

            query_embedding = self._simple_embed(query)
            query_keywords = self._get_keywords(query)

            cursor.execute("SELECT * FROM knowledge_base ORDER BY id DESC")
            all_knowledge = [dict(row) for row in cursor.fetchall()]

            scored_results = []

            for kb in all_knowledge:
                kb_id = str(kb['id'])

                if kb_id in self._embedding_cache:
                    semantic_score = self._cosine_similarity(query_embedding, self._embedding_cache[kb_id])
                else:
                    kb_embedding = self._simple_embed(f"{kb['title']} {kb['content']}")
                    self._embedding_cache[kb_id] = kb_embedding
                    semantic_score = self._cosine_similarity(query_embedding, kb_embedding)

                keyword_score = 0.0
                kb_keywords = self._get_keywords(f"{kb['title']} {kb['content']} {kb.get('tags', '')}")
                if query_keywords:
                    keyword_score = len(query_keywords & kb_keywords) / len(query_keywords)

                title_exact = 1.0 if query.lower() in kb['title'].lower() else 0.0

                combined_score = (semantic_score * 0.4 + keyword_score * 0.4 + title_exact * 0.2)

                scored_results.append({
                    'kb': kb,
                    'score': combined_score,
                    'semantic_score': semantic_score,
                    'keyword_score': keyword_score
                })

            scored_results.sort(key=lambda x: x['score'], reverse=True)

            return [r['kb'] for r in scored_results[:limit]]

        except Exception as e:
            logger.error(f"搜索知识库失败: {str(e)}")
            return []
        finally:
            conn.close()

    def get_context_for_query(self, query: str, max_contexts: int = 3) -> str:
        """为查询获取增强上下文

        Args:
            query: 查询文本
            max_contexts: 最大上下文数量

        Returns:
            str: 格式化的上下文字符串
        """
        results = self.search_knowledge(query, limit=max_contexts, use_semantic=True)

        if not results:
            return ""

        context_parts = []
        context_parts.append("相关知识库信息：")

        for i, kb in enumerate(results, 1):
            context_parts.append(f"\n[{i}] {kb['title']}")
            context_parts.append(f"分类: {kb.get('category', '默认')}")
            context_parts.append(f"内容: {kb['content']}")

        return "\n".join(context_parts)

    def get_all_knowledge(self, category: str = None) -> List[Dict[str, Any]]:
        """获取所有知识库条目

        Args:
            category: 按分类筛选（可选）

        Returns:
            list: 知识库条目列表
        """
        conn = self._get_db_connection()
        cursor = conn.cursor()

        try:
            if category:
                cursor.execute(
                    "SELECT * FROM knowledge_base WHERE category = ? ORDER BY id DESC",
                    (category,)
                )
            else:
                cursor.execute("SELECT * FROM knowledge_base ORDER BY id DESC")

            return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"获取知识库列表失败: {str(e)}")
            return []
        finally:
            conn.close()

    def get_categories(self) -> List[str]:
        """获取所有分类

        Returns:
            list: 分类列表
        """
        conn = self._get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT DISTINCT category FROM knowledge_base WHERE category IS NOT NULL ORDER BY category")
            return [row[0] for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"获取分类列表失败: {str(e)}")
            return []
        finally:
            conn.close()

    def batch_import(self, knowledge_list: List[Dict[str, Any]]) -> Dict[str, int]:
        """批量导入知识库条目

        Args:
            knowledge_list: 知识库条目列表

        Returns:
            dict: 导入统计
        """
        stats = {"success": 0, "failed": 0, "duplicates": 0}

        for kb in knowledge_list:
            try:
                title = kb.get("title")
                content = kb.get("content")
                category = kb.get("category", "默认")
                tags = kb.get("tags", "")

                if not title or not content:
                    stats["failed"] += 1
                    continue

                existing = self.search_knowledge(title, limit=1, use_semantic=False)
                if existing and any(e['title'] == title for e in existing):
                    stats["duplicates"] += 1
                    continue

                self.add_knowledge(title, content, category, tags)
                stats["success"] += 1

            except Exception as e:
                logger.error(f"批量导入失败: {str(e)}")
                stats["failed"] += 1

        logger.info(f"批量导入完成: {stats}")
        return stats


rag_service = RAGService()