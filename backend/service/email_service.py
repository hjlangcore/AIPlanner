"""
邮件提醒服务模块

提供邮件提醒功能，支持SMTP发送任务到期提醒。
"""
import smtplib
import os
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Callable, Optional


class EmailReminderService:
    """邮件提醒服务类

    负责发送邮件提醒任务到期情况。
    """

    def __init__(self):
        """初始化邮件服务"""
        self.is_running = False
        self._thread = None
        self._callbacks: List[Callable] = []
        self._config_file = "email_config.json"

        # 从环境变量读取邮件配置，与 README.md 保持一致
        self.smtp_host = os.getenv("SMTP_SERVER", "")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASS", "")
        self.sender_email = os.getenv("SENDER_EMAIL", "")
        self.receiver_email = os.getenv("RECEIVER_EMAIL", "")

        self._load_config()

    def _load_config(self):
        """从配置文件加载邮件配置"""
        try:
            if os.path.exists(self._config_file):
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.smtp_host = config.get("smtp_host", self.smtp_host)
                    self.smtp_port = config.get("smtp_port", self.smtp_port)
                    self.smtp_user = config.get("smtp_user", self.smtp_user)
                    self.smtp_password = config.get("smtp_password", self.smtp_password)
                    self.sender_email = config.get("sender_email", self.sender_email)
                    self.receiver_email = config.get("receiver_email", self.receiver_email)
        except Exception as e:
            print(f"[EmailReminder] 加载邮件配置失败: {str(e)}")

    def save_config(self, config: dict) -> bool:
        """保存邮件配置到文件

        Args:
            config: 邮件配置信息

        Returns:
            bool: 保存是否成功
        """
        try:
            self.smtp_host = config.get("smtp_host", self.smtp_host)
            self.smtp_port = config.get("smtp_port", self.smtp_port)
            self.smtp_user = config.get("smtp_user", self.smtp_user)
            self.smtp_password = config.get("smtp_password", self.smtp_password)
            self.sender_email = config.get("sender_email", self.sender_email)
            self.receiver_email = config.get("receiver_email", self.receiver_email)

            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "smtp_host": self.smtp_host,
                    "smtp_port": self.smtp_port,
                    "smtp_user": self.smtp_user,
                    "smtp_password": self.smtp_password,
                    "sender_email": self.sender_email,
                    "receiver_email": self.receiver_email
                }, f, ensure_ascii=False, indent=2)

            print("[EmailReminder] 邮件配置已保存")
            return True
        except Exception as e:
            print(f"[EmailReminder] 保存邮件配置失败: {str(e)}")
            return False

    def get_config(self) -> dict:
        """获取当前邮件配置（不包含密码）

        Returns:
            dict: 邮件配置信息
        """
        return {
            "smtp_host": self.smtp_host,
            "smtp_port": self.smtp_port,
            "smtp_user": self.smtp_user,
            "sender_email": self.sender_email,
            "receiver_email": self.receiver_email,
            "is_configured": self.is_configured()
        }
    
    def is_configured(self) -> bool:
        """检查邮件服务是否已配置"""
        return bool(self.smtp_host and self.smtp_user and self.smtp_password and self.receiver_email)
    
    def send_email(self, subject: str, html_content: str) -> bool:
        """发送邮件
        
        Args:
            subject: 邮件主题
            html_content: HTML格式的邮件内容
        
        Returns:
            bool: 发送是否成功
        """
        if not self.is_configured():
            print("[EmailReminder] 邮件服务未配置，跳过发送")
            return False
        
        try:
            # 创建邮件
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.sender_email or self.smtp_user
            msg["To"] = self.receiver_email
            
            # 添加HTML内容
            html_part = MIMEText(html_content, "html", "utf-8")
            msg.attach(html_part)
            
            # 发送邮件
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            print(f"[EmailReminder] 邮件发送成功: {subject}")
            return True
        except Exception as e:
            print(f"[EmailReminder] 邮件发送失败: {str(e)}")
            return False
    
    def send_task_reminder(self, urgent_tasks: List[dict], overdue_tasks: List[dict] = None) -> bool:
        """发送任务提醒邮件
        
        Args:
            urgent_tasks: 今日到期任务列表
            overdue_tasks: 逾期任务列表
        
        Returns:
            bool: 发送是否成功
        """
        if not urgent_tasks and not overdue_tasks:
            print("[EmailReminder] 没有需要提醒的任务")
            return True
        
        # 生成HTML邮件内容
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px 10px 0 0; text-align: center; }}
                .content {{ background: #f8fafc; padding: 20px; border-radius: 0 0 10px 10px; }}
                .task-item {{ background: white; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #667eea; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .task-overdue {{ border-left-color: #ef4444; background: #fef2f2; }}
                .task-urgent {{ border-left-color: #f59e0b; background: #fffbeb; }}
                .priority {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }}
                .priority-high {{ background: #fee2e2; color: #ef4444; }}
                .priority-medium {{ background: #fef3c7; color: #d97706; }}
                .priority-low {{ background: #dbeafe; color: #2563eb; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📋 智能待办提醒</h1>
                    <p>{datetime.now().strftime('%Y年%m月%d日 %H:%M')}</p>
                </div>
                <div class="content">
        """
        
        # 逾期任务
        if overdue_tasks:
            html_content += "<h2 style='color: #ef4444;'>⚠️ 已逾期任务</h2>"
            for task in overdue_tasks:
                priority = task.get("priority", "中")
                pri_class = {"高": "priority-high", "中": "priority-medium", "低": "priority-low"}.get(priority, "priority-medium")
                html_content += f"""
                    <div class="task-item task-overdue">
                        <strong>{task.get('raw_task', task.get('task', ''))}</strong>
                        <br>
                        <span class="priority {pri_class}">{priority}</span>
                        <span style="color: #666; margin-left: 10px;">截止: {task.get('deadline', '')}</span>
                    </div>
                """
        
        # 今日到期任务
        if urgent_tasks:
            html_content += "<h2 style='color: #f59e0b;'>⏰ 今日到期任务</h2>"
            for task in urgent_tasks:
                priority = task.get("priority", "中")
                pri_class = {"高": "priority-high", "中": "priority-medium", "低": "priority-low"}.get(priority, "priority-medium")
                html_content += f"""
                    <div class="task-item task-urgent">
                        <strong>{task.get('raw_task', task.get('task', ''))}</strong>
                        <br>
                        <span class="priority {pri_class}">{priority}</span>
                    </div>
                """
        
        html_content += """
                </div>
                <div class="footer">
                    <p>此邮件由智能待办系统自动发送</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        subject = "📋 智能待办提醒"
        if overdue_tasks:
            subject = f"⚠️ 您有 {len(overdue_tasks)} 个逾期任务待处理！"
        elif urgent_tasks:
            subject = f"⏰ 您有 {len(urgent_tasks)} 个任务今日到期"
        
        return self.send_email(subject, html_content)
    
    def add_callback(self, callback: Callable):
        """添加提醒回调函数"""
        self._callbacks.append(callback)

    def send_test_email(self) -> dict:
        """发送测试邮件验证配置是否正确

        Returns:
            dict: 测试结果
        """
        if not self.is_configured():
            return {
                "success": False,
                "message": "邮件服务未配置，请先配置SMTP服务器信息"
            }

        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px 10px 0 0; text-align: center; }
                .content { background: #f8fafc; padding: 20px; border-radius: 0 0 10px 10px; }
                .success { color: #22c55e; font-size: 48px; text-align: center; }
                .footer { text-align: center; margin-top: 20px; color: #666; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✅ 智能待办系统</h1>
                    <p>测试邮件</p>
                </div>
                <div class="content">
                    <div class="success">✓</div>
                    <h2 style="text-align: center;">邮件服务配置成功！</h2>
                    <p style="text-align: center;">如果您收到这封邮件，说明智能待办系统的邮件提醒功能已配置正确。</p>
                    <p style="text-align: center; color: #666;">
                        发送时间: {time}
                    </p>
                </div>
                <div class="footer">
                    <p>此邮件由智能待办系统自动发送</p>
                </div>
            </div>
        </body>
        </html>
        """.format(time=datetime.now().strftime('%Y年%m月%d日 %H:%M:%S'))

        success = self.send_email("✅ 智能待办系统 - 邮件配置测试", html_content)

        if success:
            return {
                "success": True,
                "message": "测试邮件发送成功！"
            }
        else:
            return {
                "success": False,
                "message": "测试邮件发送失败，请检查SMTP配置"
            }


# 全局邮件提醒服务实例
email_reminder_service = EmailReminderService()
