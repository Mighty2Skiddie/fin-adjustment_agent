import { lazy } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from '@/components/AppShell'
const AboutPage = lazy(() => import('@/pages/AboutPage'))
const AuditPage = lazy(() => import('@/pages/AuditPage'))
const EntryDetailPage = lazy(() => import('@/pages/EntryDetailPage'))
const EvalsPage = lazy(() => import('@/pages/EvalsPage'))
const HealthPage = lazy(() => import('@/pages/HealthPage'))
const LedgerPage = lazy(() => import('@/pages/LedgerPage'))
const NotFoundPage = lazy(() => import('@/pages/NotFoundPage'))
const QueuePage = lazy(() => import('@/pages/QueuePage'))

/** App routes. A run id of "latest" is resolved inside each page by useRunId(). */
export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/runs/latest/health" replace />} />
        <Route path="runs/:runId">
          <Route index element={<Navigate to="health" replace />} />
          <Route path="health" element={<HealthPage />} />
          <Route path="queue" element={<QueuePage />} />
          <Route path="entries/:jeId" element={<EntryDetailPage />} />
          <Route path="ledger" element={<LedgerPage />} />
          <Route path="audit" element={<AuditPage />} />
          <Route path="evals" element={<EvalsPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
        <Route path="about" element={<AboutPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
