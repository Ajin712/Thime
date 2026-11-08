import { NavLink, Outlet } from 'react-router-dom'
import { clsx } from 'clsx'

const NAV = [
  { to: '/',        label: '홈',    icon: '🌙' },
  { to: '/records', label: '기록',  icon: '📝' },
  { to: '/feeds',   label: '생각들', icon: '💬' },
  { to: '/inbox',   label: '편지함', icon: '✉️'  },
]

export function AppShell() {
  return (
    <div className="min-h-screen bg-night-800 text-night-50 flex flex-col max-w-md mx-auto relative">
      {/* 배경 그라데이션 */}
      <div className="fixed inset-0 max-w-md mx-auto pointer-events-none">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-96 bg-brand-500/10 rounded-full blur-3xl" />
      </div>

      {/* 콘텐츠 영역 */}
      <main className="flex-1 overflow-y-auto pb-20 px-4 pt-6 relative z-10">
        <Outlet />
      </main>

      {/* 하단 내비게이션 */}
      <nav
        className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-md bg-night-800/90 backdrop-blur-xl border-t border-night-700 z-50"
        aria-label="메인 내비게이션"
      >
        <ul className="flex">
          {NAV.map(({ to, label, icon }) => (
            <li key={to} className="flex-1">
              <NavLink
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  clsx(
                    'flex flex-col items-center gap-1 py-3 text-xs font-medium transition-colors',
                    isActive ? 'text-brand-400' : 'text-night-400 hover:text-night-200',
                  )
                }
                aria-label={label}
              >
                <span className="text-xl leading-none" aria-hidden>{icon}</span>
                <span>{label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  )
}
