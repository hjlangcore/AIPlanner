import axios from 'axios'
import {
  Task,
  TaskStatus,
  ReminderTask,
  DashboardData,
  Statistics,
  Category,
  ApiResult,
  CreateTaskResponse,
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  ChatSession,
  ChatMessage,
  FilterPreset,
  TaskTemplate,
  TaskCreate,
  TaskManualCreate
} from '../types/task'

export const API_URL = '/api'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// ==================== Token 管理 ====================

/**
 * 获取认证 Token
 * 优先从 zustand persist 存储读取，兼容旧的直接存储方式
 */
const getAuthToken = (): string | null => {
  try {
    // 方式1: 从 zustand persist 存储读取 (auth-storage)
    const authData = localStorage.getItem('auth-storage')
    if (authData) {
      const parsed = JSON.parse(authData)
      if (parsed.state?.token) {
        return parsed.state.token
      }
    }
    
    // 方式2: 直接从 localStorage 读取 (旧方式)
    const directToken = localStorage.getItem('token')
    if (directToken) {
      return directToken
    }
    
    // 方式3: 从其他可能的存储键读取
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)
      if (key && key.includes('token')) {
        const value = localStorage.getItem(key)
        if (value && !value.includes('{')) {
          return value
        }
      }
    }
  } catch (e) {
    console.error('[Auth] 读取 Token 失败:', e)
  }
  
  console.warn('[Auth] 未找到有效的认证 Token')
  return null
}

/**
 * 检查用户是否已认证
 */
const checkIsAuthenticated = (): boolean => {
  const token = getAuthToken()
  return token !== null && token.length > 0
}

/**
 * 清除认证信息
 */
const clearAuth = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('auth-storage')
}

// ==================== 请求拦截器 ====================

api.interceptors.request.use(config => {
  const token = getAuthToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}, error => {
  console.error('[API] 请求拦截器错误:', error)
  return Promise.reject(error)
})

api.interceptors.response.use(
  response => {
    return response
  },
  error => {
    console.error('[API] 响应错误:', error)
    if (error.response && error.response.status === 401) {
      console.warn('[API] 认证失败，清除认证信息')
      clearAuth()
      // 可以选择重定向到登录页
      // window.location.href = '/login'
    }
    if (error.response) {
      console.error('[API] 错误响应:', error.response.status, error.response.data)
    }
    return Promise.reject(error)
  }
)

// ==================== API 接口定义 ====================

export const taskApi = {
  // 认证相关
  login: (data: LoginRequest) => api.post<LoginResponse>('/auth/login', data),
  register: (data: RegisterRequest) => api.post<ApiResult>('/auth/register', data),

  // 聊天相关
  createChatSession: (title?: string) => api.post<{ session_id: string }>('/chat/sessions', { title }),
  getChatSessions: () => api.get<ChatSession[]>('/chat/sessions'),
  getChatMessages: (sessionId: string) => api.get<ChatMessage[]>(`/chat/messages/${sessionId}`),
  sendChatMessage: (sessionId: string, message: string) => api.post<{ response: string }>('/chat/message', { session_id: sessionId, message }),
  deleteChatSession: (sessionId: string) => api.delete<ApiResult>(`/chat/sessions/${sessionId}`),
  exportChat: (sessionId: string) => {
    const token = getAuthToken()
    return `${window.location.origin}/api/chat/export/${sessionId}?token=${token || ''}`
  },

  // 健康检查
  healthCheck: () => api.get('/health'),

  // 任务相关
  getTasks: (params?: { status?: string; category?: string; priority?: string }) =>
    api.get<Task[]>('/tasks', { params }),
  createTask: (data: TaskCreate) => api.post<CreateTaskResponse>('/tasks', data),
  createTaskManual: (data: TaskManualCreate) => api.post<CreateTaskResponse>('/tasks/manual', data),
  updateTask: (id: number, data: Partial<Task>) => api.put<ApiResult>(`/tasks/${id}`, data),
  deleteTask: (id: number) => api.delete<ApiResult>(`/tasks/${id}`),
  getTask: (id: number) => api.get<Task>(`/tasks/${id}`),

  // 分类相关
  getCategories: () => api.get<Category[]>('/categories'),
  createCategory: (data: Partial<Category>) => api.post<Category>('/categories', data),
  updateCategory: (id: number, data: Partial<Category>) => api.put<Category>(`/categories/${id}`, data),
  deleteCategory: (id: number) => api.delete<ApiResult>(`/categories/${id}`),

  // 统计相关
  getStatistics: () => api.get<Statistics>('/statistics'),
  getDashboard: () => api.get<DashboardData>('/dashboard'),
  getTasksByDate: (date: string) => api.get<Task[]>(`/tasks/by-date/${date}`),
  getUpcomingDeadlines: (days: number = 7) => api.get<ReminderTask[]>(`/tasks/upcoming?days=${days}`),

  // 筛选预设
  getFilterPresets: () => api.get<FilterPreset[]>('/filter-presets'),
  createFilterPreset: (data: Partial<FilterPreset>) => api.post<FilterPreset>('/filter-presets', data),
  deleteFilterPreset: (id: number) => api.delete<ApiResult>(`/filter-presets/${id}`),

  // 任务模板
  getTaskTemplates: () => api.get<TaskTemplate[]>('/task-templates'),
  createTaskTemplate: (data: Partial<TaskTemplate>) => api.post<TaskTemplate>('/task-templates', data),
  deleteTaskTemplate: (id: number) => api.delete<ApiResult>(`/task-templates/${id}`),

  // 智能筛选
  smartSearch: (query: string) => api.get<Task[]>('/tasks/smart-search', { params: { query } }),
  suggestCategories: (taskName: string) => api.get<string[]>('/categories/suggest', { params: { task_name: taskName } }),
  getSimilarTasks: (taskId: number) => api.get<Task[]>('/tasks/similar', { params: { task_id: taskId } }),

  // 任务冲突检测
  checkTaskConflicts: (deadline: string, taskId?: number) => api.get<Task[]>(`/tasks/conflicts`, { 
    params: { deadline, task_id: taskId } 
  }),

  // Agent相关接口
  sendAgentMessage: (sessionId: string, message: string) => api.post<any>('/agent/message', { 
    session_id: sessionId, 
    message 
  }),
  
  // 流式发送Agent消息
  // 注意：EventSource只支持GET请求，token通过URL传递（安全限制）
  // 使用完毕后请调用 closeEventSource(eventSource) 关闭连接
  sendAgentMessageStream: (sessionId: string, message: string) => {
    const token = getAuthToken()
    
    if (!token) {
      console.error('[Agent Stream] 未找到有效的认证 Token')
      // 返回一个错误的事件源
      const errorEventSource = {
        onopen: null,
        onmessage: null,
        onerror: null,
        close: () => {},
        readyState: 2 // EventSource.CLOSED
      } as any
      // 触发错误回调
      setTimeout(() => {
        if (errorEventSource.onerror) {
          errorEventSource.onerror(new Error('未认证'))
        }
      }, 0)
      return errorEventSource
    }
    
    // 构建URL，注意消息需要编码，并且需要添加时间戳避免缓存
    const timestamp = Date.now()
    const encodedMessage = encodeURIComponent(message)
    const url = `/api/agent/message/stream?session_id=${sessionId}&message=${encodedMessage}&token=${encodeURIComponent(token)}&t=${timestamp}`
    
    console.log('[Agent Stream] 创建EventSource连接')
    const eventSource = new EventSource(url)
    
    // 设置超时检测（120秒）
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const timeoutId = window.setTimeout(() => {
      console.error('[Agent Stream] 连接超时，关闭连接')
      eventSource.close()
    }, 120000)
    
    // 在返回的eventSource上保存timeoutId，方便后续清理
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(eventSource as any)._timeoutId = timeoutId
    
    return eventSource
  },

  // 关闭EventSource连接，释放资源
  closeEventSource: (eventSource: EventSource | null) => {
    if (eventSource) {
      if ((eventSource as any)._timeoutId) {
        clearTimeout((eventSource as any)._timeoutId)
      }
      eventSource.close()
    }
  }
}

// 导出辅助函数供其他组件使用
export { getAuthToken, checkIsAuthenticated as isAuthenticated, clearAuth }
