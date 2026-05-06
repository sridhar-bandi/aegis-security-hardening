import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import MonacoEditor from '@monaco-editor/react'
import {
  listPolicyRules,
  updatePolicyRuleCode,
  approvePolicyRule,
  rejectPolicyRule,
  importPolicyRuleCode,
  generatePolicyCodes,
} from '../api/endpoints'
import type { PolicyRule } from '../types'

const STATUS_DOT: Record<string, string> = {
  pending: 'bg-gray-400',
  generating: 'bg-yellow-400 animate-pulse',
  generated: 'bg-blue-500',
  reviewed: 'bg-orange-400',
  approved: 'bg-green-500',
  rejected: 'bg-red-500',
}

const STATUS_LABEL: Record<string, string> = {
  pending: 'Pending',
  generating: 'Generating…',
  generated: 'Generated',
  reviewed: 'Reviewed',
  approved: 'Approved',
  rejected: 'Rejected',
}

type CodeTab = 'evaluation_code' | 'remediation_code' | 'rollback_code'
const CODE_TABS: { key: CodeTab; label: string }[] = [
  { key: 'evaluation_code', label: 'Evaluate' },
  { key: 'remediation_code', label: 'Remediate' },
  { key: 'rollback_code', label: 'Rollback' },
]

export default function PolicyImplementationEditorPage() {
  const { policyId } = useParams<{ policyId: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: rules = [] } = useQuery({
    queryKey: ['policy-rules', policyId],
    queryFn: () => listPolicyRules(policyId!),
    enabled: !!policyId,
  })

  const [selectedRule, setSelectedRule] = useState<PolicyRule | null>(null)
  const [activeTab, setActiveTab] = useState<CodeTab>('evaluation_code')
  const [editedCode, setEditedCode] = useState('')
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set())
  const [streaming, setStreaming] = useState(false)
  const [streamLog, setStreamLog] = useState<string[]>([])
  const [showImportModal, setShowImportModal] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  // Group rules by category
  const categoryGroups = (() => {
    const order: string[] = []
    const map = new Map<string, PolicyRule[]>()
    for (const r of rules) {
      const cat = r.category || 'Uncategorized'
      if (!map.has(cat)) { map.set(cat, []); order.push(cat) }
      map.get(cat)!.push(r)
    }
    return order.map((cat) => ({ category: cat, rules: map.get(cat)! }))
  })()

  // Auto-expand all categories on first load
  useEffect(() => {
    if (rules.length > 0) {
      setExpandedCategories(new Set(rules.map((r) => r.category || 'Uncategorized')))
    }
  }, [rules.length]) // eslint-disable-line react-hooks/exhaustive-deps

  // Sync editor content when selected rule or tab changes
  useEffect(() => {
    if (selectedRule) {
      setEditedCode(selectedRule[activeTab] ?? '')
    }
  }, [selectedRule, activeTab])

  // Keep selectedRule in sync with latest data
  useEffect(() => {
    if (selectedRule) {
      const updated = rules.find((r) => r.id === selectedRule.id)
      if (updated && updated !== selectedRule) {
        setSelectedRule(updated)
      }
    }
  }, [rules]) // eslint-disable-line react-hooks/exhaustive-deps

  const saveMut = useMutation({
    mutationFn: () => updatePolicyRuleCode(policyId!, selectedRule!.id, { [activeTab]: editedCode }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['policy-rules', policyId] }),
  })

  const approveMut = useMutation({
    mutationFn: () => approvePolicyRule(policyId!, selectedRule!.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['policy-rules', policyId] }),
  })

  const rejectMut = useMutation({
    mutationFn: () => rejectPolicyRule(policyId!, selectedRule!.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['policy-rules', policyId] }),
  })

  const regenMut = useMutation({
    mutationFn: () => generatePolicyCodes(policyId!, selectedRule ? [selectedRule.id] : undefined),
    onSuccess: (data) => {
      setStreaming(true)
      setStreamLog([])
      const token = localStorage.getItem('aegis_token') ?? ''
      const ws = new WebSocket(`ws://${location.host}/api/v1/ws/codegen/policy/${policyId}?token=${token}`)
      wsRef.current = ws
      ws.onmessage = (evt) => {
        const msg = JSON.parse(evt.data)
        setStreamLog((prev) => [...prev, JSON.stringify(msg)])
        if (msg.type === 'completed' || msg.type === 'failed') {
          setStreaming(false)
          ws.close()
          qc.invalidateQueries({ queryKey: ['policy-rules', policyId] })
        }
      }
      ws.onerror = () => setStreaming(false)
    },
  })

  const toggleCategory = (cat: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev)
      next.has(cat) ? next.delete(cat) : next.add(cat)
      return next
    })
  }

  return (
    <div className="flex flex-col h-full" style={{ minHeight: '80vh' }}>
      <button
        onClick={() => navigate('/policies')}
        className="flex items-center gap-1 text-sm text-slate-500 hover:text-aegis-blue mb-3 w-fit"
      >
        <span>←</span> Back to Policies
      </button>
      <div className="flex gap-4 flex-1">
      {/* ── Sidebar: Rules list ── */}
      <div className="w-72 flex-shrink-0 flex flex-col overflow-y-auto">
        <div className="flex items-center gap-2 mb-3 flex-wrap">
          <h2 className="font-bold text-aegis-dark flex-1 truncate text-sm">Policy Implementation</h2>
          <button
            onClick={() => regenMut.mutate()}
            disabled={streaming}
            className="text-xs bg-aegis-blue text-white rounded px-2 py-1 disabled:opacity-50"
          >
            {streaming ? '⏳ Generating…' : '⚡ Generate All'}
          </button>
        </div>

        {categoryGroups.map(({ category, rules: catRules }) => (
          <div key={category} className="mb-1">
            <button
              className="w-full flex items-center gap-1 px-2 py-1 rounded hover:bg-slate-100 text-xs font-semibold text-slate-600"
              onClick={() => toggleCategory(category)}
            >
              <span className="text-[10px]">{expandedCategories.has(category) ? '▼' : '▶'}</span>
              <span className="truncate flex-1 text-left">{category}</span>
              <span className="text-[10px] text-slate-400">{catRules.length}</span>
            </button>
            {expandedCategories.has(category) && (
              <div className="ml-3">
                {catRules.map((rule) => (
                  <button
                    key={rule.id}
                    onClick={() => setSelectedRule(rule)}
                    className={`w-full flex items-center gap-2 px-2 py-1 rounded text-xs text-left truncate ${
                      selectedRule?.id === rule.id ? 'bg-aegis-blue/10 font-medium' : 'hover:bg-slate-50'
                    }`}
                  >
                    <span className={`w-2 h-2 rounded-full flex-shrink-0 ${STATUS_DOT[rule.code_status] ?? 'bg-gray-400'}`} />
                    <span className="truncate">{rule.rule_id}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}

        {/* Stream log */}
        {streaming && (
          <div className="mt-4 p-2 bg-slate-900 text-green-300 rounded text-[10px] max-h-40 overflow-y-auto font-mono">
            {streamLog.map((l, i) => <div key={i}>{l}</div>)}
          </div>
        )}
      </div>

      {/* ── Main editor panel ── */}
      <div className="flex-1 flex flex-col min-w-0">
        {selectedRule ? (
          <>
            {/* Rule header */}
            <div className="flex items-center gap-3 mb-2 flex-wrap">
              <h3 className="font-semibold text-sm text-aegis-dark truncate flex-1">{selectedRule.title}</h3>
              <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${
                selectedRule.code_status === 'approved' ? 'bg-green-100 text-green-700' :
                selectedRule.code_status === 'rejected' ? 'bg-red-100 text-red-700' :
                'bg-slate-100 text-slate-600'
              }`}>
                <span className={`w-2 h-2 rounded-full ${STATUS_DOT[selectedRule.code_status] ?? 'bg-gray-400'}`} />
                {STATUS_LABEL[selectedRule.code_status] ?? selectedRule.code_status}
              </span>
              {selectedRule.code_source !== 'llm' && (
                <span className="text-[10px] bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded">
                  {selectedRule.code_source === 'imported' ? `📁 ${selectedRule.imported_filename ?? 'Imported'}` : '✏️ Manual'}
                </span>
              )}
            </div>

            {/* Code tabs */}
            <div className="flex gap-1 mb-2">
              {CODE_TABS.map((t) => (
                <button
                  key={t.key}
                  onClick={() => setActiveTab(t.key)}
                  className={`px-3 py-1 rounded text-xs font-medium ${
                    activeTab === t.key ? 'bg-aegis-blue text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {/* Monaco Editor */}
            <div className="flex-1 border rounded overflow-hidden" style={{ minHeight: 300 }}>
              <MonacoEditor
                height="100%"
                language="python"
                theme="vs-dark"
                value={editedCode}
                onChange={(v) => setEditedCode(v ?? '')}
                options={{ minimap: { enabled: false }, fontSize: 12, wordWrap: 'on' }}
              />
            </div>

            {/* Action buttons */}
            <div className="flex gap-2 mt-2 flex-wrap">
              <button
                onClick={() => saveMut.mutate()}
                disabled={saveMut.isPending}
                className="px-3 py-1.5 text-xs bg-aegis-blue text-white rounded disabled:opacity-50"
              >
                💾 Save
              </button>
              <button
                onClick={() => approveMut.mutate()}
                disabled={approveMut.isPending || !selectedRule.evaluation_code}
                className="px-3 py-1.5 text-xs bg-green-600 text-white rounded disabled:opacity-50"
              >
                ✓ Approve
              </button>
              <button
                onClick={() => rejectMut.mutate()}
                disabled={rejectMut.isPending}
                className="px-3 py-1.5 text-xs bg-red-600 text-white rounded disabled:opacity-50"
              >
                ✗ Reject
              </button>
              <button
                onClick={() => setShowImportModal(true)}
                className="px-3 py-1.5 text-xs bg-indigo-600 text-white rounded"
              >
                📂 Import
              </button>
              <button
                onClick={() => regenMut.mutate()}
                disabled={streaming}
                className="px-3 py-1.5 text-xs bg-purple-600 text-white rounded disabled:opacity-50"
              >
                🔄 Re-generate
              </button>
            </div>
          </>
        ) : (
          <div className="flex items-center justify-center h-full text-slate-400 text-sm">
            Select a rule from the sidebar to review its implementation code.
          </div>
        )}
      </div>

      {/* ── Import Modal ── */}
      {showImportModal && selectedRule && (
        <ImportModal
          policyId={policyId!}
          ruleId={selectedRule.id}
          onClose={() => setShowImportModal(false)}
          onSuccess={() => {
            setShowImportModal(false)
            qc.invalidateQueries({ queryKey: ['policy-rules', policyId] })
          }}
        />
      )}
      </div>
    </div>
  )
}

// ── Import Modal Component ──
function ImportModal({ policyId, ruleId, onClose, onSuccess }: {
  policyId: string
  ruleId: string
  onClose: () => void
  onSuccess: () => void
}) {
  const [codeType, setCodeType] = useState<string>('evaluation')
  const [file, setFile] = useState<File | null>(null)

  const importMut = useMutation({
    mutationFn: () => importPolicyRuleCode(policyId, ruleId, codeType, file!),
    onSuccess,
  })

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-lg p-6 w-96 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <h3 className="font-bold text-sm mb-4">Import Script File</h3>
        <div className="mb-3">
          <label className="block text-xs text-slate-600 mb-1">Code Type</label>
          <select
            value={codeType}
            onChange={(e) => setCodeType(e.target.value)}
            className="w-full border rounded px-2 py-1 text-sm"
          >
            <option value="evaluation">Evaluation</option>
            <option value="remediation">Remediation</option>
            <option value="rollback">Rollback</option>
          </select>
        </div>
        <div className="mb-4">
          <label className="block text-xs text-slate-600 mb-1">Script File</label>
          <input
            type="file"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="w-full text-sm"
          />
        </div>
        <div className="flex gap-2 justify-end">
          <button onClick={onClose} className="px-3 py-1.5 text-xs border rounded">Cancel</button>
          <button
            onClick={() => importMut.mutate()}
            disabled={!file || importMut.isPending}
            className="px-3 py-1.5 text-xs bg-aegis-blue text-white rounded disabled:opacity-50"
          >
            Import
          </button>
        </div>
        {importMut.isError && (
          <p className="text-xs text-red-600 mt-2">Import failed. Please try again.</p>
        )}
      </div>
    </div>
  )
}
