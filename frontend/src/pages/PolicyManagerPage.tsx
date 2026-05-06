import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { listPolicies, listPolicyRules, deletePolicy, listProfiles, createProfile, deleteProfile, promoteProfile, newProfileVersion, updateProfile } from '../api/endpoints'
import { useWorkspace } from '../context/WorkspaceContext'
import type { Policy, PolicyRule, PolicyProfile } from '../types'

const SEVERITY_COLOR: Record<string, string> = {
  critical: '#c0392b', high: '#e67e22', medium: '#f39c12',
  low: '#27ae60', informational: '#2980b9',
}

export default function PolicyManagerPage() {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const { selectedWorkspace } = useWorkspace()
  const workspaceId = selectedWorkspace?.id ?? ''
  const [selectedPolicy, setSelectedPolicy] = useState<Policy | null>(null)
  const [showImport, setShowImport] = useState(false)
  const [showCreateProfile, setShowCreateProfile] = useState(false)
  const [viewingProfile, setViewingProfile] = useState<PolicyProfile | null>(null)

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

  const { data: profiles = [] } = useQuery({
    queryKey: ['profiles', selectedPolicy?.id],
    queryFn: () => listProfiles(selectedPolicy!.id),
    enabled: !!selectedPolicy,
  })

  const deleteMut = useMutation({
    mutationFn: (policyId: string) => deletePolicy(policyId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['policies', workspaceId] })
      setSelectedPolicy(null)
    },
  })

  const promoteMut = useMutation({
    mutationFn: (profileId: string) => promoteProfile(profileId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['profiles', selectedPolicy?.id] }),
  })

  const deleteProfileMut = useMutation({
    mutationFn: (profileId: string) => deleteProfile(profileId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['profiles', selectedPolicy?.id] }),
  })

  const newVersionMut = useMutation({
    mutationFn: (profileId: string) => newProfileVersion(profileId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['profiles', selectedPolicy?.id] }),
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
                onClick={() => navigate(`/policies/${selectedPolicy.id}/implementation`)}
                className="text-xs bg-aegis-blue text-white rounded px-2 py-1"
              >
                Review Implementation
              </button>
              <button
                onClick={() => deleteMut.mutate(selectedPolicy.id)}
                className="text-xs text-aegis-red hover:underline ml-auto"
              >
                Delete Policy
              </button>
            </div>
            <RulesTable rules={rules} />

            {/* Profiles Section */}
            <div className="mt-6">
              <div className="flex items-center gap-3 mb-3">
                <h4 className="font-semibold text-sm text-aegis-dark">Profiles</h4>
                <button
                  onClick={() => setShowCreateProfile(true)}
                  className="text-xs bg-aegis-dark text-white rounded px-2 py-1"
                >
                  + Create Profile
                </button>
              </div>
              {profiles.length === 0 ? (
                <p className="text-xs text-gray-400 italic">No profiles yet. Create one to get started.</p>
              ) : (
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {profiles.map((profile) => (
                    <ProfileCard
                      key={profile.id}
                      profile={profile}
                      onPromote={() => promoteMut.mutate(profile.id)}
                      onDelete={() => deleteProfileMut.mutate(profile.id)}
                      onNewVersion={() => newVersionMut.mutate(profile.id)}
                      onClick={() => setViewingProfile(profile)}
                    />
                  ))}
                </div>
              )}
            </div>
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

      {/* Create Profile Modal */}
      {showCreateProfile && selectedPolicy && (
        <CreateProfileModal
          policyId={selectedPolicy.id}
          rules={rules}
          onClose={() => setShowCreateProfile(false)}
          onCreated={() => {
            qc.invalidateQueries({ queryKey: ['profiles', selectedPolicy.id] })
            setShowCreateProfile(false)
          }}
        />
      )}

      {/* Profile Rules Modal */}
      {viewingProfile && (
        <ProfileRulesModal
          profile={viewingProfile}
          allRules={rules}
          onClose={() => setViewingProfile(null)}
          onUpdated={() => {
            qc.invalidateQueries({ queryKey: ['profiles', selectedPolicy?.id] })
            setViewingProfile(null)
          }}
          onDelete={() => {
            deleteProfileMut.mutate(viewingProfile.id)
            setViewingProfile(null)
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
            {['Rule ID', 'Title', 'Severity', 'Category', 'Status'].map((h) => (
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
              <td className="px-3 py-2">
                <span className={`text-xs px-1.5 py-0.5 rounded ${
                  r.code_status === 'approved' ? 'bg-green-100 text-green-700' :
                  r.code_status === 'rejected' ? 'bg-red-100 text-red-700' :
                  r.code_status === 'generated' ? 'bg-blue-100 text-blue-700' :
                  'bg-gray-100 text-gray-600'
                }`}>
                  {r.code_status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

const PROFILE_STATUS_STYLE: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700',
  in_review: 'bg-orange-100 text-orange-700',
  approved: 'bg-blue-100 text-blue-700',
  locked: 'bg-green-100 text-green-700',
}

function ProfileCard({ profile, onPromote, onDelete, onNewVersion, onClick }: {
  profile: PolicyProfile
  onPromote: () => void
  onDelete: () => void
  onNewVersion: () => void
  onClick: () => void
}) {
  return (
    <div
      className="bg-white border rounded-lg p-3 shadow-sm cursor-pointer hover:border-aegis-blue transition-colors"
      onClick={onClick}
    >
      <div className="flex items-center gap-2 mb-2">
        <span className="font-medium text-sm truncate flex-1">{profile.name}</span>
        <span className={`text-[10px] px-1.5 py-0.5 rounded ${PROFILE_STATUS_STYLE[profile.status] ?? 'bg-gray-100'}`}>
          {profile.status}
        </span>
      </div>
      <div className="text-xs text-slate-500 mb-2">
        {profile.profile_type === 'tailored' ? 'Tailored' : 'Standard'} · v{profile.version}
      </div>
      <div className="flex items-center gap-2 text-xs mb-2">
        <span className="text-slate-600">{profile.approved_count}/{profile.rule_count} approved</span>
        <div className="flex-1 bg-gray-200 rounded-full h-1.5">
          <div
            className="bg-green-500 h-1.5 rounded-full"
            style={{ width: `${profile.rule_count > 0 ? (profile.approved_count / profile.rule_count) * 100 : 0}%` }}
          />
        </div>
      </div>
      <div className="flex gap-1 flex-wrap" onClick={(e) => e.stopPropagation()}>
        {profile.status === 'draft' && (
          <>
            <button
              onClick={onPromote}
              disabled={profile.approved_count < profile.rule_count}
              className="text-[10px] px-2 py-0.5 bg-green-600 text-white rounded disabled:opacity-40"
            >
              Promote
            </button>
            <button onClick={onDelete} className="text-[10px] px-2 py-0.5 bg-red-600 text-white rounded">
              Delete
            </button>
          </>
        )}
        {profile.status === 'locked' && (
          <>
            <button onClick={onNewVersion} className="text-[10px] px-2 py-0.5 bg-indigo-600 text-white rounded">
              New Version
            </button>
            <button onClick={onDelete} className="text-[10px] px-2 py-0.5 bg-red-600 text-white rounded">
              Delete
            </button>
          </>
        )}
      </div>
    </div>
  )
}

function CreateProfileModal({ policyId, rules, onClose, onCreated }: {
  policyId: string
  rules: PolicyRule[]
  onClose: () => void
  onCreated: () => void
}) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [profileType, setProfileType] = useState<'standard' | 'tailored'>('standard')
  const [selectedRuleIds, setSelectedRuleIds] = useState<Set<string>>(new Set())

  const createMut = useMutation({
    mutationFn: () =>
      createProfile(policyId, {
        name,
        description: description || undefined,
        profile_type: profileType,
        included_rule_ids: profileType === 'tailored' ? Array.from(selectedRuleIds) : undefined,
      }),
    onSuccess: onCreated,
  })

  const toggleRule = (ruleId: string) => {
    setSelectedRuleIds((prev) => {
      const next = new Set(prev)
      next.has(ruleId) ? next.delete(ruleId) : next.add(ruleId)
      return next
    })
  }

  // Group rules by category for selection
  const categories = (() => {
    const map = new Map<string, PolicyRule[]>()
    for (const r of rules) {
      const cat = r.category || 'Uncategorized'
      if (!map.has(cat)) map.set(cat, [])
      map.get(cat)!.push(r)
    }
    return Array.from(map.entries())
  })()

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6 max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-bold text-aegis-dark mb-4">Create Profile</h3>

        <div className="flex flex-col gap-3 text-sm">
          <label className="flex flex-col gap-1">
            <span className="font-medium">Name</span>
            <input value={name} onChange={(e) => setName(e.target.value)} className="border rounded px-3 py-2" placeholder="e.g. CIS L1 Standard" />
          </label>

          <label className="flex flex-col gap-1">
            <span className="font-medium">Description</span>
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} className="border rounded px-3 py-2" rows={2} />
          </label>

          <div className="flex gap-4">
            <label className="flex items-center gap-2">
              <input type="radio" checked={profileType === 'standard'} onChange={() => setProfileType('standard')} />
              <span>Standard (all rules)</span>
            </label>
            <label className="flex items-center gap-2">
              <input type="radio" checked={profileType === 'tailored'} onChange={() => setProfileType('tailored')} />
              <span>Tailored (select rules)</span>
            </label>
          </div>

          {profileType === 'tailored' && (
            <div className="border rounded p-3 max-h-60 overflow-y-auto">
              <div className="flex gap-2 mb-2">
                <button onClick={() => setSelectedRuleIds(new Set(rules.map((r) => r.id)))} className="text-xs text-aegis-blue hover:underline">Select All</button>
                <button onClick={() => setSelectedRuleIds(new Set())} className="text-xs text-aegis-blue hover:underline">Deselect All</button>
              </div>
              {categories.map(([cat, catRules]) => (
                <div key={cat} className="mb-2">
                  <div className="text-xs font-semibold text-slate-600 mb-1">{cat}</div>
                  {catRules.map((r) => (
                    <label key={r.id} className="flex items-center gap-2 text-xs py-0.5">
                      <input type="checkbox" checked={selectedRuleIds.has(r.id)} onChange={() => toggleRule(r.id)} />
                      <span className="truncate">{r.rule_id} — {r.title}</span>
                    </label>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="flex gap-3 mt-4">
          <button onClick={onClose} className="flex-1 border rounded py-2 text-sm">Cancel</button>
          <button
            onClick={() => createMut.mutate()}
            disabled={!name || createMut.isPending || (profileType === 'tailored' && selectedRuleIds.size === 0)}
            className="flex-1 bg-aegis-dark text-white rounded py-2 text-sm disabled:opacity-50"
          >
            Create
          </button>
        </div>
        {createMut.isError && <p className="text-xs text-red-600 mt-2">Failed to create profile.</p>}
      </div>
    </div>
  )
}

function ProfileRulesModal({ profile, allRules, onClose, onUpdated, onDelete }: {
  profile: PolicyProfile
  allRules: PolicyRule[]
  onClose: () => void
  onUpdated: () => void
  onDelete: () => void
}) {
  const isDraft = profile.status === 'draft'
  const [editing, setEditing] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(
    () => new Set(profile.included_rule_ids ?? allRules.map((r) => r.id))
  )

  const saveMut = useMutation({
    mutationFn: () => updateProfile(profile.id, { included_rule_ids: Array.from(selectedIds) }),
    onSuccess: () => {
      setEditing(false)
      onUpdated()
    },
  })

  const toggleRule = (ruleId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      next.has(ruleId) ? next.delete(ruleId) : next.add(ruleId)
      return next
    })
  }

  const displayRules = editing ? allRules : (
    profile.profile_type === 'tailored' && profile.included_rule_ids
      ? allRules.filter((r) => profile.included_rule_ids!.includes(r.id))
      : allRules
  )

  const categories = (() => {
    const map = new Map<string, PolicyRule[]>()
    for (const r of displayRules) {
      const cat = r.category || 'Uncategorized'
      if (!map.has(cat)) map.set(cat, [])
      map.get(cat)!.push(r)
    }
    return Array.from(map.entries()).sort((a, b) => a[0].localeCompare(b[0]))
  })()

  const approvedCount = displayRules.filter((r) => r.code_status === 'approved').length

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div
        className="bg-white rounded-xl shadow-xl w-full max-w-2xl p-6 max-h-[85vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-bold text-aegis-dark">{profile.name}</h3>
            <p className="text-xs text-slate-500">
              {profile.profile_type === 'tailored' ? 'Tailored' : 'Standard'} · v{profile.version} ·{' '}
              <span className={`font-semibold ${PROFILE_STATUS_STYLE[profile.status]?.includes('green') ? 'text-green-700' : ''}`}>
                {profile.status}
              </span>
              {' '}· {approvedCount}/{displayRules.length} approved
              {editing && <span className="ml-2 text-amber-600 font-semibold">· Editing ({selectedIds.size} selected)</span>}
            </p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700 text-xl leading-none">&times;</button>
        </div>

        {profile.description && (
          <p className="text-sm text-slate-600 mb-3">{profile.description}</p>
        )}

        {/* Edit controls for draft profiles */}
        {isDraft && (
          <div className="flex items-center gap-2 mb-3">
            {!editing ? (
              <button
                onClick={() => setEditing(true)}
                className="text-xs bg-aegis-dark text-white rounded px-3 py-1 hover:opacity-90"
              >
                ✏️ Customize Rules
              </button>
            ) : (
              <>
                <button
                  onClick={() => setSelectedIds(new Set(allRules.map((r) => r.id)))}
                  className="text-xs text-aegis-blue hover:underline"
                >
                  Select All
                </button>
                <button
                  onClick={() => setSelectedIds(new Set())}
                  className="text-xs text-aegis-blue hover:underline"
                >
                  Deselect All
                </button>
                <div className="ml-auto flex gap-2">
                  <button
                    onClick={() => { setEditing(false); setSelectedIds(new Set(profile.included_rule_ids ?? allRules.map((r) => r.id))) }}
                    className="text-xs border rounded px-3 py-1 text-gray-600 hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => saveMut.mutate()}
                    disabled={saveMut.isPending || selectedIds.size === 0}
                    className="text-xs bg-green-600 text-white rounded px-3 py-1 disabled:opacity-50 hover:bg-green-700"
                  >
                    {saveMut.isPending ? 'Saving…' : `Save (${selectedIds.size} rules)`}
                  </button>
                </div>
              </>
            )}
          </div>
        )}
        {saveMut.isError && <p className="text-xs text-red-600 mb-2">Failed to save rule selection.</p>}

        <div className="flex-1 overflow-y-auto">
          {categories.map(([cat, catRules]) => (
            <div key={cat} className="mb-4">
              <div className="flex items-center gap-2 mb-2">
                <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wide">{cat}</h4>
                <span className="text-[10px] text-slate-400">{catRules.length} rules</span>
                {editing && (
                  <button
                    onClick={() => {
                      const catIds = catRules.map((r) => r.id)
                      const allSelected = catIds.every((id) => selectedIds.has(id))
                      setSelectedIds((prev) => {
                        const next = new Set(prev)
                        catIds.forEach((id) => allSelected ? next.delete(id) : next.add(id))
                        return next
                      })
                    }}
                    className="text-[10px] text-aegis-blue hover:underline"
                  >
                    {catRules.every((r) => selectedIds.has(r.id)) ? 'deselect all' : 'select all'}
                  </button>
                )}
              </div>
              <div className="divide-y divide-gray-100 border rounded">
                {catRules.map((r) => (
                  <div
                    key={r.id}
                    className={`flex items-center gap-3 px-3 py-2 text-xs ${editing && !selectedIds.has(r.id) ? 'opacity-40' : ''}`}
                    onClick={editing ? () => toggleRule(r.id) : undefined}
                    style={editing ? { cursor: 'pointer' } : undefined}
                  >
                    {editing ? (
                      <input
                        type="checkbox"
                        checked={selectedIds.has(r.id)}
                        onChange={() => toggleRule(r.id)}
                        onClick={(e) => e.stopPropagation()}
                        className="shrink-0"
                      />
                    ) : (
                      <span className={`w-2 h-2 rounded-full shrink-0 ${
                        r.code_status === 'approved' ? 'bg-green-500' :
                        r.code_status === 'rejected' ? 'bg-red-500' :
                        r.code_status === 'generated' ? 'bg-blue-500' :
                        'bg-gray-400'
                      }`} />
                    )}
                    <span className="font-mono text-slate-500 shrink-0 w-28 truncate" title={r.rule_id}>{r.rule_id}</span>
                    <span className="flex-1 truncate">{r.title}</span>
                    <span className="font-semibold shrink-0" style={{ color: SEVERITY_COLOR[r.severity] }}>
                      {r.severity}
                    </span>
                    <span className={`shrink-0 px-1.5 py-0.5 rounded ${
                      r.code_status === 'approved' ? 'bg-green-100 text-green-700' :
                      r.code_status === 'rejected' ? 'bg-red-100 text-red-700' :
                      r.code_status === 'generated' ? 'bg-blue-100 text-blue-700' :
                      'bg-gray-100 text-gray-600'
                    }`}>
                      {r.code_status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))}
          {displayRules.length === 0 && (
            <p className="text-sm text-gray-400 italic text-center py-8">No rules in this profile.</p>
          )}
        </div>
      </div>
    </div>
  )
}
