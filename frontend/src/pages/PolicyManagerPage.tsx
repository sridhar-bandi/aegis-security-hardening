import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listWorkspaces, listPolicies, listPolicyRules, deletePolicy } from '../api/endpoints'
import type { Policy, PolicyRule } from '../types'

const SEVERITY_COLOR: Record<string, string> = {
  critical: '#c0392b', high: '#e67e22', medium: '#f39c12',
  low: '#27ae60', informational: '#2980b9',
}

export default function PolicyManagerPage() {
  const qc = useQueryClient()
  const [workspaceId, setWorkspaceId] = useState('')
  const [selectedPolicy, setSelectedPolicy] = useState<Policy | null>(null)

  const { data: workspaces = [] } = useQuery({ queryKey: ['workspaces'], queryFn: listWorkspaces })
  const { data: policies = [] } = useQuery({
    queryKey: ['policies', workspaceId],
    queryFn: () => listPolicies(workspaceId),
    enabled: !!workspaceId,
  })
  const { data: rules = [] } = useQuery({
    queryKey: ['policy-rules', selectedPolicy?.id],
    queryFn: () => listPolicyRules(selectedPolicy!.id),
    enabled: !!selectedPolicy,
  })

  const deleteMut = useMutation({
    mutationFn: (policyId: string) => deletePolicy(policyId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['policies', workspaceId] })
      setSelectedPolicy(null)
    },
  })

  return (
    <div className="flex gap-6 h-full">
      <div className="w-72 flex-shrink-0">
        <h2 className="text-xl font-bold text-aegis-dark mb-4">Policy Manager</h2>
        <select
          value={workspaceId}
          onChange={(e) => { setWorkspaceId(e.target.value); setSelectedPolicy(null) }}
          className="w-full border rounded px-2 py-1 text-sm mb-4"
        >
          <option value="">Select workspace…</option>
          {workspaces.map((ws) => (
            <option key={ws.id} value={ws.id}>{ws.name}</option>
          ))}
        </select>

        {/* Upload policy form */}
        {workspaceId && <UploadPolicyForm workspaceId={workspaceId} onUploaded={() => qc.invalidateQueries({ queryKey: ['policies', workspaceId] })} />}

        <div className="mt-4 flex flex-col gap-2">
          {policies.map((p) => (
            <button
              key={p.id}
              onClick={() => setSelectedPolicy(p)}
              className={`text-left px-3 py-2 rounded text-sm ${selectedPolicy?.id === p.id ? 'bg-aegis-dark text-white' : 'bg-white hover:bg-gray-100'}`}
            >
              <div className="font-medium">{p.name}</div>
              <div className="text-xs opacity-60">{p.standard} / {p.format}</div>
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1">
        {selectedPolicy ? (
          <>
            <div className="flex items-center gap-3 mb-4">
              <h3 className="text-lg font-semibold">{selectedPolicy.name}</h3>
              <button
                onClick={() => deleteMut.mutate(selectedPolicy.id)}
                className="text-xs text-aegis-red hover:underline ml-auto"
              >
                Delete Policy
              </button>
            </div>
            <RulesTable rules={rules} />
          </>
        ) : (
          <p className="text-gray-400">Select a policy to view its rules.</p>
        )}
      </div>
    </div>
  )
}

function UploadPolicyForm({ workspaceId, onUploaded }: { workspaceId: string; onUploaded: () => void }) {
  const [name, setName] = useState('')
  const [fmt, setFmt] = useState('json')
  const [standard, setStandard] = useState('Custom')
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleUpload = async () => {
    if (!file || !name) return
    setUploading(true)
    setError(null)
    const form = new FormData()
    form.append('file', file)
    const token = localStorage.getItem('aegis_token')
    const params = new URLSearchParams({ workspace_id: workspaceId, name, format: fmt, standard })
    try {
      const res = await fetch(`/api/v1/policies/upload?${params}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }))
        setError(body?.detail ?? `Upload failed (${res.status})`)
        return
      }
      setName('')
      setFile(null)
      onUploaded()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Network error')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="bg-white rounded-lg p-3 shadow text-sm flex flex-col gap-2">
      <p className="font-medium text-aegis-dark">Upload Policy</p>
      <input placeholder="Policy name" value={name} onChange={(e) => setName(e.target.value)} className="border rounded px-2 py-1" />
      <select value={fmt} onChange={(e) => setFmt(e.target.value)} className="border rounded px-2 py-1">
        <option value="json">JSON</option>
        <option value="text">Plain Text</option>
        <option value="OVAL">OVAL XML</option>
        <option value="XCCDF">XCCDF XML</option>
      </select>
      <select value={standard} onChange={(e) => setStandard(e.target.value)} className="border rounded px-2 py-1">
        {['CIS', 'STIG', 'SRG', 'Custom'].map((s) => <option key={s}>{s}</option>)}
      </select>
      <input type="file" accept=".xml,.txt,.json" onChange={(e) => setFile(e.target.files?.[0] ?? null)} className="text-xs" />
      {error && <p className="text-xs text-red-600">{error}</p>}
      <button onClick={handleUpload} disabled={uploading || !file || !name} className="bg-aegis-dark text-white rounded py-1 disabled:opacity-50">
        {uploading ? 'Uploading…' : 'Upload'}
      </button>
    </div>
  )
}

function RulesTable({ rules }: { rules: PolicyRule[] }) {
  return (
    <div className="overflow-auto rounded-lg shadow">
      <table className="w-full text-sm bg-white">
        <thead className="bg-aegis-dark text-white">
          <tr>
            {['Rule ID', 'Title', 'Severity', 'Category', 'Component Types'].map((h) => (
              <th key={h} className="px-3 py-2 text-left">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rules.map((r) => (
            <tr key={r.id} className="border-b hover:bg-gray-50">
              <td className="px-3 py-2 font-mono text-xs">{r.rule_id}</td>
              <td className="px-3 py-2">{r.title}</td>
              <td className="px-3 py-2">
                <span className="font-semibold" style={{ color: SEVERITY_COLOR[r.severity] }}>
                  {r.severity.toUpperCase()}
                </span>
              </td>
              <td className="px-3 py-2">{r.category}</td>
              <td className="px-3 py-2 text-xs">{(r.target_component_types ?? []).join(', ')}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
