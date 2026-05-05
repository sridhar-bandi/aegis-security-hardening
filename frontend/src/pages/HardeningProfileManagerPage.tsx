import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  listSolutionTypes,
  listPolicies,
  listProfiles,
  createProfile,
  deleteProfile,
  triggerCodeGen,
  generatePolicyCodes,
} from '../api/endpoints'
import { useWorkspace } from '../context/WorkspaceContext'
import type { HardeningProfile, Policy, SolutionType } from '../types'

const STATUS_BADGE: Record<string, string> = {
  draft:      'bg-gray-100 text-gray-600',
  generating: 'bg-yellow-100 text-yellow-700',
  ready:      'bg-green-100 text-green-700',
}

const CODE_STATUS_BADGE: Record<string, string> = {
  pending:   'bg-gray-100 text-gray-500',
  generating:'bg-yellow-100 text-yellow-700',
  generated: 'bg-blue-100 text-blue-700',
  reviewed:  'bg-orange-100 text-orange-700',
  approved:  'bg-green-100 text-green-700',
  rejected:  'bg-red-100 text-red-700',
}

export default function HardeningProfileManagerPage() {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const { selectedWorkspace } = useWorkspace()
  const workspaceId = selectedWorkspace?.id ?? ''

  const [solutionTypeId, setSolutionTypeId]   = useState('')
  const [newName, setNewName]                 = useState('')
  // Maps each component type → selected policy id
  const [componentPolicyMap, setComponentPolicyMap] = useState<Record<string, string>>({})

  // ── Data ────────────────────────────────────────────────────────────────
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

  const { data: profiles = [], isLoading: profilesLoading } = useQuery({
    queryKey: ['profiles', solutionTypeId],
    queryFn: () => listProfiles(solutionTypeId),
    enabled: !!solutionTypeId,
  })

  const policyMap = Object.fromEntries(policies.map((p: Policy) => [p.id, p]))
  const selectedST = solutionTypes.find((s: SolutionType) => s.id === solutionTypeId)

  // ── Mutations ────────────────────────────────────────────────────────────
  const createMut = useMutation({
    mutationFn: () => createProfile(newName.trim(), solutionTypeId, componentPolicyMap),
    onSuccess: (profile) => {
      qc.invalidateQueries({ queryKey: ['profiles', solutionTypeId] })
      setNewName('')
      setComponentPolicyMap({})
      // Auto-trigger profile-level code generation
      triggerCodeGen(profile.id).catch(() => {/* silent */})
    },
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteProfile(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['profiles', solutionTypeId] }),
  })

  const codegenMut = useMutation({
    mutationFn: (profileId: string) => triggerCodeGen(profileId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['profiles', solutionTypeId] }),
  })

  // Per-policy codegen status — keyed by policy id
  const [policyCodegenStatus, setPolicyCodegenStatus] = useState<Record<string, 'idle' | 'pending' | 'done' | 'error'>>({})

  const handlePolicyCodegen = useCallback(async (policyId: string) => {
    setPolicyCodegenStatus((prev) => ({ ...prev, [policyId]: 'pending' }))
    try {
      await generatePolicyCodes(policyId)
      setPolicyCodegenStatus((prev) => ({ ...prev, [policyId]: 'done' }))
      qc.invalidateQueries({ queryKey: ['policies', workspaceId] })
      // Reset back to idle after 4 s so the button is usable again
      setTimeout(() => {
        setPolicyCodegenStatus((prev) => ({ ...prev, [policyId]: 'idle' }))
      }, 4000)
    } catch {
      setPolicyCodegenStatus((prev) => ({ ...prev, [policyId]: 'error' }))
      setTimeout(() => {
        setPolicyCodegenStatus((prev) => ({ ...prev, [policyId]: 'idle' }))
      }, 4000)
    }
  }, [qc, workspaceId])

  const canCreate = !!solutionTypeId && newName.trim().length > 0 &&
    (selectedST?.component_selection ?? []).length > 0 &&
    (selectedST?.component_selection ?? []).every((c: string) => !!componentPolicyMap[c])

  const handleSolutionTypeChange = (id: string) => {
    setSolutionTypeId(id)
    setComponentPolicyMap({})
  }

  return (
    <div>
      <h2 className="text-xl font-bold text-aegis-dark mb-6">Hardening Profiles</h2>

      {/* ── Selector Panel ───────────────────────────────────────────────── */}
      {!workspaceId && (
        <div className="bg-amber-50 border border-amber-200 text-amber-700 text-sm rounded px-4 py-3 mb-6">
          Select a workspace from the header to manage hardening profiles.
        </div>
      )}

      {workspaceId && (
      <div className="bg-white rounded-lg shadow p-5 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Solution Type</label>
            <select
              value={solutionTypeId}
              onChange={(e) => handleSolutionTypeChange(e.target.value)}
              className="w-full border rounded px-2 py-1.5 text-sm"
            >
              <option value="">Select solution type…</option>
              {solutionTypes.map((st: SolutionType) => (
                <option key={st.id} value={st.id}>{st.name}</option>
              ))}
            </select>
            {selectedST?.component_selection && selectedST.component_selection.length > 0 && (
              <p className="text-xs text-gray-400 mt-1">
                {selectedST.component_selection.length} component type(s) configured
              </p>
            )}
          </div>
        </div>
      </div>
      )}

      {/* ── Policies panel (dev stage) ───────────────────────────────────── */}
      {workspaceId && policies.length > 0 && (
        <div className="bg-white rounded-lg shadow p-5 mb-6">
          <h3 className="font-semibold text-aegis-dark mb-3">
            Policies in Workspace
            <span className="ml-2 text-xs font-normal text-gray-400">(development stage — trigger code generation per policy)</span>
          </h3>
          <div className="divide-y">
            {policies.map((p: Policy) => (
              <div key={p.id} className="flex items-center justify-between py-2">
                <div>
                  <span className="font-medium text-sm">{p.name}</span>
                  <span className="ml-2 text-xs text-gray-400 uppercase">{p.standard}</span>
                  <span
                    className={`ml-2 text-xs px-1.5 py-0.5 rounded font-medium ${CODE_STATUS_BADGE[p.code_status ?? 'pending']}`}
                  >
                    {p.code_status ?? 'pending'}
                  </span>
                </div>
                <button
                  onClick={() => handlePolicyCodegen(p.id)}
                  disabled={policyCodegenStatus[p.id] === 'pending'}
                  className={`text-xs rounded px-3 py-1 font-medium transition-colors disabled:opacity-50 ${
                    policyCodegenStatus[p.id] === 'done'
                      ? 'bg-green-600 text-white'
                      : policyCodegenStatus[p.id] === 'error'
                      ? 'bg-red-600 text-white'
                      : 'bg-aegis-dark text-white hover:opacity-90'
                  }`}
                >
                  {policyCodegenStatus[p.id] === 'pending'
                    ? 'Queuing…'
                    : policyCodegenStatus[p.id] === 'done'
                    ? '✓ Queued'
                    : policyCodegenStatus[p.id] === 'error'
                    ? '✗ Failed — retry'
                    : '⚡ Generate Rule Codes'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Create Profile Panel ─────────────────────────────────────────── */}
      {solutionTypeId && (
        <div className="bg-white rounded-lg shadow p-5 mb-6">
          <h3 className="font-semibold text-aegis-dark mb-4">Create Hardening Profile</h3>

          {selectedST && (!selectedST.component_selection || selectedST.component_selection.length === 0) && (
            <div className="bg-amber-50 border border-amber-200 rounded p-3 mb-4">
              <p className="text-xs text-amber-700">
                ⚠ This solution type has no component types configured yet. Go to{' '}
                <button
                  className="underline font-medium"
                  onClick={() => navigate('/solution-types')}
                >
                  Solution Types
                </button>{' '}
                to add components before creating a profile.
              </p>
            </div>
          )}

          {/* Profile name */}
          <div className="mb-4">
            <label className="block text-xs font-medium text-gray-500 mb-1">Profile Name</label>
            <input
              placeholder="e.g. PCAI CIS Baseline"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="w-full md:w-1/2 border rounded px-2 py-1.5 text-sm"
            />
          </div>

          {/* Per-component policy mapping */}
          {(selectedST?.component_selection ?? []).length > 0 && (
            <div className="mb-4">
              <p className="text-xs font-semibold text-gray-600 mb-2">
                Assign a security policy to each component type:
              </p>
              {policies.length === 0 && (
                <p className="text-xs text-amber-500 mb-2">
                  No policies found in this workspace. Upload at least one policy first.
                </p>
              )}
              <div className="divide-y border rounded overflow-hidden">
                {(selectedST!.component_selection as string[]).map((compId: string) => (
                  <div key={compId} className="flex items-center gap-3 px-3 py-2 bg-white">
                    <span className="text-sm font-medium text-aegis-dark w-48 shrink-0 truncate" title={compId}>
                      {compId}
                    </span>
                    <select
                      value={componentPolicyMap[compId] ?? ''}
                      onChange={(e) =>
                        setComponentPolicyMap((prev) => ({
                          ...prev,
                          [compId]: e.target.value,
                        }))
                      }
                      className="flex-1 border rounded px-2 py-1 text-sm"
                    >
                      <option value="">— select policy —</option>
                      {policies.map((p: Policy) => (
                        <option key={p.id} value={p.id}>
                          {p.name} ({p.standard})
                        </option>
                      ))}
                    </select>
                    {componentPolicyMap[compId] ? (
                      <span className="text-green-500 text-sm shrink-0">✓</span>
                    ) : (
                      <span className="text-gray-300 text-sm shrink-0">○</span>
                    )}
                  </div>
                ))}
              </div>
              {(selectedST!.component_selection as string[]).some((c: string) => !componentPolicyMap[c]) && (
                <p className="text-xs text-amber-500 mt-1">
                  All components must have a policy assigned before creating the profile.
                </p>
              )}
            </div>
          )}

          <button
            onClick={() => createMut.mutate()}
            disabled={!canCreate || createMut.isPending}
            className="bg-aegis-dark text-white rounded px-5 py-2 text-sm disabled:opacity-50 hover:opacity-90 transition-opacity"
          >
            {createMut.isPending ? 'Creating…' : 'Create Hardening Profile'}
          </button>
          {createMut.isSuccess && (
            <p className="text-xs text-green-600 mt-2">
              Profile created. Code generation triggered — monitor progress in the editor.
            </p>
          )}
          {createMut.isError && (
            <p className="text-xs text-red-600 mt-2">
              Failed to create profile. Please try again.
            </p>
          )}
        </div>
      )}

      {/* ── Profiles List ────────────────────────────────────────────────── */}
      {solutionTypeId && (
        <>
          <h3 className="font-semibold text-aegis-dark mb-3">
            Profiles for "{selectedST?.name}"
          </h3>

          {profilesLoading && (
            <p className="text-sm text-gray-400">Loading profiles…</p>
          )}

          {!profilesLoading && profiles.length === 0 && (
            <div className="bg-white rounded-lg shadow p-6 text-center">
              <p className="text-sm text-gray-400 mb-1">No hardening profiles yet.</p>
              <p className="text-xs text-gray-300">
                Create one above by choosing a policy — AEGIS will generate evaluation,
                remediation and rollback code for each rule × component combination.
              </p>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {profiles.map((profile: HardeningProfile) => {
              const cpm = profile.component_policy_map ?? {}
              return (
                <div key={profile.id} className="bg-white rounded-lg shadow p-4 flex flex-col gap-2">
                  <div className="flex items-start justify-between">
                    <div className="font-semibold text-aegis-dark">{profile.name}</div>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize ${STATUS_BADGE[profile.status] ?? 'bg-gray-100 text-gray-600'}`}
                    >
                      {profile.status}
                    </span>
                  </div>

                  {/* Component → Policy mapping summary */}
                  {Object.keys(cpm).length > 0 && (
                    <div className="text-xs text-gray-500 space-y-0.5">
                      {Object.entries(cpm).map(([comp, polId]) => {
                        const pol = policyMap[polId]
                        return (
                          <div key={comp} className="flex gap-1 items-center">
                            <span className="font-medium text-aegis-dark truncate max-w-[100px]" title={comp}>{comp}</span>
                            <span className="text-gray-300">→</span>
                            <span className="truncate" title={pol?.name ?? polId}>{pol?.name ?? polId}</span>
                          </div>
                        )
                      })}
                    </div>
                  )}

                  <div className="text-xs text-gray-300 font-mono truncate">{profile.id}</div>

                  <div className="flex gap-2 mt-auto pt-2">
                    <button
                      onClick={() => navigate(`/profiles/${profile.id}`)}
                      className="flex-1 text-sm bg-aegis-dark text-white rounded px-3 py-1 hover:opacity-90 transition-opacity"
                    >
                      Edit / Review Codes
                    </button>
                    <button
                      onClick={() => codegenMut.mutate(profile.id)}
                      disabled={codegenMut.isPending}
                      title="Re-trigger LLM code generation for pending rules"
                      className="text-sm bg-blue-600 text-white rounded px-3 py-1 hover:bg-blue-700 disabled:opacity-50"
                    >
                      ⚡
                    </button>
                    <button
                      onClick={() => {
                        if (window.confirm(`Delete profile "${profile.name}"?`)) {
                          deleteMut.mutate(profile.id)
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
        </>
      )}

      {!solutionTypeId && !workspaceId && (
        <p className="text-sm text-gray-400">Select a workspace and solution type to manage hardening profiles.</p>
      )}
      {workspaceId && !solutionTypeId && (
        <p className="text-sm text-gray-400">Select a solution type to view and create hardening profiles.</p>
      )}
    </div>
  )
}
