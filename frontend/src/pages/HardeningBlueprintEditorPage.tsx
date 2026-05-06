import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import MonacoEditor from '@monaco-editor/react'
import { getBlueprint, listBlueprintRules, updateRuleCode, approveRule, rejectRule, triggerCodeGen, deleteBlueprint } from '../api/endpoints'
import type { BlueprintRule } from '../types'

const STATUS_COLOR: Record<string, string> = {
  pending: '#7f8c8d',
  generated: '#2980b9',
  reviewed: '#e67e22',
  approved: '#27ae60',
  rejected: '#c0392b',
}

const STATUS_DOT: Record<string, string> = {
  pending:   'bg-gray-400',
  generated: 'bg-blue-500',
  reviewed:  'bg-orange-400',
  approved:  'bg-green-500',
  rejected:  'bg-red-500',
}

type CodeTab = 'evaluation_code' | 'remediation_code' | 'rollback_code'
const CODE_TABS: { key: CodeTab; label: string }[] = [
  { key: 'evaluation_code', label: 'Evaluate' },
  { key: 'remediation_code', label: 'Remediate' },
  { key: 'rollback_code', label: 'Rollback' },
]

// ── Component label helpers (mirrors HardeningBlueprintManagerPage) ────────────────
const ID_PREFIX_MAP: { prefix: string; category: string; suffix: string }[] = [
  { prefix: 'server-', category: 'Server',          suffix: '— Host OS' },
  { prefix: 'ilo-',    category: 'iLO',             suffix: '— iLO'     },
  { prefix: 'switch-', category: 'Network Switch',  suffix: ''          },
  { prefix: 'pdu-',    category: 'PDU',             suffix: ''          },
  { prefix: 'storage-',category: 'Storage',         suffix: ''          },
  { prefix: 'vm-',     category: 'Virtual Machine', suffix: ''          },
]

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
        label = dash !== -1 ? `${rest.slice(0, dash)} (${rest.slice(dash + 1)})` : rest
      } else {
        label = rest.replace(/-/g, ' ')
      }
      return { label: suffix ? `${label} ${suffix}` : label, category }
    }
  }
  return { label: id, category: 'Other' }
}

const CATEGORY_BADGE: Record<string, string> = {
  'Server':          'bg-green-100 text-green-800',
  'iLO':             'bg-orange-100 text-orange-800',
  'Network Switch':  'bg-blue-100 text-blue-800',
  'PDU':             'bg-yellow-100 text-yellow-800',
  'Storage':         'bg-purple-100 text-purple-800',
  'Virtual Machine': 'bg-indigo-100 text-indigo-800',
}

export default function HardeningBlueprintEditorPage() {
  const { blueprintId } = useParams<{ blueprintId: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: blueprint } = useQuery({
    queryKey: ['blueprint', blueprintId],
    queryFn: () => getBlueprint(blueprintId!),
    enabled: !!blueprintId,
  })

  const { data: rules = [] } = useQuery({
    queryKey: ['blueprint-rules', blueprintId],
    queryFn: () => listBlueprintRules(blueprintId!),
    enabled: !!blueprintId,
  })

  const [selectedRule, setSelectedRule] = useState<BlueprintRule | null>(null)
  const [activeTab, setActiveTab] = useState<CodeTab>('evaluation_code')
  const [editedCode, setEditedCode] = useState('')
  const [expandedComponents, setExpandedComponents] = useState<Set<string>>(new Set())
  const wsRef = useRef<WebSocket | null>(null)
  const [streaming, setStreaming] = useState(false)
  const [streamLog, setStreamLog] = useState<string[]>([])

  // Group rules by component_type, preserving backend order
  const componentGroups = (() => {
    const order: string[] = []
    const map = new Map<string, BlueprintRule[]>()
    for (const r of rules) {
      if (!map.has(r.component_type)) { map.set(r.component_type, []); order.push(r.component_type) }
      map.get(r.component_type)!.push(r)
    }
    return order.map((ct) => ({ componentType: ct, rules: map.get(ct)! }))
  })()

  // Auto-expand the component that contains the selected rule
  useEffect(() => {
    if (selectedRule) {
      setExpandedComponents((prev) => new Set([...prev, selectedRule.component_type]))
    }
  }, [selectedRule])

  // Auto-expand all components on first load
  useEffect(() => {
    if (rules.length > 0) {
      setExpandedComponents(new Set(rules.map((r) => r.component_type)))
    }
  }, [rules.length]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (selectedRule) {
      setEditedCode(selectedRule[activeTab] ?? '')
    }
  }, [selectedRule, activeTab])

  const saveMut = useMutation({
    mutationFn: () => updateRuleCode(blueprintId!, selectedRule!.id, { [activeTab]: editedCode }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['blueprint-rules', blueprintId] }),
  })

  const approveMut = useMutation({
    mutationFn: () => approveRule(blueprintId!, selectedRule!.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['blueprint-rules', blueprintId] }),
  })

  const rejectMut = useMutation({
    mutationFn: () => rejectRule(blueprintId!, selectedRule!.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['blueprint-rules', blueprintId] }),
  })

  const triggerGenMut = useMutation({
    mutationFn: () => triggerCodeGen(blueprintId!),
    onSuccess: () => {
      setStreaming(true)
      setStreamLog([])
      const token = localStorage.getItem('aegis_token') ?? ''
      const ws = new WebSocket(`ws://${location.host}/api/v1/ws/codegen/${blueprintId}?token=${token}`)
      wsRef.current = ws
      ws.onmessage = (evt) => {
        const msg = JSON.parse(evt.data)
        setStreamLog((prev) => [...prev, JSON.stringify(msg)])
        if (msg.type === 'completed' || msg.type === 'failed') {
          setStreaming(false)
          ws.close()
          qc.invalidateQueries({ queryKey: ['blueprint-rules', blueprintId] })
        }
      }
      ws.onerror = () => setStreaming(false)
    },
  })

  const deleteMut = useMutation({
    mutationFn: () => deleteBlueprint(blueprintId!),
    onSuccess: () => navigate(-1),
  })

  const toggleComponent = (ct: string) => {
    setExpandedComponents((prev) => {
      const next = new Set(prev)
      next.has(ct) ? next.delete(ct) : next.add(ct)
      return next
    })
  }

  return (
    <div className="flex flex-col h-full" style={{ minHeight: '80vh' }}>
      <button
        onClick={() => navigate('/blueprints')}
        className="flex items-center gap-1 text-sm text-slate-500 hover:text-aegis-blue mb-3 w-fit"
      >
        <span>←</span> Back to Blueprints
      </button>
      <div className="flex gap-4 flex-1">
      {/* ── Sidebar ── */}
      <div className="w-72 flex-shrink-0 flex flex-col overflow-y-auto">
        {/* Header row */}
        <div className="flex items-center gap-2 mb-3 flex-wrap">
          <h2 className="font-bold text-aegis-dark flex-1 truncate text-sm">{blueprint?.name ?? 'Blueprint'}</h2>
          <button
            onClick={() => triggerGenMut.mutate()}
            disabled={streaming}
            className="text-xs bg-aegis-blue text-white rounded px-2 py-1 disabled:opacity-50"
          >
            {streaming ? '⏳ Generating…' : '⚡ Generate Codes'}
          </button>
          <button
            onClick={() => {
              if (window.confirm(`Delete blueprint "${blueprint?.name}"? This cannot be undone.`)) {
                deleteMut.mutate()
              }
            }}
            className="text-xs bg-red-600 text-white rounded px-2 py-1 hover:bg-red-700"
          >
            Delete
          </button>
        </div>

        {/* Component count summary */}
        {componentGroups.length > 0 && (
          <p className="text-xs text-gray-400 mb-2">
            {componentGroups.length} component{componentGroups.length !== 1 ? 's' : ''} ·{' '}
            {rules.length} rule{rules.length !== 1 ? 's' : ''}
          </p>
        )}

        {streaming && (
          <div className="bg-gray-900 text-green-400 text-xs rounded p-2 max-h-28 overflow-y-auto font-mono mb-2">
            {streamLog.map((l, i) => <div key={i}>{l}</div>)}
          </div>
        )}

        {/* ── Component → Rules grouped list ── */}
        <div className="flex flex-col gap-1">
          {componentGroups.map(({ componentType, rules: compRules }) => {
            const { label, category } = humanizeCompId(componentType)
            const badgeClass = CATEGORY_BADGE[category] ?? 'bg-gray-100 text-gray-700'
            const expanded = expandedComponents.has(componentType)
            const statusCounts = compRules.reduce<Record<string, number>>((acc, r) => {
              acc[r.code_status] = (acc[r.code_status] ?? 0) + 1
              return acc
            }, {})
            const allApproved = compRules.every((r) => r.code_status === 'approved')
            const anyPending  = compRules.some((r) => r.code_status === 'pending')

            return (
              <div key={componentType} className="rounded border border-gray-200 overflow-hidden">
                {/* Component header */}
                <button
                  onClick={() => toggleComponent(componentType)}
                  className="w-full flex items-center gap-2 px-2 py-2 bg-gray-50 hover:bg-gray-100 text-left"
                >
                  <span className="text-gray-400 text-xs w-3">{expanded ? '▼' : '▶'}</span>
                  <span className={`text-xs font-medium px-1.5 py-0.5 rounded shrink-0 ${badgeClass}`}>
                    {category}
                  </span>
                  <span className="text-xs font-semibold text-aegis-dark flex-1 truncate" title={label}>
                    {label}
                  </span>
                  <span className={`w-2 h-2 rounded-full shrink-0 ${allApproved ? 'bg-green-500' : anyPending ? 'bg-gray-400' : 'bg-blue-500'}`} />
                </button>

                {/* Status mini-summary when collapsed */}
                {!expanded && (
                  <div className="px-2 py-1 bg-white flex gap-2 flex-wrap">
                    {Object.entries(statusCounts).map(([status, count]) => (
                      <span key={status} className="flex items-center gap-1 text-xs text-gray-500">
                        <span className={`w-1.5 h-1.5 rounded-full inline-block ${STATUS_DOT[status] ?? 'bg-gray-300'}`} />
                        {count} {status}
                      </span>
                    ))}
                  </div>
                )}

                {/* Rules list */}
                {expanded && (
                  <div className="divide-y divide-gray-100">
                    {compRules.map((r) => {
                      const isSelected = selectedRule?.id === r.id
                      return (
                        <button
                          key={r.id}
                          onClick={() => setSelectedRule(r)}
                          className={`w-full text-left px-3 py-2 flex items-start gap-2 transition-colors ${
                            isSelected ? 'bg-aegis-dark text-white' : 'bg-white hover:bg-gray-50'
                          }`}
                        >
                          <span className={`w-1.5 h-1.5 rounded-full shrink-0 mt-1.5 ${STATUS_DOT[r.code_status] ?? 'bg-gray-300'}`} />
                          <div className="min-w-0 flex-1">
                            <div className="text-xs font-medium leading-snug truncate" title={r.rule_title ?? r.policy_rule_id}>
                              {r.rule_title ?? r.rule_short_id ?? '(untitled rule)'}
                            </div>
                            <div
                              className="text-xs mt-0.5 font-semibold uppercase"
                              style={{ color: isSelected ? 'rgba(255,255,255,0.7)' : STATUS_COLOR[r.code_status] }}
                            >
                              {r.code_status}
                            </div>
                          </div>
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* ── Code editor panel ── */}
      <div className="flex-1 flex flex-col">
        {selectedRule ? (
          <>
            {/* Context breadcrumb */}
            <div className="mb-2 text-xs text-gray-400 truncate">
              <span className="font-medium text-aegis-dark">{humanizeCompId(selectedRule.component_type).label}</span>
              <span className="mx-1">→</span>
              <span>{selectedRule.rule_title ?? selectedRule.rule_short_id ?? selectedRule.policy_rule_id}</span>
            </div>

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
          <div className="flex items-center justify-center h-full text-gray-400 flex-col gap-2">
            <span className="text-lg">←</span>
            <span className="text-sm">Select a rule from the component list to view and edit its generated code.</span>
          </div>
        )}
      </div>
      </div>
    </div>
  )
}
