import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { Task, TaskStatus, ReminderTask, CreateTaskResponse } from '../types/task'
import { taskApi } from '../api/taskApi'

interface TaskState {
  tasks: Task[]
  todayTasks: ReminderTask[]
  loading: boolean
  error: string | null
  lastFetchTime: number | null
  cacheTTL: number
  
  // 操作方法
  fetchTasks: (force?: boolean) => Promise<void>
  fetchTodayTasks: (force?: boolean) => Promise<void>
  createTask: (rawInput: string) => Promise<CreateTaskResponse>
  updateTask: (taskId: number, data: Partial<Task>) => Promise<void>
  updateTaskStatus: (taskId: number, status: TaskStatus) => Promise<void>
  updateTaskProgress: (taskId: number, progress: number) => Promise<void>
  updateSubTaskStatus: (taskId: number, subTaskIndex: number, completed: boolean) => Promise<void>
  deleteTask: (taskId: number) => Promise<void>
  clearError: () => void
  clearCache: () => void
}

// 缓存有效期：5分钟
const CACHE_TTL = 5 * 60 * 1000

export const useTaskStore = create<TaskState>()(
  persist(
    (set, get) => ({
      tasks: [],
      todayTasks: [],
      loading: false,
      error: null,
      lastFetchTime: null,
      cacheTTL: CACHE_TTL,

      fetchTasks: async (force = false) => {
        const { tasks, lastFetchTime, cacheTTL } = get()
        const now = Date.now()
        
        // 如果有缓存且未过期且不强制刷新，直接返回
        if (!force && tasks.length > 0 && lastFetchTime && (now - lastFetchTime < cacheTTL)) {
          return
        }

        set({ loading: true, error: null })
        try {
          const res = await taskApi.getTasks()
          set({ 
            tasks: res.data, 
            loading: false,
            lastFetchTime: now 
          })
        } catch (error) {
          set({ error: '获取任务失败', loading: false })
          console.error('获取任务失败:', error)
        }
      },

      fetchTodayTasks: async (force = false) => {
        const { lastFetchTime, cacheTTL } = get()
        const now = Date.now()
        
        // 如果有缓存且未过期且不强制刷新，直接返回
        if (!force && lastFetchTime && (now - lastFetchTime < cacheTTL)) {
          return
        }

        try {
          const res = await taskApi.getTodayReminders()
          set({ 
            todayTasks: res.data,
            lastFetchTime: now 
          })
        } catch (error) {
          console.error('获取今日任务失败:', error)
        }
      },

      createTask: async (rawInput) => {
        set({ loading: true, error: null })
        try {
          console.log('开始创建任务:', rawInput)
          const res = await taskApi.createTask({ raw_input: rawInput })
          const result = res.data
          console.log('创建任务成功:', result)
          if (result.success) {
            console.log('开始刷新任务列表')
            await get().fetchTasks(true) // 强制刷新
            await get().fetchTodayTasks(true)
            console.log('任务列表刷新完成')
          }
          return result
        } catch (error) {
          console.error('创建任务失败:', error)
          set({ error: '创建任务失败', loading: false })
          throw error
        } finally {
          set({ loading: false })
          console.log('创建任务操作完成')
        }
      },

      updateTask: async (taskId, data) => {
        set({ loading: true, error: null })
        try {
          await taskApi.updateTask(taskId, data)
          await get().fetchTasks(true)
          await get().fetchTodayTasks(true)
        } catch (error) {
          set({ error: '更新任务失败', loading: false })
          console.error('更新任务失败:', error)
        }
      },

      updateTaskStatus: async (taskId, status) => {
        set({ loading: true, error: null })
        try {
          await taskApi.updateTaskStatus(taskId, status)
          await get().fetchTasks(true)
          await get().fetchTodayTasks(true)
        } catch (error) {
          set({ error: '更新任务状态失败', loading: false })
          console.error('更新任务状态失败:', error)
        }
      },

      updateTaskProgress: async (taskId, progress) => {
        set({ loading: true, error: null })
        try {
          await taskApi.updateTaskProgress(taskId, progress)
          await get().fetchTasks(true)
        } catch (error) {
          set({ error: '更新任务进度失败', loading: false })
          console.error('更新任务进度失败:', error)
        }
      },

      updateSubTaskStatus: async (taskId, subTaskIndex, completed) => {
        set({ loading: true, error: null })
        try {
          await taskApi.updateSubTaskStatus(taskId, subTaskIndex, completed)
          await get().fetchTasks(true)
        } catch (error) {
          set({ error: '更新子任务状态失败', loading: false })
          console.error('更新子任务状态失败:', error)
        }
      },

      deleteTask: async (taskId) => {
        set({ loading: true, error: null })
        try {
          await taskApi.deleteTask(taskId)
          await get().fetchTasks(true)
          await get().fetchTodayTasks(true)
        } catch (error) {
          set({ error: '删除任务失败', loading: false })
          console.error('删除任务失败:', error)
        }
      },

      clearError: () => {
        set({ error: null })
      },

      clearCache: () => {
        set({ 
          tasks: [], 
          todayTasks: [], 
          lastFetchTime: null 
        })
      }
    }),
    {
      name: 'task-storage',
      storage: createJSONStorage(() => localStorage),
      // 只持久化需要的数据
      partialize: (state) => ({
        tasks: state.tasks,
        todayTasks: state.todayTasks,
        lastFetchTime: state.lastFetchTime
      })
    }
  )
)
