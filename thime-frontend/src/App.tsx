import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Authenticator } from '@aws-amplify/ui-react'
import '@aws-amplify/ui-react/styles.css'

import { useAuthStore } from '@/stores/authStore'
import { AppShell } from '@/components/layout/AppShell'
import { HomePage } from '@/pages/HomePage'
import { RecordsPage } from '@/pages/RecordsPage'
import { RecordDetailPage } from '@/pages/RecordDetailPage'
import { FeedsPage } from '@/pages/FeedsPage'
import { InboxPage } from '@/pages/InboxPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60,     // 1분
      retry: 1,
    },
  },
})

function AuthenticatedApp() {
  const fetchUser = useAuthStore((s) => s.fetchUser)
  useEffect(() => { fetchUser() }, [fetchUser])

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<HomePage />} />
            <Route path="records" element={<RecordsPage />} />
            <Route path="records/:id" element={<RecordDetailPage />} />
            <Route path="feeds" element={<FeedsPage />} />
            <Route path="inbox" element={<InboxPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default function App() {
  return (
    <Authenticator
      loginMechanisms={['email']}
      signUpAttributes={['email']}
      components={{
        Header() {
          return (
            <div className="text-center py-8">
              <p className="text-4xl mb-2">🌙</p>
              <h1 className="text-2xl font-bold text-night-50">Thime</h1>
              <p className="text-night-400 text-sm mt-1">생각하는 시간</p>
            </div>
          )
        },
      }}
    >
      <AuthenticatedApp />
    </Authenticator>
  )
}
