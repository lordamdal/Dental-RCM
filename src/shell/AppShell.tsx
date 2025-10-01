import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import SidebarCases from '../components/SidebarCases'
import CaseChatPanel from '../components/CaseChatPanel'

export default function AppShell() {
  const [queueVisible, setQueueVisible] = useState(true)

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
                <p className="text-xs uppercase tracking-[0.45em] text-emerald-200/70">Dental RCM</p>
                <p className="text-lg font-semibold text-white">Case Command Center</p>
              </div>
            </div>

            <div className="flex items-center gap-3 text-xs text-emerald-200">
              <button
                onClick={() => setQueueVisible(v => !v)}
                className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-slate-200 transition hover:border-emerald-400/60 hover:text-white"
              >
                <span className={`inline-flex h-2 w-2 rounded-full ${queueVisible ? 'bg-emerald-400' : 'bg-slate-500'}`} />
                {queueVisible ? 'Hide queue' : 'Show queue'}
              </button>
            </div>
          </div>
        </header>

        <div className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6">
          <div className="grid h-full grid-rows-[minmax(0,1fr)_auto] gap-6">
            <div className={`grid min-h-0 gap-6 ${queueVisible ? 'grid-cols-1 lg:grid-cols-[300px_minmax(0,1fr)] xl:grid-cols-[320px_minmax(0,1fr)]' : 'grid-cols-1'}`}>
              {queueVisible && (
                <aside className="flex min-h-0 flex-col overflow-hidden rounded-3xl border border-white/10 bg-white/5 shadow-[0_25px_70px_rgba(8,47,73,0.35)] backdrop-blur">
                  <SidebarCases onCollapsedToggle={() => setQueueVisible(false)} />
                </aside>
              )}

              <main className="flex min-h-0 flex-col overflow-hidden rounded-3xl border border-white/10 bg-slate-900/60 shadow-[0_25px_70px_rgba(15,23,42,0.45)] backdrop-blur">
                <div className="flex-1 min-h-0 overflow-hidden px-4 py-5 sm:px-8">
                  <div className="h-full min-h-0 overflow-hidden">
                    <Outlet/>
                  </div>
                </div>
              </main>
            </div>

            <section className="h-[660px] rounded-3xl border border-white/10 bg-slate-900/60 shadow-[0_25px_70px_rgba(15,23,42,0.45)] backdrop-blur lg:h-[480px] xl:h-[600px]">
              <CaseChatPanel/>
            </section>
          </div>
        </div>
        {!queueVisible && (
          <button
            onClick={() => setQueueVisible(true)}
            className="fixed left-4 top-1/2 z-40 flex h-10 w-10 -translate-y-1/2 items-center justify-center rounded-full border border-white/20 bg-slate-900/80 text-white shadow-lg backdrop-blur hover:border-emerald-400/60"
            aria-label="Show case queue"
          >
            <i className="fa-solid fa-chevron-right" />
          </button>
        )}
      </div>
    </div>
  )
}
