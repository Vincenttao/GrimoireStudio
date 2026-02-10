import { create } from 'zustand'

interface User {
  id: number
  email: string
}

interface ProjectMeta {
  id: number | null
  title: string | null
}

interface AppState {
  user: User | null
  projectMeta: ProjectMeta
  uiFlags: {
    isSidebarOpen: boolean
    isGenerating: boolean
  }
  setUser: (user: User | null) => void
  setProjectMeta: (meta: ProjectMeta) => void
  toggleSidebar: () => void
  setGenerating: (generating: boolean) => void
}

export const useAppStore = create<AppState>((set) => ({
  user: null,
  projectMeta: { id: null, title: null },
  uiFlags: {
    isSidebarOpen: true,
    isGenerating: false,
  },
  setUser: (user) => set({ user }),
  setProjectMeta: (projectMeta) => set({ projectMeta }),
  toggleSidebar: () => set((state) => ({ 
    uiFlags: { ...state.uiFlags, isSidebarOpen: !state.uiFlags.isSidebarOpen } 
  })),
  setGenerating: (isGenerating) => set((state) => ({ 
    uiFlags: { ...state.uiFlags, isGenerating } 
  })),
}))
