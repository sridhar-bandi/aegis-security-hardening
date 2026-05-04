import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { listWorkspaces, listInstances, createInstance, deleteInstance } from '../api/endpoints'

export default function InstanceManagerPage() {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [workspaceId, setWorkspaceId] = useState('')
  const [newName, setNewName] = useState('')

  const { data: workspaces = [] } = useQuery({ queryKey: ['workspaces'], queryFn: listWorkspaces })
  const { data: instances = [] } = useQuery({
    queryKey: ['instances', workspaceId],
    queryFn: () => listInstances(workspaceId),
    enabled: !!workspaceId,
  })

  const createMut = useMutation({
    mutationFn: () => createInstance(workspaceId, newName),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['instances', workspaceId] }); setNewName('') },
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteInstance(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['instances', workspaceId] }),
  })

  return (
    <div>
      <h2 className="text-xl font-bold text-aegis-dark mb-4">Solution Instances</h2>
      <div className="flex gap-3 mb-6">
        <select
          value={workspaceId}
          onChange={(e) => setWorkspaceId(e.target.value)}
          className="border rounded px-2 py-1 text-sm"
        >
          <option value="">Select workspace…</option>
          {workspaces.map((ws) => <option key={ws.id} value={ws.id}>{ws.name}</option>)}
        </select>
        <input
          placeholder="New instance name"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          className="border rounded px-2 py-1 text-sm"
        />
        <button
          onClick={() => createMut.mutate()}
          disabled={!workspaceId || !newName}
          className="bg-aegis-dark text-white rounded px-3 py-1 text-sm disabled:opacity-50"
        >
          Create Instance
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {instances.map((inst) => (
          <div key={inst.id} className="bg-white rounded-lg shadow p-4">
            <div className="font-semibold mb-1">{inst.name}</div>
            <div className="text-xs text-gray-400 mb-3 font-mono">{inst.id}</div>
            <div className="flex gap-2">
              <button
                onClick={() => navigate(`/instances/${inst.id}/enforcement`)}
                className="text-sm bg-aegis-dark text-white rounded px-3 py-1"
              >
                Open Enforcement Console
              </button>
              <button
                onClick={() => {
                  if (window.confirm(`Delete instance "${inst.name}"? This will also delete all enforcement jobs and compliance reports.`)) {
                    deleteMut.mutate(inst.id)
                  }
                }}
                className="text-sm bg-red-600 text-white rounded px-3 py-1 hover:bg-red-700"
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
