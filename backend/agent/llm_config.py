"""
大模型配置模块

初始化 OpenAI 客户端，配置大语言模型 API 连接参数。
支持阿里云百炼 API、DeeSeek API 等兼容 OpenAI 接口的大模型。

配置项（从环境变量读取）：
- LLM_API_KEY: API 密钥（必填）
- LLM_BASE_URL: API 地址（默认：阿里云百炼）
- LLM_MODEL: 对话模型（默认：deepseek-chat）
- LLM2_MODEL: Agent 专用模型（默认：qwen-max，用于复杂任务决策）

AgentLLMConfig 类：
- 为 Agent 提供专用的大模型配置
- Agent 使用更强模型处理复杂任务决策
- Chat 使用轻量模型进行对话
"""
import os
from dotenv import load_dotenv
from openai import OpenAI


# 加载环境变量（指定 .env 文件路径）
import os as _os
_current_dir = _os.path.dirname(_os.path.abspath(__file__))
_project_root = _os.path.dirname(_os.path.dirname(_current_dir))
_env_path = _os.path.join(_project_root, ".env")
load_dotenv(_env_path)

api_key = os.getenv("LLM_API_KEY")
base_url = os.getenv("LLM_BASE_URL")

if not api_key:
    # 兼容性检查：尝试读取旧的键名或提醒用户
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if api_key:
        print("⚠️ 警告: 正在使用旧的 DASHSCOPE_API_KEY，建议在 .env 中改为 LLM_API_KEY")
        # 如果使用了 DASHSCOPE_API_KEY 且没有提供 base_url，则自动补全百炼的 API 地址
        if not base_url:
            base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
            print(f"ℹ️ 信息: 已自动设置 Base URL 为 {base_url}")

if not api_key:
    raise ValueError("❌ 错误: 未在环境变量或 .env 文件中找到 LLM_API_KEY。请检查配置。")

# 初始化客户端
client = OpenAI(
    api_key=api_key,
    base_url=base_url,
)

# 大模型名称
model = os.getenv("LLM_MODEL", "deepseek-chat")


class AgentLLMConfig:
    """Agent 专用 LLM 配置

    支持双模型配置：Agent 使用更强的模型（如 qwen-max）做复杂任务决策，
    Chat 使用轻量模型（如 qwen-turbo）做对话。
    API Key 和 Base URL 与普通 LLM 共用同一套配置。
    """

    def __init__(self):
        # Agent 专用模型，读取 LLM2_MODEL，默认 qwen-max
        self.model = os.getenv("LLM2_MODEL", "qwen-max")

        # API Key 和 Base URL 复用普通 LLM 配置
        self.api_key = api_key
        self.base_url = base_url

        # 初始化 Agent 专用客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=60,
        )

    def __repr__(self) -> str:
        return f"AgentLLMConfig(model={self.model}, base_url={self.base_url})"


# 全局 Agent LLM 配置实例
agent_llm_config = AgentLLMConfig()
