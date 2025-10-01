import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useStore } from '../store'
import { listCases, createCase, deleteCase } from '../services/api'

const friendlyLabel = (value?: string | null) => {
  if (!value) return '—'
  return value
    .replace(/_/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/(^|\s)\S/g, (s) => s.toUpperCase())
}

export default function SidebarCases({ onCollapsedToggle }: { onCollapsedToggle?: () => void }) {
  const { cases, setCases, setDocuments, setMessages } = useStore()
  const [query, setQuery] = useState('')
  const [newTitle, setNewTitle] = useState('')
  const navigate = useNavigate()
  const { pathname } = useLocation()

  useEffect(() => {
    listCases().then(setCases).catch(err => {
      console.error('Failed to load cases', err)
      alert('Failed to load cases. Please try again later.')
    })
  }, [setCases])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return cases
    return cases.filter(c =>
      c.title.toLowerCase().includes(q) ||
      (c.patient_name || '').toLowerCase().includes(q) ||
      (c.workflow_stage || '').toLowerCase().includes(q),
    )
  }, [cases, query])

  const create = async () => {
    const title = (newTitle || `New Case ${Math.random().toString(36).slice(2,6).toUpperCase()}`).trim()
    if (!title) return
    try {
      const created = await createCase({ title })
      const refreshed = await listCases()
      setCases(refreshed)
      navigate(`/cases/${created.case_id}`)
      setNewTitle('')
    } catch (err) {
      console.error('Failed to create case', err)
      alert('Failed to create case. Please try again later.')
    }
  }

  const remove = async (caseId: string, title: string) => {
    const ok = confirm(`Delete case "${title}"? This will remove all related chat history and documents.`)
    if (!ok) return
    try {
      await deleteCase(caseId)
      setMessages(caseId, [])
      setDocuments(caseId, [])
      const refreshed = await listCases()
      setCases(refreshed)
      if (pathname.includes(caseId)) {
        navigate('/')
      }
    } catch (err) {
      console.error('Failed to delete case', err)
      alert('Failed to delete case. Please try again later.')
    }
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="border-b border-white/10 px-6 py-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[0.65rem] uppercase tracking-[0.35em] text-emerald-200/70">Pipeline</p>
            <h2 className="text-xl font-semibold text-white">Case Queue</h2>
          </div>
          <div className="flex items-center gap-2">
            {onCollapsedToggle && (
              <button
                onClick={onCollapsedToggle}
                className="flex h-8 w-8 items-center justify-center rounded-full border border-white/15 bg-white/5 text-slate-300 transition hover:border-emerald-400/50 hover:text-white"
                aria-label="Collapse case queue"
              >
                <i className="fa-solid fa-chevron-left" />
              </button>
            )}
          </div>
        </div>
        <div className="mt-4 space-y-2">
          <label className="group flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-300 focus-within:border-emerald-400/60 focus-within:text-white">
            <svg className="h-4 w-4 text-emerald-300/80" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-4.35-4.35M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14Z" />
            </svg>
            <input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search by patient, payer, or status…" className="h-6 w-full bg-transparent text-sm text-white placeholder:text-slate-400 focus:outline-none" />
          </label>
          <div className="flex items-center gap-2">
            <label className="group flex-1 flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-300 focus-within:border-emerald-400/60 focus-within:text-white">
              <svg className="h-4 w-4 text-emerald-300/80" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              <input
                value={newTitle}
                onChange={e=>setNewTitle(e.target.value)}
                onKeyDown={(e)=>{ if(e.key==='Enter'){ e.preventDefault(); create(); }}}
                placeholder="Enter patient name (optional)"
                className="h-6 w-full bg-transparent text-sm text-white placeholder:text-slate-400 focus:outline-none"
              />
            </label>
            <button onClick={create} className="rounded-full border border-emerald-400/40 bg-emerald-400/10 px-4 py-2 text-sm font-medium text-emerald-200 transition hover:bg-emerald-400/20 hover:text-white">New Case</button>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-5">
        <div className="space-y-3">
          {filtered.map(c => {
            const isActive = pathname.includes(c.case_id)
            return (
              <button
                key={c.case_id}
                onClick={() => navigate(`/cases/${c.case_id}`)}
                className={`group w-full rounded-2xl border px-4 py-4 text-left transition ${isActive ? 'border-emerald-400/70 bg-emerald-400/10 shadow-[0_15px_35px_rgba(16,185,129,0.25)]' : 'border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10'}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-white">{c.title}</p>
                    <p className="mt-1 text-xs text-slate-300">{c.patient_name || 'No patient yet'}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`rounded-full px-2 py-1 text-[0.65rem] font-semibold uppercase tracking-wide ${isActive ? 'bg-emerald-400/20 text-emerald-100' : 'bg-white/5 text-slate-200'}`}>{friendlyLabel(c.status) || 'New'}</span>
                    <button
                      onClick={(event) => {
                        event.stopPropagation()
                        remove(c.case_id, c.title)
                      }}
                      className="rounded-full border border-transparent p-1 text-xs text-slate-300 opacity-0 transition group-hover:opacity-100 hover:border-red-400/60 hover:text-red-200"
                      title="Delete case"
                    >
                      ✕
                    </button>
                  </div>
                </div>
                <div className="mt-4 flex items-center justify-between text-xs text-slate-300">
                  <div className="flex items-center gap-2">
                    <span className="inline-flex h-2 w-2 rounded-full bg-emerald-400/80" />
                    {friendlyLabel(c.workflow_stage) || 'Awaiting kickoff'}
                  </div>
                  <div className="text-right">
                    <p className="font-semibold text-slate-100">{c.reimbursement_amount != null ? `$${c.reimbursement_amount.toLocaleString()}` : '—'}</p>
                    <p className="text-[0.65rem] text-slate-400">{c.reimbursement_date || 'Projected timeline pending'}</p>
                  </div>
                </div>
              </button>
            )
          })}

          {filtered.length === 0 && (
            <div className="rounded-2xl border border-dashed border-white/15 bg-white/5 p-6 text-center text-sm text-slate-300">
              No cases match that search just yet.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
