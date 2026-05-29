import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Menu } from 'lucide-react'
import { Sidebar } from '@/components/layout/Sidebar'

export function MainLayout() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false)

  return (
    <div className="flex h-full overflow-hidden bg-graphite-50">
      {mobileNavOpen ? (
        <button
          type="button"
          aria-label="Fechar menu"
          className="fixed inset-0 z-40 bg-graphite-900/40 backdrop-blur-[1px] lg:hidden"
          onClick={() => setMobileNavOpen(false)}
        />
      ) : null}

      <Sidebar
        mobileOpen={mobileNavOpen}
        onMobileClose={() => setMobileNavOpen(false)}
      />

      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <header
          data-app-no-drag
          className="sticky top-0 z-30 flex shrink-0 items-center gap-3 border-b border-graphite-200 bg-white/95 px-4 py-3 backdrop-blur-sm sm:px-6 lg:px-8"
        >
          <button
            type="button"
            data-app-no-drag
            aria-label="Abrir menu"
            className="inline-flex cursor-pointer items-center justify-center rounded-lg border border-graphite-200 p-2 text-graphite-600 transition-colors hover:bg-graphite-50 lg:hidden"
            onClick={() => setMobileNavOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </button>
          <p className="text-xs font-medium uppercase tracking-wide text-graphite-500">
            OAE Report Generator
          </p>
        </header>

        <main
          data-app-no-drag
          className="flex min-h-0 min-w-0 flex-1 flex-col overflow-y-auto overflow-x-hidden scrollbar-thin"
        >
          <Outlet />
        </main>
      </div>
    </div>
  )
}
