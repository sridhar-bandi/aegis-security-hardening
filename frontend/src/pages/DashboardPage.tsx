import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { listWorkspaces, listInstances, listJobs, createWorkspace, deleteWorkspace } from '../api/endpoints'
import { complianceLevel } from '../types'

const COLORS = { green: '#27ae60', orange: '#e67e22', red: '#c0392b' }

export default function DashboardPage() {
  const { data: workspaces = [] } = useQuery({ queryKey: ['workspaces'], queryFn: listWorkspaces })
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')

  const mutation = useMutation({
    mutationFn: () => createWorkspace(name, description),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspaces'] })
      setShowForm(false)
      setName('')
      setDescription('')
    },
  })

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-aegis-dark">Compliance Dashboard</h2>
        <button
          onClick={() => setShowForm(true)}
          className="bg-aegis-dark text-white px-4 py-2 rounded hover:opacity-90 text-sm"
        >
          + New Workspace
        </button>
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold mb-4">Create Workspace</h3>
            <label className="block text-sm font-medium mb-1">Name *</label>
            <input
              className="w-full border rounded px-3 py-2 mb-3 text-sm"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Production Hardening"
              autoFocus
            />
            <label className="block text-sm font-medium mb-1">Description</label>
            <textarea
              className="w-full border rounded px-3 py-2 mb-4 text-sm"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description"
              rows={3}
            />
            {mutation.isError && (
              <p className="text-red-600 text-sm mb-3">Failed to create workspace.</p>
            )}
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setShowForm(false)}
                className="px-4 py-2 text-sm rounded border hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={() => mutation.mutate()}
                disabled={!name.trim() || mutation.isPending}
                className="px-4 py-2 text-sm rounded bg-aegis-dark text-white hover:opacity-90 disabled:opacity-50"
              >
                {mutation.isPending ? 'Creating…' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}

      {workspaces.length === 0 && (
        <p className="text-gray-500">No workspaces found. Click "New Workspace" to get started.</p>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {workspaces.map((ws) => (
          <WorkspaceCard key={ws.id} workspaceId={ws.id} workspaceName={ws.name} />
        ))}
      </div>
    </div>
  )
}

function WorkspaceCard({ workspaceId, workspaceName }: { workspaceId: string; workspaceName: string }) {
  const qc = useQueryClient()
  const { data: instances = [] } = useQuery({
    queryKey: ['instances', workspaceId],
    queryFn: () => listInstances(workspaceId),
  })

  const deleteMut = useMutation({
    mutationFn: () => deleteWorkspace(workspaceId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['workspaces'] }),
  })

  // Aggregate pass/fail from latest jobs
  let totalPass = 0
  let totalFail = 0
  instances.forEach((inst) => {
    // We'd need to fetch jobs per instance; use placeholder aggregation here
    _ = inst
  })
  const total = totalPass + totalFail
  const passPercent = total ? Math.round((totalPass / total) * 100) : 0
  const level = complianceLevel(passPercent)

  const pieData = [
    { name: 'Pass', value: totalPass },
    { name: 'Fail', value: totalFail },
  ].filter((d) => d.value > 0)

  return (
    <div className="bg-white rounded-xl shadow p-5">
      <div className="flex items-start justify-between mb-1">
        <h3 className="font-semibold text-lg text-aegis-dark">{workspaceName}</h3>
        <button
          onClick={() => {
            if (window.confirm(`Delete workspace "${workspaceName}"? This will permanently delete all policies, solution types, instances, and jobs within it.`)) {
              deleteMut.mutate()
            }
          }}
          className="text-red-500 hover:text-red-700 ml-2 flex-shrink-0"
          title="Delete workspace"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>
      <p className="text-sm text-gray-400 mb-4">{instances.length} instance(s)</p>
      <div
        className="text-3xl font-bold mb-2"
        style={{ color: COLORS[level] }}
      >
        {total > 0 ? `${passPercent}%` : 'N/A'}
      </div>
      {pieData.length > 0 && (
        <ResponsiveContainer width="100%" height={160}>
          <PieChart>
            <Pie data={pieData} dataKey="value" outerRadius={60} label>
              <Cell fill={COLORS.green} />
              <Cell fill={COLORS.red} />
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}

// Suppress unused var warning
let _ : unknown
