import { useState, useCallback, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  listSolutionTypes,
  listPolicies,
  listAllProfiles,
  createProfile,
  deleteProfile,
  triggerCodeGen,
} from '../api/endpoints'
import { useWorkspace } from '../context/WorkspaceContext'
import type { HardeningProfile, Policy, SolutionType } from '../types'

// ── Component ID helpers ─────────────────────────────────────────────────────

const ID_PREFIX_MAP: { prefix: string; category: string; suffix: string }[] = [
  { prefix: 'server-', category: 'Server',          suffix: '— Host OS' },
  { prefix: 'ilo-',    category: 'iLO',             suffix: '— iLO'     },
  { prefix: 'switch-', category: 'Network Switch',  suffix: ''          },
  { prefix: 'pdu-',    category: 'PDU',             suffix: ''          },
  { prefix: 'storage-',category: 'Storage',         suffix: ''          },
  { prefix: 'vm-',     category: 'Virtual Machine', suffix: ''          },
]

const CATEGORY_BADGE: Record<string, string> = {
  'Server':          'bg-green-100 text-green-800',
  'iLO':             'bg-orange-100 text-orange-800',
  'Network Switch':  'bg-blue-100 text-blue-800',
  'PDU':             'bg-yellow-100 text-yellow-800',
  'Storage':         'bg-purple-100 text-purple-800',
  'Virtual Machine': 'bg-indigo-100 text-indigo-800',
}

function humanizeCompId(id: string): { label: string; category: string } {
  for (const { prefix, category, suffix } of ID_PREFIX_MAP) {
    if (id.startsWith(prefix)) {
      const rest = id.slice(prefix.length)
      let label: string
      if (prefix === 'server-' || prefix === 'ilo-') {
        const dash = rest.lastIndexOf('-')
        if (dash > 0 && dash < rest.length - 1) {
          const type = rest.slice(0, dash).replace(/-/g, ' ')
          const role = rest.slice(dash + 1)
          label = `${type} (${role})`
        } else {
          label = rest.replace(/-/g, ' ')
        }
      } else if (prefix === 'vm-') {
        const dash = rest.indexOf('-')
        if (dash !== -1) {
          label = `${rest.slice(0, dash)} (${rest.slice(dash + 1)})`
        } else {
          label = rest
        }
      } else {
        label = rest.replace(/-/g, ' ')
      }
      return { label: suffix ? `${label} ${suffix}` : label, category }
    }
  }
  return { label: id, category: 'Other' }
}

// ── Policy auto-matching ─────────────────────────────────────────────────────

// Keywords per component category used to score policy relevance
const COMPONENT_POLICY_KEYWORDS: Record<string, string[]> = {
  'server-':  ['ubuntu', 'linux', 'server', 'host', 'os', 'rhel', 'centos', 'debian', 'windows'],
  'ilo-':     ['ilo', 'bmc', 'baseboard', 'redfish', 'out-of-band', 'hpe ilo'],
  'switch-':  ['switch', 'network', 'aruba', 'cisco', 'juniper', 'nexus', 'mellanox', 'cumulus'],
  'pdu-':     ['pdu', 'power distribution', 'powerstrip'],
  'storage-': ['storage', 'alletra', 'san', 'nas', 'vastdata'],
  'vm-':      ['vmware', 'esxi', 'virtual', 'vm', 'hypervisor', 'vsphere'],
}

function findBestPolicy(compId: string, policies: Policy[]): string {
  if (policies.length === 0) return ''
  const prefix = Object.keys(COMPONENT_POLICY_KEYWORDS).find((p) => compId.startsWith(p))
  if (!prefix) return ''
  const keywords = COMPONENT_POLICY_KEYWORDS[prefix]
  let bestId = ''
  let bestScore = 0
  for (const policy of policies) {
    const hay = `${policy.name} ${policy.standard} ${policy.description ?? ''}`.toLowerCase()
    const score = keywords.reduce((acc, kw) => acc + (hay.includes(kw) ? 1 : 0), 0)
    if (score > bestScore) {
      bestScore = score
      bestId = policy.id
    }
  }
  return bestId
}

const STATUS_BADGE: Record<string, string> = {
  draft:      'bg-gray-100 text-gray-600',
  generating: 'bg-yellow-100 text-yellow-700',
  ready:      'bg-green-100 text-green-700',
}

export default function HardeningProfileManagerPage() {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const { selectedWorkspace } = useWorkspace()
  const workspaceId = selectedWorkspace?.id ?? ''

  const [showCreateForm, setShowCreateForm]   = useState(false)
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
    queryKey: ['profiles', workspaceId],
    queryFn: () => listAllProfiles(workspaceId),
    enabled: !!workspaceId,
  })

  const policyMap = Object.fromEntries(policies.map((p: Policy) => [p.id, p]))
  const selectedST = solutionTypes.find((s: SolutionType) => s.id === solutionTypeId)

  // ── Mutations ────────────────────────────────────────────────────────────
  const createMut = useMutation({
    mutationFn: () => createProfile(newName.trim(), solutionTypeId, componentPolicyMap),
    onSuccess: (profile) => {
      qc.invalidateQueries({ queryKey: ['profiles', workspaceId] })
      setNewName('')
      setComponentPolicyMap({})
      setShowCreateForm(false)
      // Auto-trigger profile-level code generation
      triggerCodeGen(profile.id).catch(() => {/* silent */})
    },
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteProfile(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['profiles', workspaceId] }),
  })

  const codegenMut = useMutation({
    mutationFn: (profileId: string) => triggerCodeGen(profileId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['profiles', workspaceId] }),
  })

  const canCreate = !!solutionTypeId && newName.trim().length > 0 &&
    (selectedST?.component_selection ?? []).length > 0 &&
    (selectedST?.component_selection ?? []).every((c: string) => !!componentPolicyMap[c])

  // Build default policy map for a given component selection + available policies
  const buildDefaultPolicyMap = useCallback(
    (componentIds: string[]): Record<string, string> => {
      const map: Record<string, string> = {}
      for (const compId of componentIds) {
        const best = findBestPolicy(compId, policies)
        if (best) map[compId] = best
      }
      return map
    },
    [policies],
  )

  const handleSolutionTypeChange = (id: string) => {
    setSolutionTypeId(id)
    const st = solutionTypes.find((s: SolutionType) => s.id === id)
    setComponentPolicyMap(buildDefaultPolicyMap(st?.component_selection ?? []))
  }

  // Re-apply defaults when policies finish loading (they may arrive after ST selection)
  useEffect(() => {
    if (!selectedST?.component_selection?.length || !policies.length) return
    setComponentPolicyMap((prev) => {
      // Only fill in components that have no assignment yet
      const updated = { ...prev }
      let changed = false
      for (const compId of selectedST.component_selection as string[]) {
        if (!updated[compId]) {
          const best = findBestPolicy(compId, policies)
          if (best) { updated[compId] = best; changed = true }
        }
      }
      return changed ? updated : prev
    })
  }, [policies, selectedST])

  const handleCancel = () => {
    setShowCreateForm(false)
    setSolutionTypeId('')
    setNewName('')
    setComponentPolicyMap({})
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-aegis-dark">Hardening Profiles</h2>
        {workspaceId && (
          <button
            onClick={() => showCreateForm ? handleCancel() : setShowCreateForm(true)}
            className="bg-aegis-dark text-white rounded px-4 py-2 text-sm font-medium hover:opacity-90 transition-opacity flex items-center gap-2"
          >
            {showCreateForm ? '✕ Cancel' : '+ Create New Profile'}
          </button>
        )}
      </div>

      {!workspaceId && (
        <div className="bg-amber-50 border border-amber-200 text-amber-700 text-sm rounded px-4 py-3 mb-6">
          Select a workspace from the header to manage hardening profiles.
        </div>
      )}

      {/* ── Create Profile Panel ─────────────────────────────────────────── */}
      {workspaceId && showCreateForm && (
        <div className="bg-white rounded-lg shadow p-5 mb-8 border border-aegis-dark/20">
          <h3 className="font-semibold text-aegis-dark mb-4">Create New Hardening Profile</h3>

          {/* Solution Type selector */}
          <div className="mb-4">
            <label className="block text-xs font-medium text-gray-500 mb-1">Solution Type</label>
            <select
              value={solutionTypeId}
              onChange={(e) => handleSolutionTypeChange(e.target.value)}
              className="w-full md:w-1/2 border rounded px-2 py-1.5 text-sm"
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

          {solutionTypeId && selectedST && (!selectedST.component_selection || selectedST.component_selection.length === 0) && (
            <div className="bg-amber-50 border border-amber-200 rounded p-3 mb-4">
              <p className="text-xs text-amber-700">
                ⚠ This solution type has no component types configured yet. Go to{' '}
                <button className="underline font-medium" onClick={() => navigate('/solution-types')}>
                  Solution Types
                </button>{' '}
                to add components before creating a profile.
              </p>
            </div>
          )}

          {/* Profile name */}
          {solutionTypeId && (
            <div className="mb-4">
              <label className="block text-xs font-medium text-gray-500 mb-1">Profile Name</label>
              <input
                placeholder="e.g. PCAI CIS Baseline"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="w-full md:w-1/2 border rounded px-2 py-1.5 text-sm"
              />
            </div>
          )}

          {/* Per-component policy mapping */}
          {solutionTypeId && (selectedST?.component_selection ?? []).length > 0 && (
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
                {(selectedST!.component_selection as string[]).map((compId: string) => {
                  const { label, category } = humanizeCompId(compId)
                  const badgeClass = CATEGORY_BADGE[category] ?? 'bg-gray-100 text-gray-700'
                  return (
                    <div key={compId} className="flex items-center gap-3 px-3 py-2 bg-white">
                      <div className="flex items-center gap-2 w-56 shrink-0">
                        <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${badgeClass}`}>
                          {category}
                        </span>
                        <span className="text-sm font-medium text-aegis-dark truncate" title={compId}>
                          {label}
                        </span>
                      </div>
                      <select
                        value={componentPolicyMap[compId] ?? ''}
                        onChange={(e) =>
                          setComponentPolicyMap((prev) => ({ ...prev, [compId]: e.target.value }))
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
                  )
                })}
              </div>
              {(selectedST!.component_selection as string[]).some((c: string) => !componentPolicyMap[c]) && (
                <p className="text-xs text-amber-500 mt-1">
                  All components must have a policy assigned before creating the profile.
                </p>
              )}
            </div>
          )}

          {solutionTypeId && (
            <>
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
                <p className="text-xs text-red-600 mt-2">Failed to create profile. Please try again.</p>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Existing Profiles Tiles ──────────────────────────────────────── */}
      {workspaceId && (
        <>
          {profilesLoading && (
            <p className="text-sm text-gray-400">Loading profiles…</p>
          )}

          {!profilesLoading && (() => {
            const visibleProfiles = solutionTypeId
              ? profiles.filter((p: HardeningProfile) => p.solution_type_id === solutionTypeId)
              : profiles
            const sectionLabel = solutionTypeId && selectedST
              ? `Profiles for "${selectedST.name}"`
              : 'All Hardening Profiles'

            if (visibleProfiles.length === 0) {
              return (
                <div className="bg-white rounded-lg shadow p-10 text-center">
                  <p className="text-gray-400 text-sm mb-1">
                    {solutionTypeId ? `No profiles yet for "${selectedST?.name}".` : 'No hardening profiles yet.'}
                  </p>
                  <p className="text-xs text-gray-300 mb-4">
                    Create one using the button above — AEGIS will generate evaluation,
                    remediation and rollback code for each rule × component combination.
                  </p>
                  <button
                    onClick={() => setShowCreateForm(true)}
                    className="bg-aegis-dark text-white rounded px-4 py-2 text-sm hover:opacity-90 transition-opacity"
                  >
                    + Create New Profile
                  </button>
                </div>
              )
            }

            return (
              <>
                <h3 className="font-semibold text-aegis-dark mb-3 text-sm">{sectionLabel}</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                  {visibleProfiles.map((profile: HardeningProfile) => {
                const cpm = profile.component_policy_map ?? {}
                // find the solution type name for this profile
                const profileST = solutionTypes.find((s: SolutionType) => s.id === profile.solution_type_id)
                return (
                  <div key={profile.id} className="bg-white rounded-lg shadow p-4 flex flex-col gap-2 hover:shadow-md transition-shadow">
                    <div className="flex items-start justify-between">
                      <div className="font-semibold text-aegis-dark">{profile.name}</div>
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize ${STATUS_BADGE[profile.status] ?? 'bg-gray-100 text-gray-600'}`}
                      >
                        {profile.status}
                      </span>
                    </div>

                    {profileST && (
                      <div className="text-xs text-gray-400">
                        <span className="font-medium text-gray-600">Solution Type:</span> {profileST.name}
                      </div>
                    )}

                    {/* Component → Policy mapping summary */}
                    {Object.keys(cpm).length > 0 && (
                      <div className="text-xs text-gray-500 space-y-0.5">
                        {Object.entries(cpm).map(([comp, polId]) => {
                          const pol = policyMap[polId]
                          const { label, category } = humanizeCompId(comp)
                          const badgeClass = CATEGORY_BADGE[category] ?? 'bg-gray-100 text-gray-700'
                          return (
                            <div key={comp} className="flex gap-1 items-center">
                              <span className={`text-xs px-1 py-0.5 rounded ${badgeClass} shrink-0`}>{category}</span>
                              <span className="font-medium text-aegis-dark truncate max-w-[90px]" title={comp}>{label}</span>
                              <span className="text-gray-300">→</span>
                              <span className="truncate" title={pol?.name ?? polId}>{pol?.name ?? polId}</span>
                            </div>
                          )
                        })}
                      </div>
                    )}

                    <div className="flex gap-2 mt-auto pt-2">
                      <button
                        onClick={() => navigate(`/profiles/${profile.id}`)}
                        className="flex-1 text-sm bg-aegis-dark text-white rounded px-3 py-1.5 hover:opacity-90 transition-opacity"
                      >
                        Edit / Review Codes
                      </button>
                      <button
                        onClick={() => codegenMut.mutate(profile.id)}
                        disabled={codegenMut.isPending}
                        title="Re-trigger LLM code generation for pending rules"
                        className="text-sm bg-blue-600 text-white rounded px-3 py-1.5 hover:bg-blue-700 disabled:opacity-50"
                      >
                        ⚡
                      </button>
                      <button
                        onClick={() => {
                          if (window.confirm(`Delete profile "${profile.name}"?`)) {
                            deleteMut.mutate(profile.id)
                          }
                        }}
                        className="text-sm bg-red-600 text-white rounded px-3 py-1.5 hover:bg-red-700"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
              </>
            )
          })()}
        </>
      )}
    </div>
  )
}
