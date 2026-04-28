"""
定时提醒服务模块

提供任务截止日期的定时检查和提醒功能，支持邮件提醒。
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import List, Callable
from ..db.db_handler import db


class ReminderService:
    """定时提醒服务类
    
    负责定时检查任务的截止日期，并触发提醒。使用 APScheduler 实现精准定时。
    """
    
    def __init__(self):
        """初始化提醒服务"""
        self.scheduler = BackgroundScheduler()
        self._callbacks: List[Callable] = []
        self._email_enabled = False
        self._email_service = None

    def add_callback(self, callback: Callable):
        """添加提醒回调函数
        
        Args:
            callback: 当检测到到期任务时调用的函数
        """
        self._callbacks.append(callback)

    def set_email_service(self, email_service):
        """设置邮件服务
        
        Args:
            email_service: 邮件服务实例
        """
        self._email_service = email_service
        self._email_enabled = True

    def check_deadline(self):
        """检查今日到期的任务
        
        如果有到期任务，调用所有注册的回调函数。
        """
        urgent_tasks = db.get_urgent_tasks()
        overdue_tasks = db.get_overdue_tasks()
        
        if urgent_tasks or overdue_tasks:
            # 调用回调函数
            for callback in self._callbacks:
                try:
                    callback(urgent_tasks, overdue_tasks)
                except Exception as e:
                    print(f"[ReminderService] 回调执行失败: {str(e)}")
            
            # 发送邮件提醒
            if self._email_enabled and self._email_service:
                try:
                    urgent_list = [
                        {"task": t[1], "deadline": t[2], "priority": t[3]}
                        for t in urgent_tasks
                    ]
                    overdue_list = [
                        {"task": t[1], "deadline": t[2], "priority": t[3]}
                        for t in overdue_tasks
                    ]
                    self._email_service.send_task_reminder(urgent_list, overdue_list)
                except Exception as e:
                    print(f"[ReminderService] 邮件发送失败: {str(e)}")

    def start(self):
        """启动提醒服务
        
        使用 APScheduler 在每天 09:00 和 14:00 自动执行检查。
        同时每 30 分钟执行一次常规巡检。
        """
        # 添加定时任务
        self.scheduler.add_job(self.check_deadline, CronTrigger(hour=9, minute=0))
        self.scheduler.add_job(self.check_deadline, CronTrigger(hour=14, minute=0))
        self.scheduler.add_job(self.check_deadline, 'interval', minutes=30)
        
        self.scheduler.start()
        print("[ReminderService] APScheduler 定时提醒服务已启动")

    def stop(self):
        """停止提醒服务"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            print("[ReminderService] 定时提醒服务已停止")


# 全局提醒服务实例
reminder_service = ReminderService()
