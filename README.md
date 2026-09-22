# AIPlanner

[English](#aiplanner-english) | [中文](#aiplanner-中文)

---

## AIPlanner (English)

An intelligent task and schedule management system powered by AI Agents.

### Features

- **Intelligent Task Parsing** - Natural language input with automatic extraction of tasks, deadlines, and categories
- **Smart Task Breakdown** - Automatically decomposes complex tasks into executable sub-tasks
- **Automatic Priority Assessment** - Intelligently marks priorities based on deadlines and task volume
- **Calendar View** - FullCalendar implementation for task timeline distribution
- **Smart Reminder System** - Multi-channel reminders via frontend popups, browser notifications, and email
- **AI Chat Assistant** - Knowledge base enhanced conversation based on RAG technology

### Tech Stack

**Backend**
- Python 3.9+ / FastAPI
- LangGraph (Agent workflow)
- SQLite3 (Database)
- JWT + Bcrypt (Authentication)

**Frontend**
- React 18 + TypeScript
- Ant Design 5.x
- Zustand (State Management)
- FullCalendar (Calendar)

### Requirements

- Python 3.9+
- Node.js 18.0+
- npm 9.0+ or yarn

---

### Installation & Deployment

#### 1. Clone the Repository

```bash
git clone https://github.com/hjlangcore/AIPlanner.git
cd AIPlanner
```

#### 2. Backend Setup

##### Windows

```powershell
# Navigate to project directory
cd AIPlanner

# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and edit environment variables file
copy .env.example .env
# Open .env with Notepad and fill in configuration
notepad .env

# Start backend server
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

##### macOS / Linux

```bash
# Navigate to project directory
cd AIPlanner

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and edit environment variables file
cp .env.example .env
nano .env  # Edit configuration

# Start backend server
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 3. Frontend Setup

##### Windows / macOS / Linux

```bash
cd frontend/react-ts

# Install dependencies
npm install

# Start development server
npm run dev
```

#### 4. Access the Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

---

### Environment Variables Configuration

Create a `.env` file with the following parameters:

| Variable | Required | Description |
|----------|----------|-------------|
| `LLM_API_KEY` | Yes | Large Language Model API Key |
| `LLM_BASE_URL` | Yes | API endpoint URL |
| `LLM_MODEL` | No | Model name, default `deepseek-chat` |
| `JWT_SECRET_KEY` | Yes* | JWT secret key (required for production) |
| `ALLOWED_ORIGINS` | No | Allowed CORS origins, default `http://localhost:3000,http://localhost:8080` |
| `BACKEND_PORT` | No | Port number, default `8000` |

> **Security Notice**: In production environments, `JWT_SECRET_KEY` must be set via environment variable. Use a secure random key generator.

---

### Production Deployment

#### Backend

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

#### Frontend Build

```bash
cd frontend/react-ts
npm run build
# Deploy the dist directory to your web server
```

---

### Project Structure

```
AIPlanner/
├── backend/
│   ├── agent/           # Agent core modules
│   ├── db/              # Database operations
│   ├── service/         # Business services
│   └── main.py          # FastAPI entry point
├── frontend/
│   └── react-ts/        # React frontend
├── requirements.txt
├── .env.example
└── README.md
```

---

## AIPlanner (中文)

基于 AI Agent 的智能待办与日程管理系统

### 功能特性

- **智能任务解析** - 自然语言输入，自动提取任务、截止日期和分类
- **任务智能拆解** - 根据复杂度自动拆解为可执行的子任务
- **优先级自动评估** - 基于截止日期和任务量智能标记优先级
- **日历视图** - FullCalendar 实现任务时间线分布
- **智能提醒系统** - 前端弹窗、浏览器通知、邮件多通道提醒
- **AI 对话助手** - 基于 RAG 技术的知识库增强对话

### 技术栈

**后端**
- Python 3.9+ / FastAPI
- LangGraph (Agent 工作流)
- SQLite3 (数据库)
- JWT + Bcrypt (认证)

**前端**
- React 18 + TypeScript
- Ant Design 5.x
- Zustand (状态管理)
- FullCalendar (日历)

### 环境要求

- Python 3.9+
- Node.js 18.0+
- npm 9.0+ 或 yarn

---

### 安装部署

#### 1. 克隆项目

```bash
git clone https://github.com/hjlangcore/AIPlanner.git
cd AIPlanner
```

#### 2. 后端部署

##### Windows

```powershell
# 进入项目目录
cd AIPlanner

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 复制并编辑环境变量文件
copy .env.example .env
# 用记事本打开 .env 填入配置
notepad .env

# 启动后端服务
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

##### macOS / Linux

```bash
# 进入项目目录
cd AIPlanner

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 复制并编辑环境变量文件
cp .env.example .env
nano .env  # 编辑配置

# 启动后端服务
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 3. 前端部署

##### Windows / macOS / Linux

```bash
cd frontend/react-ts

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

#### 4. 访问应用

- 前端应用：http://localhost:3000
- 后端 API: http://localhost:8000
- API 文档：http://localhost:8000/docs

---

### 环境变量配置

创建 `.env` 文件，配置以下参数：

| 变量 | 必填 | 说明 |
|------|------|------|
| `LLM_API_KEY` | 是 | 大语言模型 API Key |
| `LLM_BASE_URL` | 是 | API 请求地址 |
| `LLM_MODEL` | 否 | 模型名称，默认 `deepseek-chat` |
| `JWT_SECRET_KEY` | 是* | JWT 密钥（生产环境必填） |
| `ALLOWED_ORIGINS` | 否 | 允许的跨域来源，默认 `http://localhost:3000,http://localhost:8080` |
| `BACKEND_PORT` | 否 | 端口，默认 `8000` |

> **安全提示**：生产环境中必须通过环境变量设置 `JWT_SECRET_KEY`。请使用安全的随机密钥生成器。

---

### 生产环境部署

#### 后端

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

#### 前端构建

```bash
cd frontend/react-ts
npm run build
# 部署 dist 目录到 Web 服务器
```

---

### 项目结构

```
AIPlanner/
├── backend/
│   ├── agent/           # Agent 核心模块
│   ├── db/              # 数据库操作
│   ├── service/         # 业务服务
│   └── main.py          # FastAPI 入口
├── frontend/
│   └── react-ts/        # React 前端
├── requirements.txt
├── .env.example
└── README.md
```

---

### 多语言支持 / Multi-language Support

本项目文档支持中英文双语。如需添加其他语言支持，请参考以下示例：

This project documentation supports both Chinese and English. To add support for other languages, please refer to the example below:

#### 添加新语言 / Adding New Languages

1. 在本文档顶部添加新语言的链接 / Add a link to the new language at the top of this document
2. 翻译相应章节 / Translate the corresponding sections
3. 提交 Pull Request / Submit a Pull Request

**示例语言列表 / Example Language List:**
- 🇺🇸 English
- 🇨🇳 中文
- 🇯🇵 日本語 (Japanese) - *Coming soon*
- 🇰🇷 한국어 (Korean) - *Coming soon*
- 🇫🇷 Français (French) - *Coming soon*
- 🇩🇪 Deutsch (German) - *Coming soon*

---

### 许可证 / License

MIT License

### 联系方式 / Contact

- GitHub: [@hjlangcore](https://github.com/hjlangcore)
- Issues: [GitHub Issues](https://github.com/hjlangcore/AIPlanner/issues)

---
