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

// Cross-browser safe date parsing and formatting
const parseDate = (value?: string) => {
  if (!value) return undefined
  let d = new Date(value)
  if (isNaN(d.getTime())) {
    const cleaned = value.replace(/\.(\d{3})\d+/, '.$1').replace(/\..*?(Z|[+-]\d{2}:?\d{2})$/, '$1')
    d = new Date(cleaned)
  }
  return isNaN(d.getTime()) ? undefined : d
}

const fmtDate = (value?: string) => {
  const d = parseDate(value)
  return d ? d.toLocaleString() : '—'
}

export default function CaseDashboard({ caseId }: { caseId: string }) {
  const { setDocuments, documents, cases } = useStore()
  const [theCase, setTheCase] = useState<any>(null)
  const [activeTab, setActiveTab] = useState<'overview' | 'timeline'>('overview')
  const docs = documents[caseId] || []

  const uploadedDocs = useMemo(() => {
    const list = docs.filter(d => !((d.type || '').startsWith('generated')))
    return list.sort((a, b) => new Date(b.uploaded_at).getTime() - new Date(a.uploaded_at).getTime())
  }, [docs])

  const generatedDocs = useMemo(() => {
    const list = docs.filter(d => (d.type || '').startsWith('generated'))
    return list.sort((a, b) => new Date(b.uploaded_at).getTime() - new Date(a.uploaded_at).getTime())
  }, [docs])

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
    <div className="grid h-full min-h-0 grid-rows-[minmax(0,1fr)_auto] gap-5 text-slate-100">
      <div className="flex min-h-0 flex-col rounded-3xl border border-white/5 bg-white/5 p-6 shadow-inner">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.35em] text-emerald-200/70">Active Case</p>
            <h1 className="mt-2 text-2xl font-semibold text-white">{theCase.title}</h1>
            <p className="text-sm text-slate-300">Case ID • {theCase.case_id}</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <span className="rounded-full border border-emerald-400/40 bg-emerald-400/10 px-3 py-1 text-sm font-medium text-emerald-100">{theCase.status || 'New'}</span>
            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-200">Patient • {theCase.patient_name || 'TBD'}</span>
            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-200">Payer • {theCase.payer || 'TBD'}</span>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-4">
          <div className="flex rounded-full border border-white/10 bg-slate-900/40 p-1 text-xs">
            {(['overview', 'timeline'] as const).map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`rounded-full px-4 py-1.5 font-semibold transition ${activeTab === tab ? 'bg-emerald-400/80 text-slate-900' : 'text-slate-300 hover:text-white'}`}
              >
                {tab === 'overview' ? 'Overview' : 'Timeline'}
              </button>
            ))}
          </div>
          <div className="flex max-w-md items-center gap-3 rounded-2xl border border-emerald-400/30 bg-emerald-400/10 px-4 py-3 text-xs text-emerald-50">
            <span className="inline-flex h-2 w-2 rounded-full bg-emerald-300" />
            <div className="leading-tight">
              <p className="text-[0.6rem] uppercase tracking-[0.3em] text-emerald-200/80">Next Action</p>
              <p className="text-sm font-medium text-white">{theCase.next_action || 'Use the chat to advance the workflow.'}</p>
            </div>
          </div>
        </div>

        <div className="mt-4 flex-1 min-h-0 overflow-hidden">
          {activeTab === 'overview' ? (
            <div className="grid h-full grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
              <StatCard label="Workflow Stage" value={formatLabel(theCase.workflow_stage)} tone="slate" />
              <StatCard label="Projected Reimbursement" value={theCase.reimbursement_amount != null ? `$${theCase.reimbursement_amount.toLocaleString()}` : '—'} helper={theCase.reimbursement_date || ''} tone="emerald" />
              <StatCard label="Risk Level" value={theCase.risk_level || '—'} tone="slate" />
              <StatCard label="Created" value={parseDate(theCase.created_at)?.toLocaleDateString() || '—'} helper={`Updated ${parseDate(theCase.updated_at)?.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) || '—'}`} tone="slate" />

              <InfoCard title="Patient Profile" items={[
                { label: 'Patient', value: theCase.patient_name || '—' },
                { label: 'Payer', value: theCase.payer || '—' },
                { label: 'Status', value: theCase.status || 'New' },
              ]} />

              <InfoCard title="Submission Prep" items={[
                { label: 'Docs Uploaded', value: docs.length ? `${docs.length} files` : 'Awaiting uploads' },
                { label: 'RCM Review', value: formatLabel(theCase.workflow_stage).includes('RCM') ? 'In progress' : 'On standby' },
                { label: 'Signature', value: theCase.workflow_stage === 'awaiting_signed_soap_note' ? 'Pending upload' : 'Not requested' },
              ]} />
            </div>
          ) : (
            <div className="grid h-full grid-cols-2 gap-3 overflow-y-auto pr-2">
              {stageTimeline.map((step, index) => (
                <div
                  key={step.id}
                  className={`flex items-center gap-3 rounded-2xl border px-3 py-3 text-sm transition ${step.status === 'current' ? 'border-emerald-400/60 bg-emerald-400/15 text-emerald-50' : step.status === 'done' ? 'border-emerald-300/30 bg-emerald-300/10 text-emerald-100' : 'border-white/10 bg-white/5 text-slate-300'}`}
                >
                  <span className={`flex h-8 w-8 items-center justify-center rounded-full border text-xs font-semibold ${step.status === 'done' ? 'border-emerald-300/60 bg-emerald-300/20 text-emerald-900' : step.status === 'current' ? 'border-emerald-400/80 bg-emerald-400/30 text-white' : 'border-white/15 bg-white/10 text-slate-400'}`}>
                    {step.status === 'done' ? '✓' : index + 1}
                  </span>
                  <div>
                    <p className="font-medium">{step.label}</p>
                    <p className="text-[0.65rem] uppercase tracking-[0.2em] text-slate-400">{step.status === 'current' ? 'In progress' : step.status === 'done' ? 'Completed' : 'Upcoming'}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="flex min-h-0 flex-col rounded-3xl border border-white/10 bg-white/5 p-6">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-white">Documents</h2>
          <span className="text-xs text-slate-400">Tap a document title to open it.</span>
        </div>
        <div className="mt-4 flex-1 min-h-0 overflow-hidden">
          <div className="h-full overflow-y-auto pr-2 space-y-4">
            <DocumentGroup
              title="Uploaded Documents"
              docs={uploadedDocs}
              emptyLabel="No uploaded files yet."
              onOpen={openDocument}
              variant="uploaded"
            />
            <DocumentGroup
              title="Generated Output"
              docs={generatedDocs}
              emptyLabel="No generated documents yet."
              onOpen={openDocument}
              variant="generated"
            />
          </div>
        </div>
      </div>
    </div>
  )
}

function StatCard({ label, value, helper, tone }: { label: string, value: string, helper?: string, tone: 'emerald' | 'slate' }) {
  const toneClasses = tone === 'emerald'
    ? 'border-emerald-400/40 bg-gradient-to-br from-emerald-400/20 to-sky-500/10 text-emerald-50'
    : 'border-white/10 bg-slate-950/35 text-slate-100'

  return (
    <div className={`flex flex-col justify-between rounded-2xl border p-4 ${toneClasses}`}>
      <div>
        <p className="text-[0.6rem] uppercase tracking-[0.3em] text-slate-400">{label}</p>
        <p className="mt-2 text-lg font-semibold text-white text-right">{value}</p>
      </div>
      {helper ? <p className="mt-2 text-xs text-slate-400">{helper}</p> : null}
    </div>
  )
}

function InfoCard({ title, items }: { title: string, items: { label: string, value: string }[] }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-100">
      <p className="text-xs uppercase tracking-[0.25em] text-slate-400">{title}</p>
      <dl className="mt-3 space-y-2">
        {items.map(item => (
          <div key={item.label} className="flex items-center justify-between gap-3">
            <dt className="text-xs text-slate-400">{item.label}</dt>
            <dd className="text-sm font-medium text-white">{item.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

function DocumentGroup({ title, docs, emptyLabel, onOpen, variant = 'uploaded' }: { title: string, docs: DocumentItem[], emptyLabel: string, onOpen: (doc: DocumentItem) => void, variant?: 'uploaded' | 'generated' }) {
  return (
    <section>
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-[0.3em] text-slate-300">{title}</h3>
        <span className="text-[0.6rem] text-slate-500">{docs.length} item{docs.length === 1 ? '' : 's'}</span>
      </div>
      {docs.length === 0 ? (
        <div className="mt-2 rounded-2xl border border-dashed border-white/15 bg-slate-950/30 p-4 text-xs text-slate-400">
          {emptyLabel}
        </div>
      ) : (
        <ul className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {docs.map(doc => (
            <li key={doc.doc_id} className="rounded-2xl border border-white/10 bg-slate-950/40 p-4">
              <button
                onClick={() => onOpen(doc)}
                className="w-full text-left"
              >
                <p className="truncate font-semibold text-white" title={doc.name}>{doc.name}</p>
                {variant === 'uploaded' ? (
                  <p className="text-[0.75rem] text-slate-400">{fmtDate(doc.uploaded_at)}</p>
                ) : (
                  <>
                    <p className="mt-1 text-xs text-slate-400">{doc.type || 'File'}</p>
                    <p className="text-[0.65rem] text-slate-500">{fmtDate(doc.uploaded_at)}</p>
                  </>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
