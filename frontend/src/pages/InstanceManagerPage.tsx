import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  listInstances,
  createInstance,
  deleteInstance,
  listSolutionTypes,
  listPolicies,
  listProfiles,
} from '../api/endpoints'
import { useWorkspace } from '../context/WorkspaceContext'
import type { HardeningProfile, Policy, SolutionInstance, SolutionType } from '../types'

export default function InstanceManagerPage() {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const { selectedWorkspace } = useWorkspace()
  const workspaceId = selectedWorkspace?.id ?? ''

  // Selection state
  const [solutionTypeId, setSolutionTypeId] = useState('')
  const [profileId, setProfileId] = useState('')
  const [newName, setNewName] = useState('')

  // Data queries
  const { data: solutionTypes = [] } = useQuery({
    queryKey: ['solution-types', workspaceId],
    queryFn: () => listSolutionTypes(workspaceId),
    enabled: !!workspaceId,
  })

  const { data: policies = [] } = useQuery({
    queryKey: ['policies', workspaceId],
    queryFn: () => listPolicies(workspaceId),
    enabled: !!workspaceId,
  })

  const { data: profiles = [] } = useQuery({
    queryKey: ['profiles', solutionTypeId],
    queryFn: () => listProfiles(solutionTypeId),
    enabled: !!solutionTypeId,
  })

  const { data: instances = [] } = useQuery({
    queryKey: ['instances', workspaceId],
    queryFn: () => listInstances(workspaceId),
    enabled: !!workspaceId,
  })

  // Lookup maps for display
  const stMap = Object.fromEntries(solutionTypes.map((s: SolutionType) => [s.id, s]))
  const policyMap = Object.fromEntries(policies.map((p: Policy) => [p.id, p]))

  // Selected solution type details
  const selectedSolutionType = solutionTypeId ? stMap[solutionTypeId] : null

  // Applicable policies: those referenced by profiles for the selected solution type
  const applicablePolicyIds = new Set(profiles.map((p: HardeningProfile) => p.policy_id))
  const applicablePolicies = policies.filter((p: Policy) => applicablePolicyIds.has(p.id))

  const handleSolutionTypeChange = (id: string) => {
    setSolutionTypeId(id)
    setProfileId('')
  }

  const createMut = useMutation({
    mutationFn: () =>
      createInstance(
        workspaceId,
        newName,
        solutionTypeId || undefined,
        profileId || undefined,
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['instances', workspaceId] })
      setNewName('')
      setProfileId('')
    },
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteInstance(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['instances', workspaceId] }),
  })

  return (
    <div>
      <h2 className="text-xl font-bold text-aegis-dark mb-6">Solution Instances</h2>

      {!workspaceId && (
        <div className="bg-amber-50 border border-amber-200 text-amber-700 text-sm rounded px-4 py-3 mb-6">
          Select a workspace from the header to manage instances.
        </div>
      )}

      {/* ── Create Instance Panel ── */}
      <div className="bg-white rounded-lg shadow p-5 mb-8">
        <h3 className="font-semibold text-aegis-dark mb-4">Create New Instance</h3>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 mb-4">
          {/* Step 1 – Solution Type */}
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">1. Solution Type</label>
            <select
              value={solutionTypeId}
              onChange={(e) => handleSolutionTypeChange(e.target.value)}
              disabled={!workspaceId}
              className="w-full border rounded px-2 py-1.5 text-sm disabled:opacity-50 disabled:bg-gray-50"
            >
              <option value="">Select solution type…</option>
              {solutionTypes.map((st: SolutionType) => (
                <option key={st.id} value={st.id}>{st.name}</option>
              ))}
            </select>
            {selectedSolutionType?.description && (
              <p className="text-xs text-gray-400 mt-1">{selectedSolutionType.description}</p>
            )}
          </div>

          {/* Step 2 – Profile (ties policy to solution type) */}
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">2. Hardening Profile</label>
            <select
              value={profileId}
              onChange={(e) => setProfileId(e.target.value)}
              disabled={!solutionTypeId}
              className="w-full border rounded px-2 py-1.5 text-sm disabled:opacity-50 disabled:bg-gray-50"
            >
              <option value="">Select profile…</option>
              {profiles.map((p: HardeningProfile) => {
                const policy = p.policy_id ? policyMap[p.policy_id] : undefined
                return (
                  <option key={p.id} value={p.id}>
                    {p.name}{policy ? ` (${policy.name})` : ''}
                  </option>
                )
              })}
            </select>
            {profiles.length === 0 && solutionTypeId && (
              <p className="text-xs text-amber-500 mt-1">No profiles yet for this solution type</p>
            )}
          </div>

          {/* Step 3 – Name */}
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">3. Instance Name</label>
            <input
              placeholder="Enter instance name…"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="w-full border rounded px-2 py-1.5 text-sm"
            />
          </div>
        </div>

        {/* Applicable Policies info panel */}
        {solutionTypeId && applicablePolicies.length > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded p-3 mb-4">
            <p className="text-xs font-semibold text-blue-700 mb-2">
              Applicable Policies for "{selectedSolutionType?.name}"
            </p>
            <div className="flex flex-wrap gap-2">
              {applicablePolicies.map((p: Policy) => (
                <span
                  key={p.id}
                  className="inline-flex items-center gap-1 bg-white border border-blue-200 text-blue-800 text-xs rounded px-2 py-0.5"
                >
                  <span className="font-medium">{p.name}</span>
                  <span className="text-blue-400">·</span>
                  <span className="uppercase">{p.standard}</span>
                </span>
              ))}
            </div>
          </div>
        )}

        <button
          onClick={() => createMut.mutate()}
          disabled={!workspaceId || !solutionTypeId || !newName}
          className="bg-aegis-dark text-white rounded px-4 py-1.5 text-sm disabled:opacity-50 hover:opacity-90 transition-opacity"
        >
          {createMut.isPending ? 'Creating…' : 'Create Instance'}
        </button>
      </div>

      {/* ── Instances List ── */}
      {!workspaceId && (
        <p className="text-sm text-gray-400">Select a workspace to view instances.</p>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {instances.map((inst: SolutionInstance) => {
          const st = inst.solution_type_id ? stMap[inst.solution_type_id] : null
          return (
            <div key={inst.id} className="bg-white rounded-lg shadow p-4">
              <div className="font-semibold mb-1">{inst.name}</div>
              {st && (
                <div className="text-xs text-blue-700 bg-blue-50 rounded px-2 py-0.5 inline-block mb-1">
                  {st.name}
                </div>
              )}
              <div className="text-xs text-gray-400 mb-3 font-mono truncate">{inst.id}</div>
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
          )
        })}
      </div>
    </div>
  )
}

