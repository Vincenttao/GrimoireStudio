import React, { useState } from 'react'
import GrimoireEditor from './components/editor/GrimoireEditor'
import AuthPage from './components/auth/AuthPage'
import Dashboard from './components/dashboard/Dashboard'
import { useAppStore } from './store/appStore'

function App() {
  const user = useAppStore((state) => state.user)
  const [currentView, setCurrentView] = useState<'dashboard' | 'editor'>('dashboard')
  const [activeProjectId, setActiveProjectId] = useState<number | null>(null)

  const handleSelectProject = (id: number) => {
    setActiveProjectId(id)
    setCurrentView('editor')
  }

  const handleBackToDashboard = () => {
    setCurrentView('dashboard')
    setActiveProjectId(null)
  }

  if (!user) {
    return <AuthPage />
  }

  return (
    <>
      {currentView === 'dashboard' && <Dashboard onSelectProject={handleSelectProject} />}
      {currentView === 'editor' && <GrimoireEditor onBack={handleBackToDashboard} />}
    </>
  )
}

export default App