# AIPlanner

基于 AI Agent 的智能待办与日程管理系统

## 功能特性

- **智能任务解析** - 自然语言输入，自动提取任务、截止日期和分类
- **任务智能拆解** - 根据复杂度自动拆解为可执行的子任务
- **优先级自动评估** - 基于截止日期和任务量智能标记优先级
- **日历视图** - FullCalendar 实现任务时间线分布
- **智能提醒系统** - 前端弹窗、浏览器通知、邮件多通道提醒
- **AI 对话助手** - 基于 RAG 技术的知识库增强对话

## 技术栈

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

## 环境要求

- Python 3.9+
- Node.js 18.0+
- npm 9.0+ 或 yarn

---

## 安装部署

### 1. 克隆项目

```bash
git clone https://github.com/hjlangcore/AIPlanner.git
cd AIPlanner
```

### 2. 后端部署

#### Windows

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

#### macOS / Linux

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

### 3. 前端部署

#### Windows / macOS / Linux

```bash
cd frontend/react-ts

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 4. 访问应用

- 前端应用: http://localhost:3000
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

---

## 环境变量配置

创建 `.env` 文件，配置以下参数：

| 变量 | 必填 | 说明 |
|------|------|------|
| `LLM_API_KEY` | 是 | 大语言模型 API Key |
| `LLM_BASE_URL` | 是 | API 请求地址 |
| `LLM_MODEL` | 否 | 模型名称，默认 `deepseek-chat` |
| `JWT_SECRET_KEY` | 否 | JWT 密钥 |
| `BACKEND_PORT` | 否 | 端口，默认 `8000` |

---

## 生产环境部署

### 后端

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### 前端构建

```bash
cd frontend/react-ts
npm run build
# 部署 dist 目录到 Web 服务器
```

---

## 项目结构

```
AIPlanner/
├── backend/
│   ├── agent/           # Agent 核心模块
│   ├── db/              # 数据库操作
│   ├── service/         # 业务服务
│   └── main.py         # FastAPI 入口
├── frontend/
│   └── react-ts/        # React 前端
├── requirements.txt
├── .env.example
└── README.md
```

---

## License

MIT
