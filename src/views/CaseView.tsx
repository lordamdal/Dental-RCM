import { useParams } from 'react-router-dom'
import CaseDashboard from '../components/CaseDashboard'

export default function CaseView() {
  const { caseId } = useParams<{ caseId: string }>();
  if (!caseId) return null;
  return <CaseDashboard caseId={caseId} />
}
