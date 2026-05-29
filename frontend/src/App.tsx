import { useEffect, useState } from 'react'
import { BrowserRouter, HashRouter, Navigate, Route, Routes } from 'react-router-dom'
import { MainLayout } from '@/layouts/MainLayout'
import { DashboardPage } from '@/pages/DashboardPage'
import { ManagementPage } from '@/pages/ManagementPage'
import { PhotoLayoutPage } from '@/pages/PhotoLayoutPage'
import { ProcessingPage } from '@/pages/ProcessingPage'
import { ProjectFormPage } from '@/pages/ProjectFormPage'
import { ReportCompletePage } from '@/pages/ReportCompletePage'
import { ValidationPage } from '@/pages/ValidationPage'
import { useProjectStore } from '@/store/project-store'

const Router = window.electronAPI?.isDesktop ? HashRouter : BrowserRouter
const isDesktop = Boolean(window.electronAPI?.isDesktop)

export default function App() {
  const [storeReady, setStoreReady] = useState(() => useProjectStore.persist.hasHydrated())

  useEffect(() => {
    if (isDesktop) {
      document.body.classList.add('electron-desktop')
    }
    return () => {
      if (isDesktop) {
        document.body.classList.remove('electron-desktop')
      }
    }
  }, [])

  useEffect(() => {
    if (useProjectStore.persist.hasHydrated()) {
      setStoreReady(true)
      return
    }
    return useProjectStore.persist.onFinishHydration(() => setStoreReady(true))
  }, [])

  if (!storeReady) {
    return null
  }

  return (
    <Router>
      <Routes>
        <Route element={<MainLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="obras/:projectId" element={<ProjectFormPage />} />
          <Route path="obras/:projectId/validacao" element={<ValidationPage />} />
          <Route path="obras/:projectId/fotos" element={<PhotoLayoutPage />} />
          <Route path="obras/:projectId/processamento" element={<ProcessingPage />} />
          <Route path="template" element={<Navigate to="/gerenciamento" replace />} />
          <Route path="gerenciamento" element={<ManagementPage />} />
          <Route path="obras/:projectId/concluido" element={<ReportCompletePage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </Router>
  )
}
