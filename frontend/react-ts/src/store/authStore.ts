import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { taskApi } from '../api/taskApi'
import { LoginRequest, RegisterRequest } from '../types/task'

interface AuthState {
  user: any | null
  token: string | null
  isAuthenticated: boolean
  
  login: (data: LoginRequest) => Promise<void>
  register: (data: RegisterRequest) => Promise<void>
  logout: () => void
  initAuth: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      initAuth: () => {
        // persist 中间件已经处理了初始化，这里可以留空或做其他处理
      },

      login: async (data: LoginRequest) => {
        try {
          const res = await taskApi.login(data)
          set({
            token: res.data.access_token,
            user: res.data.user,
            isAuthenticated: true
          })
        } catch (error) {
          console.error('登录失败:', error)
          throw error
        }
      },

      register: async (data: RegisterRequest) => {
        try {
          await taskApi.register(data)
        } catch (error) {
          console.error('注册失败:', error)
          throw error
        }
      },

      logout: () => {
        set({ user: null, token: null, isAuthenticated: false })
      }
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated
      })
    }
  )
)
