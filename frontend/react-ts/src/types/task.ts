export type TaskStatus = '待执行' | '进行中' | '已完成' | '已过期'
export type TaskPriority = '高' | '中' | '低'

export interface SubTask {
  text: string
  completed: boolean
}

export interface Task {
  id: number
  raw_task: string
  sub_tasks: SubTask[]
  priority: TaskPriority
  deadline: string
  schedule: string
  status: TaskStatus
  category: string
  tags: string[]
  progress: number
  notes: string
  update_time: string
  create_time: string
}

export interface TaskCreate {
  raw_input: string
}

export interface ApiResult {
  success: boolean
  error?: string
}

export interface CreateTaskResponse extends ApiResult {
  task_info?: {
    raw_input?: string
    task_name?: string
    deadline?: string
    sub_tasks?: string[]
    priority?: TaskPriority
  }
}

export interface TaskStatusUpdate {
  status: TaskStatus
}

export interface ReminderTask {
  id: number
  task: string
  deadline: string
  priority: TaskPriority
  category: string
}

export interface Category {
  id: number
  name: string
  color: string
  icon: string
}

export interface Statistics {
  total: number
  completed: number
  in_progress: number
  pending: number
  urgent: number
  today_deadline: number
  overdue: number
  completion_rate: number
  recent_stats: {
    date: string
    created: number
    completed: number
  }[]
}

export interface DashboardData {
  stats: Statistics
  today_tasks: ReminderTask[]
  overdue_tasks: ReminderTask[]
  categories: Category[]
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: {
    username: string
    full_name: string
  }
}

export interface RegisterRequest {
  username: string
  password: string
  full_name?: string
  email?: string
}

export interface ChatSession {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  intent?: string
  slots?: any
  created_at: string
}

// 筛选预设相关类型
export interface FilterPreset {
  id?: number
  name: string
  filters: {
    status?: string
    priority?: string
    category?: string
    tag?: string
    dateRange?: [string, string]
    progressRange?: [number, number]
  }
  created_at?: string
}

// 任务模板相关类型
export interface TaskTemplate {
  id?: number
  name: string
  description?: string
  priority: TaskPriority
  category: string
  tags: string[]
  sub_tasks: SubTask[]
  notes: string
  created_at?: string
}

// 从模板创建任务的请求
export interface TaskManualCreate {
  raw_task: string
  sub_tasks?: string[]
  priority?: TaskPriority
  deadline?: string
  schedule?: string
  category?: string
  tags?: string[]
  notes?: string
}

export interface CreateTaskFromTemplateRequest {
  templateId: number
  customDeadline?: string
  customName?: string
}

// Agent相关类型
export interface ToolCall {
  tool_name: string
  parameters: Record<string, any>
  result: string
  timestamp: number
  success: boolean
}

export interface PlanStep {
  step: number
  description: string
  tool: string | null
  parameters: Record<string, any>
}

export interface AgentMessageResponse {
  response: string
  agent_state: string
  tool_calls: ToolCall[]
  plan: PlanStep[]
}

export interface AgentStreamEvent {
  step: string
  message: string
  progress: number
  data: {
    plan?: PlanStep[]
    step?: PlanStep
    tool_call?: ToolCall
    tool_result?: {
      tool_name?: string
      parameters?: Record<string, any>
      result?: any
      success?: boolean
      message?: string
      error?: string
    }
    response?: string
    tool_calls?: ToolCall[]
  } | null
}
