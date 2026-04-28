import { create } from 'zustand'
import { ChatSession, ChatMessage, ToolCall, PlanStep, AgentStreamEvent } from '../types/task'
import { taskApi } from '../api/taskApi'

interface ChatState {
  sessions: ChatSession[]
  currentSessionId: string | null
  messages: ChatMessage[]
  loading: boolean
  sending: boolean
  
  // Agent相关状态
  agentMode: boolean
  agentState: string
  agentPlan: PlanStep[]
  agentToolCalls: ToolCall[]
  agentProgress: number
  agentStreaming: boolean
  
  fetchSessions: () => Promise<void>
  setCurrentSession: (sessionId: string) => Promise<void>
  createSession: (title?: string) => Promise<string>
  deleteSession: (sessionId: string) => Promise<void>
  sendMessage: (message: string) => Promise<void>
  clearMessages: () => void
  
  // Agent相关方法
  setAgentMode: (mode: boolean) => void
  sendAgentMessage: (message: string) => Promise<void>
  sendAgentMessageStream: (message: string) => void
  clearAgentState: () => void
}

// 从本地存储获取会话ID
const getStoredSessionId = (): string | null => {
  try {
    return localStorage.getItem('currentChatSessionId')
  } catch (error) {
    console.error('获取存储的会话ID失败:', error)
    return null
  }
}

// 保存会话ID到本地存储
const storeSessionId = (sessionId: string | null) => {
  try {
    if (sessionId) {
      localStorage.setItem('currentChatSessionId', sessionId)
    } else {
      localStorage.removeItem('currentChatSessionId')
    }
  } catch (error) {
    console.error('保存会话ID失败:', error)
  }
}

export const useChatStore = create<ChatState>((set, get) => ({
  sessions: [],
  currentSessionId: getStoredSessionId(),
  messages: [],
  loading: false,
  sending: false,
  
  // Agent相关状态
  agentMode: false,
  agentState: 'idle',
  agentPlan: [],
  agentToolCalls: [],
  agentProgress: 0,
  agentStreaming: false,

  fetchSessions: async () => {
    try {
      const res = await taskApi.getChatSessions()
      set({ sessions: res.data })
      
      // 如果有存储的会话ID，检查是否存在
      const storedSessionId = getStoredSessionId()
      if (storedSessionId) {
        const sessionExists = res.data.some(session => session.id === storedSessionId)
        if (sessionExists) {
          await get().setCurrentSession(storedSessionId)
        } else {
          // 如果存储的会话不存在，使用第一个会话或创建新会话
          if (res.data.length > 0) {
            await get().setCurrentSession(res.data[0].id)
          } else {
            const newSessionId = await get().createSession()
            await get().setCurrentSession(newSessionId)
          }
        }
      } else if (res.data.length > 0) {
        // 如果没有存储的会话ID，使用第一个会话
        await get().setCurrentSession(res.data[0].id)
      } else {
        // 如果没有会话，创建一个新会话
        const newSessionId = await get().createSession()
        await get().setCurrentSession(newSessionId)
      }
    } catch (error) {
      console.error('获取会话列表失败:', error)
    }
  },

  setCurrentSession: async (sessionId: string) => {
    set({ currentSessionId: sessionId, loading: true })
    storeSessionId(sessionId)
    try {
      const res = await taskApi.getChatMessages(sessionId)
      set({ messages: res.data, loading: false })
    } catch (error) {
      console.error('获取消息历史失败:', error)
      set({ loading: false })
    }
  },

  createSession: async (title?: string) => {
    try {
      const res = await taskApi.createChatSession(title)
      await get().fetchSessions()
      return res.data.session_id
    } catch (error) {
      console.error('创建会话失败:', error)
      throw error
    }
  },

  deleteSession: async (sessionId: string) => {
    try {
      await taskApi.deleteChatSession(sessionId)
      const { currentSessionId, sessions } = get()
      if (currentSessionId === sessionId) {
        const remainingSessions = sessions.filter(s => s.id !== sessionId)
        if (remainingSessions.length > 0) {
          await get().setCurrentSession(remainingSessions[0].id)
        } else {
          const newSessionId = await get().createSession()
          await get().setCurrentSession(newSessionId)
        }
      }
      await get().fetchSessions()
    } catch (error) {
      console.error('删除会话失败:', error)
      throw error
    }
  },

  sendMessage: async (message: string) => {
    const { currentSessionId, messages } = get()
    if (!currentSessionId) return

    // 乐观更新用户消息
    const userMsg: ChatMessage = {
      role: 'user',
      content: message,
      created_at: new Date().toISOString()
    }
    set({ messages: [...messages, userMsg], sending: true })

    try {
      const res = await taskApi.sendChatMessage(currentSessionId, message)
      const assistantMsg: ChatMessage = {
        role: 'assistant',
        content: res.data.response || '抱歉，AI未返回有效响应。',
        created_at: new Date().toISOString()
      }
      set({ messages: [...get().messages, assistantMsg], sending: false })
    } catch (error: any) {
      console.error('发送消息失败:', error)

      // 根据错误类型提供更友好的提示
      let errorContent = '抱歉，大模型服务暂时不可用，请稍后再试。'

      if (error.response?.status === 401) {
        errorContent = '认证失败，请重新登录。'
      } else if (error.response?.status === 429) {
        errorContent = '请求过于频繁，请稍后再试。'
      } else if (error.response?.status === 500) {
        errorContent = '服务器处理出错，请稍后再试。'
      } else if (!navigator.onLine) {
        errorContent = '网络连接已断开，请检查网络。'
      }

      const errorMsg: ChatMessage = {
        role: 'assistant',
        content: errorContent,
        created_at: new Date().toISOString()
      }
      set({ messages: [...get().messages, errorMsg], sending: false })
    }
  },

  clearMessages: () => {
    set({ messages: [], currentSessionId: null })
    storeSessionId(null)
  },

  // Agent相关方法
  setAgentMode: (mode: boolean) => {
    set({ agentMode: mode })
    if (!mode) {
      // 退出Agent模式时清除Agent状态
      get().clearAgentState()
    }
  },

  sendAgentMessage: async (message: string) => {
    const { currentSessionId, messages } = get()
    if (!currentSessionId) return

    // 乐观更新用户消息
    const userMsg: ChatMessage = {
      role: 'user',
      content: message,
      created_at: new Date().toISOString()
    }
    set({ messages: [...messages, userMsg], sending: true })

    try {
      const res = await taskApi.sendAgentMessage(currentSessionId, message)
      const assistantMsg: ChatMessage = {
        role: 'assistant',
        content: res.data.response,
        created_at: new Date().toISOString()
      }
      set({
        messages: [...get().messages, assistantMsg],
        sending: false,
        agentState: res.data.agent_state,
        agentPlan: res.data.plan,
        agentToolCalls: res.data.tool_calls
      })
    } catch (error) {
      console.error('发送Agent消息失败:', error)
      // 显示错误提示
      const errorMsg: ChatMessage = {
        role: 'assistant',
        content: '抱歉，Agent服务暂时不可用，请稍后再试。',
        created_at: new Date().toISOString()
      }
      set({ messages: [...get().messages, errorMsg], sending: false })
    }
  },

  sendAgentMessageStream: (message: string) => {
    const { currentSessionId, messages } = get()
    if (!currentSessionId) return
  
    // 乐观更新用户消息
    const userMsg: ChatMessage = {
      role: 'user',
      content: message,
      created_at: new Date().toISOString()
    }
    set({ 
      messages: [...messages, userMsg], 
      sending: true,
      agentStreaming: true,
      agentProgress: 0,
      agentPlan: [],
      agentToolCalls: []
    })
  
    try {
      console.log('[ChatStore] 开始发送Agent流式消息:', message.substring(0, 50))
      const eventSource = taskApi.sendAgentMessageStream(currentSessionId, message)
  
      eventSource.onopen = () => {
        console.log('[Agent Stream] 连接已建立')
      }
  
      eventSource.onmessage = (event: MessageEvent) => {
        try {
          const data: AgentStreamEvent = JSON.parse(event.data)
          console.log('[Agent Stream] 收到事件:', data.step, '进度:', data.progress)
            
          // 更新进度
          set({ agentProgress: data.progress })
            
          // 处理不同阶段的事件
          if (data.step === 'planning' && data.data?.plan) {
            console.log('[Agent Stream] 收到执行计划:', data.data.plan.length, '个步骤')
            set({ agentPlan: data.data.plan })
          } else if (data.step === 'tool_result' && data.data?.tool_result) {
            // 工具执行结果（注意：这里改为tool_result而不是tool_call）
            const toolCall = {
              tool_name: data.data.tool_result.tool_name || 'unknown',
              parameters: data.data.tool_result.parameters || {},
              result: data.data.tool_result.message || '',
              timestamp: Date.now(),
              success: data.data.tool_result.success || false
            }
            console.log('[Agent Stream] 工具调用结果:', toolCall.tool_name, toolCall.success)
            set({ agentToolCalls: [...get().agentToolCalls, toolCall] })
          } else if (data.step === 'completed' && data.data?.response) {
            console.log('[Agent Stream] 处理完成')
            const assistantMsg: ChatMessage = {
              role: 'assistant',
              content: data.data.response,
              created_at: new Date().toISOString()
            }
            set({
              messages: [...get().messages, assistantMsg],
              sending: false,
              agentStreaming: false,
              agentState: 'completed'
            })
            // 清理超时定时器
            if ((eventSource as any)._timeoutId) {
              clearTimeout((eventSource as any)._timeoutId)
            }
            eventSource.close()
          } else if (data.step === 'error') {
            console.error('[Agent Stream] 收到错误事件:', data.message)
            // 显示错误提示
            const errorMsg: ChatMessage = {
              role: 'assistant',
              content: `抱歉，Agent执行过程中出现错误: ${data.message}`,
              created_at: new Date().toISOString()
            }
            set({
              messages: [...get().messages, errorMsg],
              sending: false,
              agentStreaming: false,
              agentState: 'error'
            })
            // 清理超时定时器
            if ((eventSource as any)._timeoutId) {
              clearTimeout((eventSource as any)._timeoutId)
            }
            eventSource.close()
          }
        } catch (error) {
          console.error('[Agent Stream] 处理事件失败:', error)
          eventSource.close()
        }
      }
  
      eventSource.onerror = (error: Event) => {
        const readyState = eventSource.readyState
        const readyStateText = readyState === 0 ? 'CONNECTING' : readyState === 1 ? 'OPEN' : 'CLOSED'

        // 区分连接失败和执行过程中的错误
        if (readyState === 0) {
          console.error(
            '[Agent Stream] 连接建立失败 - readyState:',
            readyStateText,
            '(CONNECTING=0, OPEN=1, CLOSED=2)',
            '错误事件:',
            error
          )
        } else if (readyState === 1) {
          console.error(
            '[Agent Stream] 连接过程中出错 - readyState:',
            readyStateText,
            '错误事件:',
            error
          )
        } else {
          console.error(
            '[Agent Stream] 连接已关闭 - readyState:',
            readyStateText,
            '错误事件:',
            error
          )
        }

        // 只有在sending为true时才显示错误（避免重复显示）
        if (get().sending) {
          const errorMsg: ChatMessage = {
            role: 'assistant',
            content: '抱歉，Agent服务暂时不可用，请稍后再试。',
            created_at: new Date().toISOString()
          }
          set({
            messages: [...get().messages, errorMsg],
            sending: false,
            agentStreaming: false,
            agentState: 'error'
          })
        }
        // 清理超时定时器
        if ((eventSource as any)._timeoutId) {
          clearTimeout((eventSource as any)._timeoutId)
        }
        eventSource.close()
      }
    } catch (error) {
      console.error('[ChatStore] 发送Agent消息流失败:', error)
      const errorMsg: ChatMessage = {
        role: 'assistant',
        content: '抱歉，Agent服务暂时不可用，请稍后再试。',
        created_at: new Date().toISOString()
      }
      set({ 
        messages: [...get().messages, errorMsg], 
        sending: false,
        agentStreaming: false,
        agentState: 'error'
      })
    }
  },

  clearAgentState: () => {
    set({
      agentState: 'idle',
      agentPlan: [],
      agentToolCalls: [],
      agentProgress: 0,
      agentStreaming: false
    })
  }
}))
