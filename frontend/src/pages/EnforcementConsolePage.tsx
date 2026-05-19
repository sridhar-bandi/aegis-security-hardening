import { useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { listJobs, evaluateInstance, remediateInstance, rollbackInstance, dryRunInstance } from '../api/endpoints'
import type { EnforcementJob } from '../types'

const STATUS_COLOR: Record<string, string> = {
  pending: '#7f8c8d', running: '#2980b9', completed: '#27ae60', failed: '#c0392b',
}

const JOB_TYPE_LABELS: Record<string, string> = {
  dry_run: 'Dry Run',
  evaluate: 'Evaluate',
  remediate: 'Remediate',
  rollback: 'Rollback',
  impact_assessment: 'Impact Assessment',
}

function JobDetails({ job }: { job: EnforcementJob }) {
  const summary = job.result_summary
  if (!summary) {
    if (job.status === 'pending' || job.status === 'running') {
      return <p className="text-gray-500 italic">Job is {job.status}…</p>
    }
    return <p className="text-gray-500 italic">No result details available.</p>
  }

  if (summary.error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded p-3">
        <p className="font-semibold text-red-700 mb-1">Error</p>
        <pre className="text-xs text-red-800 whitespace-pre-wrap">{String(summary.error)}</pre>
      </div>
    )
  }

  if (job.job_type === 'evaluate') {
    const details = (summary.details as { rule_id: string; compliant: boolean; details: string }[]) || []
    return (
      <div className="space-y-3">
        <div className="flex gap-4 text-sm">
          <span className="text-green-700 font-semibold">Pass: {(summary.pass as number) ?? 0}</span>
          <span className="text-red-700 font-semibold">Fail: {(summary.fail as number) ?? 0}</span>
          <span className="text-gray-600">Total: {(summary.total as number) ?? 0}</span>
        </div>
        {details.length > 0 && (
          <div className="max-h-60 overflow-y-auto border rounded">
            <table className="w-full text-xs">
              <thead className="bg-gray-100 sticky top-0">
                <tr>
                  <th className="text-left p-2">Rule</th>
                  <th className="text-left p-2">Status</th>
                  <th className="text-left p-2">Details</th>
                </tr>
              </thead>
              <tbody>
                {details.map((d, i) => (
                  <tr key={i} className="border-t">
                    <td className="p-2 font-mono">{d.rule_id}</td>
                    <td className="p-2">
                      <span className={d.compliant ? 'text-green-600 font-semibold' : 'text-red-600 font-semibold'}>
                        {d.compliant ? 'PASS' : 'FAIL'}
                      </span>
                    </td>
                    <td className="p-2 text-gray-600">{d.details || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    )
  }

  if (job.job_type === 'remediate' || job.job_type === 'rollback') {
    return (
      <div className="space-y-2">
        <div className="flex gap-4 text-sm">
          <span className="text-green-700 font-semibold">Success: {(summary.success as number) ?? 0}</span>
          <span className="text-red-700 font-semibold">Failed: {(summary.failed as number) ?? 0}</span>
          <span className="text-gray-600">Total: {(summary.total as number) ?? 0}</span>
        </div>
        {summary.total != null && (
          <div className="w-full bg-gray-200 rounded h-3 overflow-hidden">
            <div
              className="bg-green-500 h-full"
              style={{ width: `${((summary.success as number) / (summary.total as number)) * 100}%` }}
            />
          </div>
        )}
      </div>
    )
  }

  if (job.job_type === 'dry_run') {
    const report = summary.report as Record<string, unknown> | undefined
    return (
      <div className="space-y-3">
        <div className="flex gap-4 text-sm">
          <span className="text-green-700 font-semibold">Safe: {(summary.safe as number) ?? 0}</span>
          <span className="text-yellow-700 font-semibold">Risky: {(summary.risky as number) ?? 0}</span>
          <span className="text-red-700 font-semibold">Breaking: {(summary.breaking as number) ?? 0}</span>
        </div>
        {report && (
          <details className="text-xs">
            <summary className="cursor-pointer text-aegis-blue font-medium">View full report</summary>
            <pre className="mt-2 bg-gray-50 p-2 rounded border overflow-x-auto max-h-60 overflow-y-auto whitespace-pre-wrap">
              {JSON.stringify(report, null, 2)}
            </pre>
          </details>
        )}
      </div>
    )
  }

  // Fallback: render raw JSON for unknown types
  return (
    <pre className="text-xs bg-gray-50 p-2 rounded border overflow-x-auto max-h-60 overflow-y-auto whitespace-pre-wrap">
      {JSON.stringify(summary, null, 2)}
    </pre>
  )
}

export default function EnforcementConsolePage() {
  const { instanceId } = useParams<{ instanceId: string }>()
  const navigate = useNavigate()
  const [log, setLog] = useState<string[]>([])
  const [activeJobId, setActiveJobId] = useState<string | null>(null)
  const [selectedJob, setSelectedJob] = useState<EnforcementJob | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  const { data: jobs = [], refetch: refetchJobs } = useQuery({
    queryKey: ['jobs', instanceId],
    queryFn: () => listJobs(instanceId!),
    enabled: !!instanceId,
    refetchInterval: 5000,
  })

  const openWs = (jobId: string) => {
    wsRef.current?.close()
    setLog([])
    setActiveJobId(jobId)
    const token = localStorage.getItem('aegis_token') ?? ''
    const ws = new WebSocket(`ws://${location.host}/api/v1/ws/enforcement/${jobId}?token=${token}`)
    wsRef.current = ws
    ws.onmessage = (evt) => {
      setLog((prev) => [...prev, evt.data])
      const msg = JSON.parse(evt.data)
      if (msg.type === 'completed' || msg.type === 'failed') {
        refetchJobs()
      }
    }
  }

  const handleJobClick = (job: EnforcementJob) => {
    setSelectedJob(job)
    setActiveJobId(job.id)
    if (job.status === 'running' || job.status === 'pending') {
      openWs(job.id)
    }
  }

  const evalMut = useMutation({
    mutationFn: () => evaluateInstance(instanceId!),
    onSuccess: (job) => { refetchJobs(); openWs(job.id) },
  })
  const remMut = useMutation({
    mutationFn: () => remediateInstance(instanceId!),
    onSuccess: (job) => { refetchJobs(); openWs(job.id) },
  })
  const rollMut = useMutation({
    mutationFn: () => rollbackInstance(instanceId!),
    onSuccess: (job) => { refetchJobs(); openWs(job.id) },
  })
  const dryMut = useMutation({
    mutationFn: () => dryRunInstance(instanceId!),
    onSuccess: (job) => { refetchJobs(); openWs(job.id) },
  })

  const isRunning = evalMut.isPending || remMut.isPending || rollMut.isPending || dryMut.isPending

  return (
    <div className="flex flex-col h-full" style={{ minHeight: '80vh' }}>
      <button
        onClick={() => navigate('/instances')}
        className="flex items-center gap-1 text-sm text-slate-500 hover:text-aegis-blue mb-3 w-fit"
      >
        <span>←</span> Back to Instances
      </button>
      <div className="flex gap-6 flex-1">
      {/* Left: actions + log */}
      <div className="flex-1 flex flex-col gap-4">
        <h2 className="text-xl font-bold text-aegis-dark">Enforcement Console</h2>
        <p className="text-sm text-gray-400 font-mono">{instanceId}</p>
        <div className="flex gap-2 flex-wrap">
          {[
            { label: '🔍 Dry Run', mut: dryMut },
            { label: '📋 Evaluate', mut: evalMut },
            { label: '🔧 Remediate', mut: remMut },
            { label: '↩ Rollback', mut: rollMut },
          ].map(({ label, mut }) => (
            <button
              key={label}
              onClick={() => (mut as { mutate: () => void }).mutate()}
              disabled={isRunning}
              className="bg-aegis-dark text-white rounded px-4 py-2 text-sm disabled:opacity-50 hover:bg-gray-700 transition-colors"
            >
              {label}
            </button>
          ))}
        </div>

        <div className="flex-1 bg-gray-900 text-green-300 font-mono text-xs rounded p-4 overflow-y-auto min-h-48">
          {log.length === 0 ? (
            <span className="text-gray-600">WebSocket log will appear here…</span>
          ) : (
            log.map((l, i) => <div key={i}>{l}</div>)
          )}
        </div>

        {/* Job Details Panel */}
        {selectedJob && (
          <div className="bg-white rounded-lg shadow p-4 border border-gray-200">
            <div className="flex justify-between items-center mb-3">
              <h4 className="font-semibold text-aegis-dark">
                {JOB_TYPE_LABELS[selectedJob.job_type] || selectedJob.job_type} — Details
              </h4>
              <div className="flex items-center gap-2">
                <span style={{ color: STATUS_COLOR[selectedJob.status] }} className="text-xs font-bold uppercase">
                  {selectedJob.status}
                </span>
                <button
                  onClick={() => setSelectedJob(null)}
                  className="text-gray-400 hover:text-gray-600 text-lg leading-none"
                >
                  ×
                </button>
              </div>
            </div>
            <div className="text-xs text-gray-400 mb-3">
              Started: {new Date(selectedJob.created_at).toLocaleString()}
              {selectedJob.completed_at && <> • Completed: {new Date(selectedJob.completed_at).toLocaleString()}</>}
            </div>
            <JobDetails job={selectedJob} />
          </div>
        )}
      </div>

      {/* Right: job history */}
      <div className="w-80 flex-shrink-0">
        <h3 className="font-semibold text-aegis-dark mb-3">Job History</h3>
        <div className="flex flex-col gap-2 overflow-y-auto" style={{ maxHeight: '70vh' }}>
          {jobs.map((job) => (
            <button
              key={job.id}
              onClick={() => handleJobClick(job)}
              className={`text-left bg-white rounded-lg p-3 shadow text-xs border-l-4 ${activeJobId === job.id ? 'border-aegis-blue' : 'border-transparent'}`}
            >
              <div className="flex justify-between mb-1">
                <span className="font-semibold uppercase">{job.job_type}</span>
                <span style={{ color: STATUS_COLOR[job.status] }} className="font-bold uppercase">
                  {job.status}
                </span>
              </div>
              <div className="text-gray-400">{new Date(job.created_at).toLocaleString()}</div>
              {job.result_summary && (
                <div className="mt-1 text-gray-600">
                  {JSON.stringify(job.result_summary).slice(0, 80)}…
                </div>
              )}
            </button>
          ))}
        </div>
      </div>
      </div>
    </div>
  )
}
