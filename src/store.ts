import { create } from 'zustand'

export type CaseItem = {
  case_id: string
  title: string
  patient_name?: string
  payer?: string
  status?: string
  reimbursement_amount?: number
  reimbursement_date?: string
  workflow_stage?: string
  workflow_status?: string
  next_action?: string
  risk_level?: string
  created_at: string
  updated_at: string
}

export type Message = {
  msg_id: string
  case_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
}

export type DocumentItem = {
  doc_id: string
  case_id: string
  name: string
  type?: string
  path?: string
  public_url?: string
  uploaded_at: string
}

type State = {
  cases: CaseItem[]
  selectedCaseId?: string
  messages: Record<string, Message[]>
  documents: Record<string, DocumentItem[]>
  setCases: (c: CaseItem[]) => void
  selectCase: (id?: string) => void
  setMessages: (caseId: string, m: Message[]) => void
  setDocuments: (caseId: string, d: DocumentItem[]) => void
}

export const useStore = create<State>((set) => ({
  cases: [],
  selectedCaseId: undefined,
  messages: {},
  documents: {},
  setCases: (cases) => set({ cases }),
  selectCase: (selectedCaseId) => set({ selectedCaseId }),
  setMessages: (caseId, m) => set((s) => ({ messages: { ...s.messages, [caseId]: m } })),
  setDocuments: (caseId, d) => set((s) => ({ documents: { ...s.documents, [caseId]: d } })),
}))
