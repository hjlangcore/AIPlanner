"""
数据库模块初始化文件

本模块包含SQLite数据库操作相关的组件，
负责任务数据的持久化存储。
"""
from .db_handler import db, TodoDatabase

__all__ = ["db", "TodoDatabase"]
