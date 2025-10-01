import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useStore } from '../store'
import { listCases, listDocs, listMessages, sendMessage, uploadDoc } from '../services/api'
import type { Message as MessageItem } from '../store'

export default function CaseChatPanel() {
  const { caseId } = useParams<{ caseId: string }>()
  const { messages, setMessages, setCases, setDocuments, cases } = useStore()
  const list = (caseId && messages[caseId]) || []
  const [pending, setPending] = useState(false)
  const [input, setInput] = useState('')
  const [uploadPending, setUploadPending] = useState(false)
  const scroller = useRef<HTMLDivElement>(null)

  const refreshCaseData = useCallback(async (id: string) => {
    try {
      const [docs, casesList] = await Promise.all([
        listDocs(id),
        listCases(),
      ])
      setDocuments(id, docs)
      setCases(casesList)
    } catch (err) {
      console.error('Failed to refresh case data', err)
    }
  }, [setCases, setDocuments])

  const currentCase = useMemo(() => cases.find(c => c.case_id === caseId), [caseId, cases])

  const friendlyLabel = (value?: string | null) => {
    if (!value) return '—'
    return value
      .replace(/_/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
      .replace(/(^|\s)\S/g, (s) => s.toUpperCase())
  }

  const uploadStageMeta: Record<string, string> = {
    awaiting_case_details: 'Upload patient demographics or intake packet',
    awaiting_procedure_documents: 'Upload clinical notes with ADA CDT codes',
    awaiting_additional_documentation: 'Upload MD/operative documentation',
    awaiting_signed_soap_note: 'Upload the signed SOAP note',
  }

  const currentStage = currentCase?.workflow_stage || ''
  const uploadHint = uploadStageMeta[currentStage]
  const uploadDisabled = !uploadHint || uploadPending

  useEffect(() => {
    if (caseId) {
      listMessages(caseId).then(async m => {
        setMessages(caseId, m)
        await refreshCaseData(caseId)
      }).catch(err => {
        console.error('Failed to load messages', err)
        alert('Failed to load messages. Please try again later.')
      })
    }
  }, [caseId, refreshCaseData, setMessages])

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight })
  }, [list.length])

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!caseId || !file) return
    setUploadPending(true)
    try {
      await uploadDoc(caseId, file)
      const latest = await listMessages(caseId)
      setMessages(caseId, latest)
      await refreshCaseData(caseId)
    } catch (err) {
      console.error('Failed to upload document', err)
      alert('Failed to upload document. Please try again later.')
    } finally {
      setUploadPending(false)
      event.target.value = ''
    }
  }

  const send = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!caseId) return
    const trimmed = input.trim()
    if (!trimmed) return

    const optimistic: MessageItem = {
      msg_id: `temp-${Date.now()}`,
      case_id: caseId,
      role: 'user',
      content: trimmed,
      created_at: new Date().toISOString(),
    }

    setPending(true)
    setMessages(caseId, [...list, optimistic])
    setInput('')

    try {
      await sendMessage(caseId, trimmed)
    } catch (err) {
      console.error('Failed to send message', err)
      alert('Failed to send message. Please try again later.')
    } finally {
      try {
        const latest = await listMessages(caseId)
        setMessages(caseId, latest)
      } catch (refreshErr) {
        console.error('Failed to refresh messages', refreshErr)
      }
      try {
        await refreshCaseData(caseId)
      } catch (refreshCaseErr) {
        console.error('Failed to sync case data', refreshCaseErr)
      }
      setPending(false)
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="border-b border-white/10 bg-white/5 px-5 py-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-[0.65rem] uppercase tracking-[0.4em] text-emerald-200/70">Assistant</p>
            <p className="mt-1 text-lg font-semibold text-white">Realtime Copilot</p>
            <p className="text-xs text-slate-300">{currentCase?.workflow_status || 'Let me know how I can help.'}</p>
          </div>
          <div className="rounded-2xl border border-emerald-400/40 bg-emerald-400/10 px-3 py-2 text-right text-xs text-emerald-100">
            <div className="font-semibold uppercase tracking-wide">{friendlyLabel(currentCase?.status) || 'No case selected'}</div>
            <div className="text-[0.65rem] text-emerald-100/80">{currentCase ? friendlyLabel(currentCase.workflow_stage) : 'Select a case from the queue'}</div>
          </div>
        </div>
      </div>

      <div ref={scroller} className="flex-1 space-y-4 overflow-y-auto px-5 py-6">
        {list.filter(m=>m.role !== 'system').map(m => {
          const isUser = m.role === 'user'
          const isSystem = m.role === 'system'
          return (
            <div key={m.msg_id} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] rounded-3xl border px-4 py-3 text-sm leading-relaxed shadow-lg ${isUser ? 'rounded-tr-md border-emerald-400/60 bg-emerald-400/20 text-emerald-50' : isSystem ? 'border-sky-400/40 bg-sky-400/10 text-sky-100' : 'border-white/10 bg-white/10 text-slate-100'}`}>
                <div className="whitespace-pre-wrap text-sm">{m.content}</div>
                <div className="mt-2 text-[0.6rem] text-slate-400">{new Date(m.created_at).toLocaleString()}</div>
              </div>
            </div>
          )
        })}
        {currentStage === 'awaiting_resolution_choice' && (
          <div className="flex flex-wrap gap-2">
            {[{n:1,label:'Upload docs'},{n:2,label:'Remove procedure'},{n:3,label:'Submit as-is'},{n:4,label:'Pause case'}].map(opt => (
              <button
                key={opt.n}
                disabled={pending}
                onClick={async ()=>{
                  if(!caseId) return; setPending(true);
                  try{ await sendMessage(caseId, String(opt.n));
                    const latest = await listMessages(caseId); setMessages(caseId, latest);
                    await refreshCaseData(caseId);
                  }catch(err){ console.error('Failed to send quick option', err); alert('Failed to send. Please try again.'); }
                  finally{ setPending(false); }
                }}
                className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1.5 text-xs text-slate-200 transition hover:border-emerald-400/60 hover:text-white disabled:opacity-50"
              >
                <span className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-white/20 bg-white/5 text-[0.7rem]">{opt.n}</span>
                {opt.label}
              </button>
            ))}
          </div>
        )}

        {list.length === 0 && (
          <div className="flex h-full min-h-[240px] items-center justify-center rounded-3xl border border-dashed border-white/10 bg-white/0 text-sm text-slate-300">
            No messages yet—say hello to kick things off.
          </div>
        )}
      </div>

      <form onSubmit={send} className="border-t border-white/10 bg-slate-950/60 px-5 py-4">
        <div className="space-y-3">
          {uploadHint && (
            <label className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-emerald-400/40 bg-emerald-400/10 px-4 py-3 text-xs text-emerald-100">
              <div className="flex items-center gap-2">
                <span className="inline-flex h-2 w-2 rounded-full bg-emerald-300" />
                {uploadHint}
              </div>
              <span className="text-[0.65rem] text-emerald-100/80">Use the upload button below.</span>
            </label>
          )}

          <div className="flex flex-wrap items-end gap-3">
            <div className="flex-1 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 shadow-inner focus-within:border-emerald-400/60">
              <textarea
                value={input}
                onChange={e=>setInput(e.target.value)}
                placeholder={currentCase ? 'Type a response or ask for the next step…' : 'Select a case to start chatting…'}
                className="h-16 w-full resize-none bg-transparent text-sm text-white placeholder:text-slate-400 focus:outline-none"
              />
            </div>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <label className={`inline-flex cursor-pointer items-center gap-2 rounded-full border px-4 py-2 text-sm transition ${uploadDisabled ? 'cursor-not-allowed border-white/10 bg-white/5 text-slate-400' : 'border-emerald-400/60 bg-emerald-400/20 text-emerald-50 hover:bg-emerald-400/30'}`}>
                <input type="file" className="hidden" onChange={handleUpload} disabled={uploadDisabled} />
                <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 16V4m0 0 3.5 3.5M12 4 8.5 7.5M6 16v2a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2v-2" />
                </svg>
                {uploadPending ? 'Uploading…' : 'Upload'}
              </label>
              <button
                disabled={pending || !caseId}
                className="inline-flex items-center justify-center rounded-full border border-sky-400/60 bg-sky-500/20 px-5 py-2 text-sm font-semibold text-sky-100 transition hover:bg-sky-500/30 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {pending ? 'Sending…' : 'Send'}
              </button>
            </div>
          </div>
        </div>
      </form>
    </div>
  )
}
