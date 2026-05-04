import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import MonacoEditor from '@monaco-editor/react'
import { getProfile, listProfileRules, updateRuleCode, approveRule, rejectRule, triggerCodeGen, deleteProfile } from '../api/endpoints'
import type { ProfileRule } from '../types'

const STATUS_COLOR: Record<string, string> = {
  pending: '#7f8c8d',
  generated: '#2980b9',
  reviewed: '#e67e22',
  approved: '#27ae60',
  rejected: '#c0392b',
}

type CodeTab = 'evaluation_code' | 'remediation_code' | 'rollback_code'
const CODE_TABS: { key: CodeTab; label: string }[] = [
  { key: 'evaluation_code', label: 'Evaluate' },
  { key: 'remediation_code', label: 'Remediate' },
  { key: 'rollback_code', label: 'Rollback' },
]

export default function HardeningProfileEditorPage() {
  const { profileId } = useParams<{ profileId: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: profile } = useQuery({
    queryKey: ['profile', profileId],
    queryFn: () => getProfile(profileId!),
    enabled: !!profileId,
  })

  const { data: rules = [] } = useQuery({
    queryKey: ['profile-rules', profileId],
    queryFn: () => listProfileRules(profileId!),
    enabled: !!profileId,
  })

  const [selectedRule, setSelectedRule] = useState<ProfileRule | null>(null)
  const [activeTab, setActiveTab] = useState<CodeTab>('evaluation_code')
  const [editedCode, setEditedCode] = useState('')
  const wsRef = useRef<WebSocket | null>(null)
  const [streaming, setStreaming] = useState(false)
  const [streamLog, setStreamLog] = useState<string[]>([])

  useEffect(() => {
    if (selectedRule) {
      setEditedCode(selectedRule[activeTab] ?? '')
    }
  }, [selectedRule, activeTab])

  const saveMut = useMutation({
    mutationFn: () => updateRuleCode(profileId!, selectedRule!.id, { [activeTab]: editedCode }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['profile-rules', profileId] }),
  })

  const approveMut = useMutation({
    mutationFn: () => approveRule(profileId!, selectedRule!.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['profile-rules', profileId] }),
  })

  const rejectMut = useMutation({
    mutationFn: () => rejectRule(profileId!, selectedRule!.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['profile-rules', profileId] }),
  })

  const triggerGenMut = useMutation({
    mutationFn: () => triggerCodeGen(profileId!),
    onSuccess: (data) => {
      setStreaming(true)
      setStreamLog([])
      const token = localStorage.getItem('aegis_token') ?? ''
      const ws = new WebSocket(`ws://${location.host}/api/v1/ws/codegen/${profileId}?token=${token}`)
      wsRef.current = ws
      ws.onmessage = (evt) => {
        const msg = JSON.parse(evt.data)
        setStreamLog((prev) => [...prev, JSON.stringify(msg)])
        if (msg.type === 'completed' || msg.type === 'failed') {
          setStreaming(false)
          ws.close()
          qc.invalidateQueries({ queryKey: ['profile-rules', profileId] })
        }
      }
      ws.onerror = () => setStreaming(false)
    },
  })

  const deleteMut = useMutation({
    mutationFn: () => deleteProfile(profileId!),
    onSuccess: () => navigate(-1),
  })

  return (
    <div className="flex gap-4 h-full" style={{ minHeight: '80vh' }}>
      {/* Rules list */}
      <div className="w-64 flex-shrink-0 flex flex-col gap-2 overflow-y-auto">
        <div className="flex items-center gap-2 mb-2">
          <h2 className="font-bold text-aegis-dark flex-1 truncate">{profile?.name ?? 'Profile'}</h2>
          <button
            onClick={() => triggerGenMut.mutate()}
            disabled={streaming}
            className="text-xs bg-aegis-blue text-white rounded px-2 py-1 disabled:opacity-50"
          >
            {streaming ? '⏳ Generating…' : '⚡ Generate Codes'}
          </button>
          <button
            onClick={() => {
              if (window.confirm(`Delete profile "${profile?.name}"? This cannot be undone.`)) {
                deleteMut.mutate()
              }
            }}
            className="text-xs bg-red-600 text-white rounded px-2 py-1 hover:bg-red-700"
            title="Delete profile"
          >
            Delete
          </button>
        </div>

        {streaming && (
          <div className="bg-gray-900 text-green-400 text-xs rounded p-2 max-h-32 overflow-y-auto font-mono">
            {streamLog.map((l, i) => <div key={i}>{l}</div>)}
          </div>
        )}

        {rules.map((r) => (
          <button
            key={r.id}
            onClick={() => setSelectedRule(r)}
            className={`text-left px-2 py-2 rounded text-xs ${selectedRule?.id === r.id ? 'bg-aegis-dark text-white' : 'bg-white hover:bg-gray-100'}`}
          >
            <div className="font-medium truncate">{r.component_type}</div>
            <div style={{ color: STATUS_COLOR[r.code_status] }} className="font-semibold uppercase">
              {r.code_status}
            </div>
          </button>
        ))}
      </div>

      {/* Code editor panel */}
      <div className="flex-1 flex flex-col">
        {selectedRule ? (
          <>
            <div className="flex items-center gap-2 mb-2">
              <div className="flex gap-1">
                {CODE_TABS.map((t) => (
                  <button
                    key={t.key}
                    onClick={() => setActiveTab(t.key)}
                    className={`px-3 py-1 rounded text-sm ${activeTab === t.key ? 'bg-aegis-dark text-white' : 'bg-white border hover:bg-gray-50'}`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
              <div className="ml-auto flex gap-2">
                <button onClick={() => saveMut.mutate()} className="text-sm bg-aegis-blue text-white px-3 py-1 rounded">Save</button>
                <button onClick={() => approveMut.mutate()} className="text-sm bg-aegis-green text-white px-3 py-1 rounded">Approve</button>
                <button onClick={() => rejectMut.mutate()} className="text-sm bg-aegis-red text-white px-3 py-1 rounded">Reject</button>
              </div>
            </div>
            <div className="flex-1 rounded overflow-hidden border">
              <MonacoEditor
                height="100%"
                language="python"
                value={editedCode}
                onChange={(val) => setEditedCode(val ?? '')}
                theme="vs-dark"
                options={{ minimap: { enabled: false }, fontSize: 13, wordWrap: 'on' }}
              />
            </div>
          </>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400">
            Select a rule to view and edit its generated code.
          </div>
        )}
      </div>
    </div>
  )
}
