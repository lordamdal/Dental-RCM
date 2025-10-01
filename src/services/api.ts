
import axios from 'axios'

const baseURL = (import.meta as any).env.VITE_API_BASE || 'http://34.168.37.99:8000'
export const api = axios.create({ baseURL })

export async function listCases() {
  const res = await api.get('/cases')
  return res.data
}

export async function createCase(data: { title: string, patient_name?: string, payer?: string }) {
  const res = await api.post('/cases', data)
  return res.data
}

export async function deleteCase(caseId: string) {
  await api.delete(`/cases/${caseId}`)
}

export async function getCase(caseId: string) {
  const res = await api.get(`/cases/${caseId}`)
  return res.data
}

export async function listDocs(caseId: string) {
  const res = await api.get(`/cases/${caseId}/documents`)
  return res.data
}

export async function uploadDoc(caseId: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await api.post(`/cases/${caseId}/documents`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return res.data
}

export async function listMessages(caseId: string) {
  const res = await api.get(`/cases/${caseId}/messages`)
  return res.data
}

export async function sendMessage(caseId: string, content: string) {
  const res = await api.post(`/cases/${caseId}/chat`, { content })
  return res.data
}

export function resolvePublicUrl(path?: string | null) {
  if (!path) return ''
  try {
    const base = api.defaults.baseURL || window.location.origin
    return new URL(path, base).toString()
  } catch (err) {
    console.error('Failed to resolve document URL', err)
    return path
  }
}
