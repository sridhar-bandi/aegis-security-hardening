import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listPolicies, listPolicyRules, deletePolicy } from '../api/endpoints'
import { useWorkspace } from '../context/WorkspaceContext'
import type { Policy, PolicyRule } from '../types'

const SEVERITY_COLOR: Record<string, string> = {
  critical: '#c0392b', high: '#e67e22', medium: '#f39c12',
  low: '#27ae60', informational: '#2980b9',
}

export default function PolicyManagerPage() {
  const qc = useQueryClient()
  const { selectedWorkspace } = useWorkspace()
  const workspaceId = selectedWorkspace?.id ?? ''
  const [selectedPolicy, setSelectedPolicy] = useState<Policy | null>(null)
  const [showImport, setShowImport] = useState(false)

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
      <div className="w-72 flex-shrink-0 flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-aegis-dark">Policy Manager</h2>
          {workspaceId && (
            <a
              href="#import-policy"
              onClick={(e) => { e.preventDefault(); setShowImport(true) }}
              className="text-sm text-aegis-dark hover:underline font-medium"
            >
              + Import Policy
            </a>
          )}
        </div>

        {!workspaceId && (
          <p className="text-sm text-amber-600 bg-amber-50 border border-amber-200 rounded px-3 py-2 mb-4">
            Select a workspace from the header to manage policies.
          </p>
        )}

        {/* Policy list at the top */}
        <div className="flex flex-col gap-2">
          {policies.length === 0 && workspaceId && (
            <p className="text-xs text-gray-400 italic">No policies yet. Import one to get started.</p>
          )}
          {policies.map((p) => (
            <button
              key={p.id}
              onClick={() => setSelectedPolicy(p)}
              className={`text-left px-3 py-2 rounded text-sm ${selectedPolicy?.id === p.id ? 'bg-aegis-dark text-white' : 'bg-white hover:bg-gray-100'}`}
            >
              <div className="font-medium">{p.name}</div>
              <div className="text-xs opacity-60">{p.standard} / {p.format}</div>
              <div className="flex items-center gap-2 mt-1">
                <span className={`text-xs font-semibold px-1.5 py-0.5 rounded ${selectedPolicy?.id === p.id ? 'bg-white/20 text-white' : 'bg-aegis-dark/10 text-aegis-dark'}`}>
                  {p.rule_count} {p.rule_count === 1 ? 'rule' : 'rules'}
                </span>
                {p.target_component_types.length > 0 && (
                  <span className="text-xs opacity-70 truncate" title={p.target_component_types.join(', ')}>
                    {p.target_component_types.slice(0, 2).join(', ')}{p.target_component_types.length > 2 ? ` +${p.target_component_types.length - 2}` : ''}
                  </span>
                )}
              </div>
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

      {/* Import Policy Modal */}
      {showImport && workspaceId && (
        <ImportPolicyModal
          workspaceId={workspaceId}
          onClose={() => setShowImport(false)}
          onImported={() => {
            qc.invalidateQueries({ queryKey: ['policies', workspaceId] })
            setShowImport(false)
          }}
        />
      )}
    </div>
  )
}

function ImportPolicyModal({ workspaceId, onClose, onImported }: { workspaceId: string; onClose: () => void; onImported: () => void }) {
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
      onImported()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Network error')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div
        className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 flex flex-col gap-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold text-aegis-dark">Import Policy</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700 text-xl leading-none">&times;</button>
        </div>

        <div className="flex flex-col gap-3 text-sm">
          <label className="flex flex-col gap-1">
            <span className="font-medium text-gray-700">Policy Name <span className="text-red-500">*</span></span>
            <input
              placeholder="e.g. CIS Ubuntu 22.04 L1"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-aegis-dark"
            />
          </label>

          <label className="flex flex-col gap-1">
            <span className="font-medium text-gray-700">Format</span>
            <select value={fmt} onChange={(e) => setFmt(e.target.value)} className="border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-aegis-dark">
              <option value="json">JSON</option>
              <option value="text">Plain Text</option>
              <option value="OVAL">OVAL XML</option>
              <option value="XCCDF">XCCDF XML</option>
            </select>
          </label>

          <label className="flex flex-col gap-1">
            <span className="font-medium text-gray-700">Standard</span>
            <select value={standard} onChange={(e) => setStandard(e.target.value)} className="border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-aegis-dark">
              {['CIS', 'STIG', 'SRG', 'Custom'].map((s) => <option key={s}>{s}</option>)}
            </select>
          </label>

          <label className="flex flex-col gap-1">
            <span className="font-medium text-gray-700">Policy File <span className="text-red-500">*</span></span>
            <input
              type="file"
              accept=".xml,.txt,.json"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="text-sm file:mr-3 file:rounded file:border-0 file:bg-aegis-dark file:text-white file:px-3 file:py-1 file:cursor-pointer"
            />
          </label>

          {error && <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>}
        </div>

        <div className="flex gap-3 pt-1">
          <button onClick={onClose} className="flex-1 border rounded py-2 text-sm text-gray-600 hover:bg-gray-50">
            Cancel
          </button>
          <button
            onClick={handleUpload}
            disabled={uploading || !file || !name}
            className="flex-1 bg-aegis-dark text-white rounded py-2 text-sm disabled:opacity-50 hover:opacity-90"
          >
            {uploading ? 'Importing…' : 'Import'}
          </button>
        </div>
      </div>
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
