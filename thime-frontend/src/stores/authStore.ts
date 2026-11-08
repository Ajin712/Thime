import { create } from 'zustand'
import { getCurrentUser, signOut } from 'aws-amplify/auth'

interface AuthState {
  userId: string | null
  email: string | null
  isLoading: boolean
  fetchUser: () => Promise<void>
  logout: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  userId: null,
  email: null,
  isLoading: true,

  fetchUser: async () => {
    try {
      const user = await getCurrentUser()
      set({ userId: user.userId, email: user.signInDetails?.loginId ?? null, isLoading: false })
    } catch {
      set({ userId: null, email: null, isLoading: false })
    }
  },

  logout: async () => {
    await signOut()
    set({ userId: null, email: null })
  },
}))
