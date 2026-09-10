import CaseMonitor from '@/components/CaseMonitor';

export default function CasePage({ params }: { params: { caseId: string } }) { return <CaseMonitor caseId={params.caseId} />; }
