import { Outlet } from 'react-router-dom'
import SidebarCases from '../components/SidebarCases'
import CaseChatPanel from '../components/CaseChatPanel'

export default function AppShell() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-slate-950 text-slate-100">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(56,189,248,0.28)_0,rgba(10,15,29,0.7)_45%,rgba(2,6,23,0.95)_80%)]" />
      <div className="pointer-events-none absolute inset-y-0 left-1/2 h-[120%] w-[40rem] -translate-x-1/2 rounded-full bg-[radial-gradient(circle,rgba(52,211,153,0.18),rgba(12,74,110,0))] blur-3xl" />

      <div className="relative z-10 flex min-h-screen flex-col">
        <header className="sticky top-0 z-20 border-b border-white/10 bg-slate-950/80 backdrop-blur">
          <div className="mx-auto flex h-16 w-full max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
            <div className="flex items-center gap-3">
              <div className="group relative h-10 w-10 rounded-2xl bg-gradient-to-br from-emerald-400 via-sky-500 to-blue-600 p-[1px] shadow-lg shadow-emerald-500/30">
                <div className="flex h-full w-full items-center justify-center rounded-[1rem] bg-slate-950 text-lg font-semibold text-white">A</div>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.45em] text-emerald-200/70">Amdal RCM</p>
                <p className="text-lg font-semibold text-white">Case Command Center</p>
              </div>
            </div>

            <nav className="flex items-center gap-6 text-sm text-slate-300">
              <a className="transition hover:text-white" href="https://github.com/rdev/liquid-glass-react" target="_blank" rel="noreferrer">Design Kit</a>
              <a className="transition hover:text-white" href="https://tailwindcss.com" target="_blank" rel="noreferrer">Tailwind</a>
              <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-emerald-200">
                <span className="h-2 w-2 rounded-full bg-emerald-400" />
                Live sync
              </div>
            </nav>
          </div>
        </header>

        <div className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-6 px-4 py-6 sm:px-6">
          <div className="grid flex-1 grid-cols-1 gap-6 lg:grid-cols-[320px_minmax(0,1fr)] xl:grid-cols-[340px_minmax(0,1fr)]">
            <aside className="flex h-full flex-col rounded-3xl border border-white/10 bg-white/5 shadow-[0_25px_70px_rgba(8,47,73,0.35)] backdrop-blur">
              <SidebarCases />
            </aside>

            <main className="flex h-full flex-col overflow-hidden rounded-3xl border border-white/10 bg-slate-900/55 shadow-[0_25px_70px_rgba(15,23,42,0.45)] backdrop-blur">
              <div className="flex-1 overflow-hidden">
                <div className="h-full overflow-y-auto px-4 py-6 sm:px-8">
                  <Outlet/>
                </div>
              </div>
            </main>
          </div>

          <section className="flex h-[360px] flex-col rounded-3xl border border-white/10 bg-slate-900/55 shadow-[0_25px_70px_rgba(15,23,42,0.45)] backdrop-blur lg:h-[400px]">
            <CaseChatPanel/>
          </section>
        </div>
      </div>
    </div>
  )
}
