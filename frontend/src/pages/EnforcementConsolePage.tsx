import { useState, useEffect, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { listJobs, evaluateInstance, remediateInstance, rollbackInstance, dryRunInstance } from '../api/endpoints'
import type { EnforcementJob } from '../types'

const STATUS_COLOR: Record<string, string> = {
  pending: '#7f8c8d', running: '#2980b9', completed: '#27ae60', failed: '#c0392b',
}

export default function EnforcementConsolePage() {
  const { instanceId } = useParams<{ instanceId: string }>()
  const [log, setLog] = useState<string[]>([])
  const [activeJobId, setActiveJobId] = useState<string | null>(null)
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
    <div className="flex gap-6 h-full" style={{ minHeight: '80vh' }}>
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
      </div>

      {/* Right: job history */}
      <div className="w-80 flex-shrink-0">
        <h3 className="font-semibold text-aegis-dark mb-3">Job History</h3>
        <div className="flex flex-col gap-2 overflow-y-auto" style={{ maxHeight: '70vh' }}>
          {jobs.map((job) => (
            <button
              key={job.id}
              onClick={() => openWs(job.id)}
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
  )
}
