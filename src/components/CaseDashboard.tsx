import { useEffect, useMemo, useState } from 'react'
import { getCase, listDocs, resolvePublicUrl } from '../services/api'
import { useStore } from '../store'
import type { DocumentItem } from '../store'

const STAGE_ORDER = [
  { id: 'awaiting_case_start', label: 'Kickoff' },
  { id: 'awaiting_case_details', label: 'Case Details' },
  { id: 'awaiting_procedure_documents', label: 'Eligibility Review' },
  { id: 'awaiting_resolution_choice', label: 'Resolve Issues' },
  { id: 'awaiting_additional_documentation', label: 'Supporting Docs' },
  { id: 'rcm_review_pending', label: 'RCM Review' },
  { id: 'awaiting_rcm_user_confirmation', label: 'RCM Confirmation' },
  { id: 'awaiting_final_confirmation', label: 'Finalize Plan' },
  { id: 'awaiting_signed_soap_note', label: 'Signature' },
  { id: 'completed', label: 'Ready to Submit' },
]

export default function CaseDashboard({ caseId }: { caseId: string }) {
  const { setDocuments, documents, cases } = useStore()
  const [theCase, setTheCase] = useState<any>(null)
  const docs = documents[caseId] || []

  const formatLabel = (value?: string | null) => {
    if (!value) return '—'
    return value
      .split('_')
      .map(part => part ? part[0].toUpperCase() + part.slice(1) : part)
      .join(' ')
  }

  useEffect(() => {
    getCase(caseId).then(setTheCase).catch(err => {
      console.error('Failed to load case', err)
      alert('Failed to load case. Please try again later.')
    })
    listDocs(caseId).then(d => setDocuments(caseId, d)).catch(err => {
      console.error('Failed to load documents', err)
      alert('Failed to load documents. Please try again later.')
    })
  }, [caseId, setDocuments])

  useEffect(() => {
    const match = cases.find(c => c.case_id === caseId)
    if (match) {
      setTheCase(match)
    }
  }, [caseId, cases])

  const stageTimeline = useMemo(() => {
    const current = theCase?.workflow_stage
    const idx = STAGE_ORDER.findIndex(step => step.id === current)
    return STAGE_ORDER.map((step, stepIndex) => {
      const status = idx === -1 ? 'upcoming' : stepIndex < idx ? 'done' : stepIndex === idx ? 'current' : 'upcoming'
      return { ...step, status }
    })
  }, [theCase?.workflow_stage])

  const openDocument = (doc: DocumentItem) => {
    let candidate = ''
    if (doc.public_url) {
      candidate = doc.public_url
    } else if (doc.path && (doc.path.startsWith('/uploads') || doc.path.startsWith('http'))) {
      candidate = doc.path
    }

    if (!candidate) {
      alert('Document URL is unavailable. Please refresh and try again.')
      return
    }

    const url = resolvePublicUrl(candidate)
    window.open(url, '_blank', 'noopener,noreferrer')
  }

  if (!theCase) return <div className="p-6 text-gray-500">Loading…</div>

  return (
    <div className="flex h-full min-h-0 flex-col gap-6 overflow-hidden text-slate-100">
      <header className="flex flex-col gap-4 rounded-3xl border border-white/5 bg-white/5 p-6 shadow-inner">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.35em] text-emerald-200/70">Active Case</p>
            <h1 className="mt-2 text-2xl font-semibold text-white">{theCase.title}</h1>
            <p className="text-sm text-slate-300">Case ID • {theCase.case_id}</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <span className="rounded-full border border-emerald-400/40 bg-emerald-400/10 px-3 py-1 text-sm font-medium text-emerald-100">{theCase.status || 'New'}</span>
            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-200">{theCase.patient_name || 'Patient TBD'}</span>
            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-200">{theCase.payer || 'Payer TBD'}</span>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-2xl border border-white/10 bg-slate-950/40 p-4">
            <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Workflow Stage</p>
            <p className="mt-2 text-lg font-semibold text-white">{formatLabel(theCase.workflow_stage)}</p>
            <p className="mt-1 text-xs text-slate-300">{theCase.workflow_status || '—'}</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-slate-950/40 p-4">
            <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Next Action</p>
            <p className="mt-2 text-sm text-slate-200">{theCase.next_action || 'Proceed via chat to view guidance.'}</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-emerald-400/25 to-sky-500/10 p-4">
            <p className="text-xs uppercase tracking-[0.25em] text-emerald-100/80">Projected Reimbursement</p>
            <p className="mt-2 text-2xl font-semibold text-white">{theCase.reimbursement_amount != null ? `$${theCase.reimbursement_amount.toLocaleString()}` : '—'}</p>
            <p className="mt-1 text-xs text-emerald-100/80">{theCase.reimbursement_date || 'Pending eligibility checks'}</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-slate-950/40 p-4">
            <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Risk Level</p>
            <p className="mt-2 text-xl font-semibold text-white">{theCase.risk_level || '—'}</p>
            <p className="mt-1 text-xs text-slate-300">Risk adjusts as documentation is resolved.</p>
          </div>
        </div>
      </header>

      <section className="grid flex-1 min-h-0 grid-cols-1 gap-6 overflow-hidden xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        <div className="flex min-h-0 flex-col gap-6 overflow-hidden">
          <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white">Workflow Timeline</h2>
              <span className="text-xs text-slate-300">Track where the case sits</span>
            </div>
            <ol className="mt-5 space-y-3">
              {stageTimeline.map(step => {
                const orderNumber = STAGE_ORDER.findIndex(s => s.id === step.id) + 1
                return (
                  <li key={step.id} className={`flex items-center gap-3 rounded-2xl border px-3 py-3 text-sm transition ${step.status === 'current' ? 'border-emerald-400/60 bg-emerald-400/10 text-emerald-100' : step.status === 'done' ? 'border-white/15 bg-white/5 text-slate-200' : 'border-transparent bg-white/0 text-slate-400'}`}>
                    <span className={`flex h-8 w-8 items-center justify-center rounded-full border text-xs font-semibold ${step.status === 'done' ? 'border-emerald-400/60 bg-emerald-400/20 text-emerald-100' : step.status === 'current' ? 'border-emerald-400/80 bg-emerald-400/30 text-white' : 'border-white/10 bg-white/5 text-slate-300'}`}>
                      {step.status === 'done' ? '✓' : step.status === 'current' ? '•' : orderNumber}
                    </span>
                    <div className="flex-1">
                      <p className="font-medium">{step.label}</p>
                      <p className="text-xs text-slate-300">{step.status === 'current' ? 'In progress' : step.status === 'done' ? 'Completed' : 'Upcoming'}</p>
                    </div>
                  </li>
                )
              })}
            </ol>
          </div>

          <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
            <h2 className="text-lg font-semibold text-white">Case Summary</h2>
            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-xs text-slate-400">Eligibility</p>
                <p className="mt-1 text-sm text-slate-200">{theCase.workflow_stage && theCase.workflow_stage.includes('eligibility') ? 'Running checks' : 'Completed via last Medicare sync'}</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-xs text-slate-400">Documentation</p>
                <p className="mt-1 text-sm text-slate-200">Latest upload updates automatically within the chat flow.</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-xs text-slate-400">RCM Expert</p>
                <p className="mt-1 text-sm text-slate-200">Mila receives cases automatically when duplicate risk is detected.</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-xs text-slate-400">Signatures</p>
                <p className="mt-1 text-sm text-slate-200">Signed SOAP uploads are monitored from the chat panel.</p>
              </div>
            </div>
          </div>
        </div>

        <div className="flex min-h-0 flex-col rounded-3xl border border-white/10 bg-white/5 p-6">
          <div className="flex items-center justify-between gap-4">
            <h2 className="text-lg font-semibold text-white">Documents</h2>
            <span className="text-xs text-slate-400">Upload new files directly from the chat when prompted.</span>
          </div>
          <div className="mt-4 flex-1 min-h-0 overflow-hidden">
            <ul className="grid h-full grid-cols-1 gap-3 overflow-y-auto pr-1 sm:grid-cols-2">
              {docs.length === 0 && (
                <li className="rounded-2xl border border-dashed border-white/15 bg-slate-950/40 p-6 text-center text-sm text-slate-300">
                  No documents uploaded yet.
                </li>
              )}
              {docs.map(d => (
                <li key={d.doc_id} className="rounded-2xl border border-white/10 bg-slate-950/40 p-4">
                  <div className="space-y-2 text-sm">
                    <p className="font-medium text-white truncate" title={d.name}>{d.name}</p>
                    <p className="text-xs text-slate-300">{d.type || 'file'}</p>
                    <p className="text-xs text-slate-400">{new Date(d.uploaded_at).toLocaleString()}</p>
                  </div>
                  <button className="mt-3 inline-flex w-full items-center justify-center rounded-full border border-white/15 px-3 py-1 text-xs text-emerald-200 transition hover:border-emerald-400/60 hover:text-white" onClick={() => openDocument(d)}>View document</button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>
    </div>
  )
}
