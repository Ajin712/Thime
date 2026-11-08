import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@/lib/amplify'   // Amplify 설정 — 최초 임포트
import '@/index.css'
import App from '@/App'

const root = document.getElementById('root')
if (!root) throw new Error('#root element not found')

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
