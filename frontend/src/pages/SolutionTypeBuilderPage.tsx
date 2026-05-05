import { useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listSolutionTypes, createSolutionType, updateComponentSelection, deleteSolutionType } from '../api/endpoints'
import { useWorkspace } from '../context/WorkspaceContext'

interface ParsedComponent {
  id: string
  label: string
  category: string
  instanceCount: number
  componentIds: string[]
  jsonPaths: string[]
}

const CATEGORY_CARD: Record<string, string> = {
  PDU: 'bg-yellow-50 border-yellow-200',
  'Network Switch': 'bg-blue-50 border-blue-200',
  Server: 'bg-green-50 border-green-200',
  'iLO': 'bg-orange-50 border-orange-200',
  Storage: 'bg-purple-50 border-purple-200',
  'Virtual Machine': 'bg-indigo-50 border-indigo-200',
}

const CATEGORY_BADGE: Record<string, string> = {
  PDU: 'bg-yellow-100 text-yellow-800',
  'Network Switch': 'bg-blue-100 text-blue-800',
  Server: 'bg-green-100 text-green-800',
  'iLO': 'bg-orange-100 text-orange-800',
  Storage: 'bg-purple-100 text-purple-800',
  'Virtual Machine': 'bg-indigo-100 text-indigo-800',
}

// Preferred display order for categories
const CATEGORY_ORDER = ['Server', 'iLO', 'Network Switch', 'Storage', 'PDU', 'Virtual Machine']

function extractComponentsFromJson(json: unknown): ParsedComponent[] {
  const data = json as Record<string, unknown>
  const racks = (
    Array.isArray(data.racks) ? data.racks :
    Array.isArray((data.infrastructure as Record<string, unknown> | undefined)?.racks)
      ? (data.infrastructure as Record<string, unknown>).racks as unknown[]
      : []
  ) as Record<string, unknown>[]

  const map = new Map<string, ParsedComponent>()

  const slug = (s: string) => s.replace(/[^a-zA-Z0-9]/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '')

  // Determine the JSON path prefix for racks
  const racksPrefix = Array.isArray(data.racks) ? 'racks' : 'infrastructure.racks'

  const upsert = (id: string, label: string, category: string, compId: string, jsonPath: string) => {
    if (map.has(id)) {
      map.get(id)!.instanceCount++
      map.get(id)!.componentIds.push(compId)
      map.get(id)!.jsonPaths.push(jsonPath)
    } else {
      map.set(id, { id, label, category, instanceCount: 1, componentIds: [compId], jsonPaths: [jsonPath] })
    }
  }

  for (let rackIdx = 0; rackIdx < racks.length; rackIdx++) {
    const rack = racks[rackIdx]
    const rackPath = `${racksPrefix}[${rackIdx}]`
    for (let pi = 0; pi < ((rack.pdus as Record<string, unknown>[] | undefined) ?? []).length; pi++) {
      const pdu = ((rack.pdus as Record<string, unknown>[]))[pi]
      const type = (pdu.type as string | undefined) ?? 'Unknown PDU'
      upsert(`pdu-${slug(type)}`, type, 'PDU', pdu.componentId as string, `${rackPath}.pdus[${pi}]`)
    }
    for (let si = 0; si < ((rack.networkSwitches as Record<string, unknown>[] | undefined) ?? []).length; si++) {
      const sw = ((rack.networkSwitches as Record<string, unknown>[]))[si]
      const type = (sw.type as string | undefined) ?? 'Network Switch'
      upsert(`switch-${slug(type)}`, type, 'Network Switch', sw.componentId as string, `${rackPath}.networkSwitches[${si}]`)
    }
    for (let svi = 0; svi < ((rack.servers as Record<string, unknown>[] | undefined) ?? []).length; svi++) {
      const srv = ((rack.servers as Record<string, unknown>[]))[svi]
      const type = (srv.type as string | undefined) ?? 'Server'
      const role = (srv.allocatedFor as string | undefined) ?? ''
      const baseLabel = role ? `${type} (${role})` : type
      const baseId = `${slug(type)}${role ? `-${slug(role)}` : ''}`
      const creds = (srv.accessCredentials as Record<string, unknown>[] | undefined) ?? []
      const targets = new Set(creds.map((c) => (c.target as string | undefined)?.toUpperCase() ?? ''))
      const hasHost = targets.has('HOST') || targets.has('OS')
      const hasILO = targets.has('ILO') || targets.has('ILO_FACTORY_DEFAULT')
      const srvPath = `${rackPath}.servers[${svi}]`
      // Always emit a Server (Host) entry
      upsert(`server-${baseId}`, `${baseLabel} — Host OS`, 'Server', srv.componentId as string, srvPath)
      // Emit a separate iLO entry only when iLO credentials are present
      if (hasILO || !hasHost) {
        upsert(`ilo-${baseId}`, `${baseLabel} — iLO`, 'iLO', srv.componentId as string, srvPath)
      }
    }
    for (let sti = 0; sti < ((rack.storageArrays as Record<string, unknown>[] | undefined) ?? []).length; sti++) {
      const stor = ((rack.storageArrays as Record<string, unknown>[]))[sti]
      const type = (stor.type as string | undefined) ?? 'Storage Array'
      const storPath = `${rackPath}.storageArrays[${sti}]`
      upsert(`storage-${slug(type)}`, type, 'Storage', stor.componentId as string, storPath)
      // also walk networkSwitches nested inside storageArrays
      for (let nssi = 0; nssi < ((stor.networkSwitches as Record<string, unknown>[] | undefined) ?? []).length; nssi++) {
        const sw = ((stor.networkSwitches as Record<string, unknown>[]))[nssi]
        const swType = (sw.type as string | undefined) ?? 'Network Switch'
        upsert(`switch-${slug(swType)}`, swType, 'Network Switch', sw.componentId as string, `${storPath}.networkSwitches[${nssi}]`)
      }
    }
  }

  // Walk virtualMachines under infrastructureManagement (base-configuration.json)
  const infraMgmt = data.infrastructureManagement as Record<string, unknown> | undefined
  const hypervisorCluster = (infraMgmt?.specificAttributes as Record<string, unknown> | undefined)?.hypervisorCluster as Record<string, unknown> | undefined
  const vms = (hypervisorCluster?.virtualMachines as Record<string, unknown>[] | undefined) ?? []
  for (let vmi = 0; vmi < vms.length; vmi++) {
    const vm = vms[vmi]
    const type = (vm.type as string | undefined) ?? 'VM'
    const vmName = (vm.vmName as string | undefined) ?? (vm.hostName as string | undefined) ?? ''
    const label = vmName ? `${type} (${vmName})` : type
    upsert(`vm-${slug(type)}-${slug(vmName || vm.componentId as string)}`, label, 'Virtual Machine', vm.componentId as string, `infrastructureManagement.specificAttributes.hypervisorCluster.virtualMachines[${vmi}]`)
  }

  return Array.from(map.values())
}

type WizardStep = 'name-and-file' | 'select-components'

// Maps stored component ID prefix → category and suffix hint
const ID_PREFIX_MAP: { prefix: string; category: string; suffix: string }[] = [
  { prefix: 'server-', category: 'Server',          suffix: '— Host OS' },
  { prefix: 'ilo-',    category: 'iLO',             suffix: '— iLO'     },
  { prefix: 'switch-', category: 'Network Switch',  suffix: ''          },
  { prefix: 'pdu-',    category: 'PDU',             suffix: ''          },
  { prefix: 'storage-',category: 'Storage',         suffix: ''          },
  { prefix: 'vm-',     category: 'Virtual Machine', suffix: ''          },
]

function humanizeId(id: string): { label: string; category: string } {
  for (const { prefix, category, suffix } of ID_PREFIX_MAP) {
    if (id.startsWith(prefix)) {
      const rest = id.slice(prefix.length)
      let label: string
      if (prefix === 'vm-') {
        // vm-MVM-ez-master01 → MVM (ez-master01)
        const dash = rest.indexOf('-')
        if (dash !== -1) {
          label = `${rest.slice(0, dash)} (${rest.slice(dash + 1).replace(/-/g, '-')})`
        } else {
          label = rest
        }
      } else if (prefix === 'server-' || prefix === 'ilo-') {
        // server-DL325-controlNode → DL325 (controlNode) — Host OS
        const dash = rest.lastIndexOf('-')
        if (dash !== -1 && dash > 0 && dash < rest.length - 1) {
          const type = rest.slice(0, dash).replace(/-/g, ' ')
          const role = rest.slice(dash + 1)
          label = `${type} (${role})`
        } else {
          label = rest.replace(/-/g, ' ')
        }
      } else {
        label = rest.replace(/-/g, ' ')
      }
      return { label: suffix ? `${label} ${suffix}` : label, category }
    }
  }
  return { label: id, category: 'Other' }
}

export default function SolutionTypeBuilderPage() {
  const qc = useQueryClient()
  const { selectedWorkspace } = useWorkspace()
  const workspaceId = selectedWorkspace?.id ?? ''
  const [selectedId, setSelectedId] = useState('')

  // ── Creation wizard state ────────────────────────────────────────────────
  const [wizardOpen, setWizardOpen] = useState(false)
  const [wizardStep, setWizardStep] = useState<WizardStep>('name-and-file')
  const [wizardName, setWizardName] = useState('')
  const [wizardComponents, setWizardComponents] = useState<ParsedComponent[]>([])
  const [wizardSelectedIds, setWizardSelectedIds] = useState<string[]>([])
  const [wizardFileName, setWizardFileName] = useState('')
  const [wizardSolutionName, setWizardSolutionName] = useState('')
  const [wizardParseError, setWizardParseError] = useState('')
  const wizardFileRef = useRef<HTMLInputElement>(null)

  // ── Existing solution-type edit state ────────────────────────────────────
  const [parsedComponents, setParsedComponents] = useState<ParsedComponent[]>([])
  const [scidFileName, setScidFileName] = useState('')
  const [parseError, setParseError] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const { data: solutionTypes = [] } = useQuery({
    queryKey: ['solution-types', workspaceId],
    queryFn: () => listSolutionTypes(workspaceId),
    enabled: !!workspaceId,
  })

  const selected = solutionTypes.find((s) => s.id === selectedId)

  // Create + immediately apply component selection in one shot
  const createAndConfigureMut = useMutation({
    mutationFn: async () => {
      const st = await createSolutionType(workspaceId, wizardName)
      if (wizardSelectedIds.length > 0) {
        await updateComponentSelection(st.id, wizardSelectedIds)
      }
      return st
    },
    onSuccess: (st) => {
      qc.invalidateQueries({ queryKey: ['solution-types', workspaceId] })
      setSelectedId(st.id)
      closeWizard()
    },
  })

  const updateMut = useMutation({
    mutationFn: ({ id, ids }: { id: string; ids: string[] }) => updateComponentSelection(id, ids),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['solution-types', workspaceId] }),
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteSolutionType(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['solution-types', workspaceId] })
      setSelectedId('')
      setParsedComponents([])
      setScidFileName('')
    },
  })

  // ── Wizard helpers ───────────────────────────────────────────────────────
  const openWizard = () => {
    setWizardOpen(true)
    setWizardStep('name-and-file')
    setWizardName('')
    setWizardComponents([])
    setWizardSelectedIds([])
    setWizardFileName('')
    setWizardSolutionName('')
    setWizardParseError('')
    setSelectedId('')
  }

  const closeWizard = () => {
    setWizardOpen(false)
    setWizardStep('name-and-file')
    setWizardName('')
    setWizardComponents([])
    setWizardSelectedIds([])
    setWizardFileName('')
    setWizardSolutionName('')
    setWizardParseError('')
  }

  const parseFile = (file: File, onSuccess: (comps: ParsedComponent[], solutionName: string) => void, onError: (msg: string) => void) => {
    const reader = new FileReader()
    reader.onload = (ev) => {
      try {
        const json = JSON.parse(ev.target?.result as string) as Record<string, unknown>
        const comps = extractComponentsFromJson(json)
        if (comps.length === 0) {
          onError('No component types found. Ensure the file contains racks with pdus, networkSwitches, servers, or storageArrays.')
        } else {
          const solutionName = (json.solutionName as string | undefined) ?? ''
          onSuccess(comps, solutionName)
        }
      } catch {
        onError('Invalid JSON file. Please upload a valid SCID infrastructure JSON.')
      }
    }
    reader.readAsText(file)
  }

  const handleWizardFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setWizardParseError('')
    parseFile(
      file,
      (comps, solutionName) => {
        setWizardComponents(comps)
        setWizardFileName(file.name)
        setWizardSelectedIds([])
        if (!wizardName && solutionName) setWizardName(solutionName)
        setWizardSolutionName(solutionName)
      },
      setWizardParseError,
    )
    e.target.value = ''
  }

  const toggleWizardComponent = (id: string) => {
    setWizardSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    )
  }

  const selectAllInCategory = (category: string) => {
    const ids = wizardComponents.filter((c) => c.category === category).map((c) => c.id)
    setWizardSelectedIds((prev) => Array.from(new Set([...prev, ...ids])))
  }

  const clearCategory = (category: string) => {
    const ids = new Set(wizardComponents.filter((c) => c.category === category).map((c) => c.id))
    setWizardSelectedIds((prev) => prev.filter((x) => !ids.has(x)))
  }

  // ── Existing solution type helpers ───────────────────────────────────────
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setParseError('')
    parseFile(
      file,
      (comps) => { setParsedComponents(comps); setScidFileName(file.name) },
      setParseError,
    )
    e.target.value = ''
  }

  const sortCategories = (cats: string[]) =>
    [...cats].sort((a, b) => {
      const ai = CATEGORY_ORDER.indexOf(a)
      const bi = CATEGORY_ORDER.indexOf(b)
      return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi)
    })

  const wizardCategories = sortCategories(Array.from(new Set(wizardComponents.map((c) => c.category))))

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <div className="flex gap-6 h-full">
      {/* Sidebar */}
      <div className="w-72 flex-shrink-0 flex flex-col">
        <h2 className="text-xl font-bold text-aegis-dark mb-4">Solution Type Builder</h2>

        {!workspaceId && (
          <p className="text-sm text-amber-600 bg-amber-50 border border-amber-200 rounded px-3 py-2 mb-3">
            Select a workspace from the header to manage solution types.
          </p>
        )}

        {workspaceId && (
          <button
            onClick={openWizard}
            className="flex items-center justify-center gap-2 w-full bg-aegis-dark text-white rounded px-3 py-2 text-sm mb-4 hover:bg-aegis-dark/90 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Solution Type
          </button>
        )}

        <div className="flex flex-col gap-2 overflow-y-auto">
          {solutionTypes.map((st) => (
            <div
              key={st.id}
              className={`flex items-center rounded text-sm transition-colors ${selectedId === st.id && !wizardOpen ? 'bg-aegis-dark text-white' : 'bg-white hover:bg-gray-100'}`}
            >
              <button
                onClick={() => { setSelectedId(st.id); setWizardOpen(false); setParsedComponents([]); setScidFileName('') }}
                className="flex-1 text-left px-3 py-2"
              >
                <div className="font-medium">{st.name}</div>
                <div className="text-xs opacity-60">{(st.component_selection ?? []).length} component type{(st.component_selection ?? []).length !== 1 ? 's' : ''} selected</div>
              </button>
              <button
                onClick={() => {
                  if (window.confirm(`Delete solution type "${st.name}"? This will also delete all associated profiles.`)) {
                    deleteMut.mutate(st.id)
                  }
                }}
                className={`px-2 py-2 opacity-60 hover:opacity-100 transition-opacity ${selectedId === st.id && !wizardOpen ? 'text-white' : 'text-red-500'}`}
                title="Delete solution type"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Main panel */}
      <div className="flex-1 min-w-0">

        {/* ── CREATION WIZARD ── */}
        {wizardOpen && (
          <div className="h-full flex flex-col">
            {/* Wizard header with step indicator */}
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-lg font-semibold text-aegis-dark">New Solution Type</h3>
                <p className="text-sm text-gray-500 mt-0.5">
                  {wizardStep === 'name-and-file'
                    ? 'Step 1 of 2 — Name your solution type and upload its infrastructure definition'
                    : 'Step 2 of 2 — Select which component types to harden with applicable policies'}
                </p>
              </div>
              <button onClick={closeWizard} className="text-gray-400 hover:text-gray-600">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Step progress bar */}
            <div className="flex items-center gap-2 mb-6">
              <div className={`h-1.5 flex-1 rounded-full ${wizardStep === 'name-and-file' ? 'bg-aegis-dark' : 'bg-aegis-dark'}`} />
              <div className={`h-1.5 flex-1 rounded-full ${wizardStep === 'select-components' ? 'bg-aegis-dark' : 'bg-gray-200'}`} />
            </div>

            {/* ── Step 1: Name + File upload ── */}
            {wizardStep === 'name-and-file' && (
              <div className="flex flex-col gap-5 flex-1">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Solution Type Name</label>
                  <input
                    autoFocus
                    placeholder="e.g. HPE Private Cloud AI — Gen2 SM"
                    value={wizardName}
                    onChange={(e) => setWizardName(e.target.value)}
                    className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-aegis-dark/30"
                  />
                  {wizardSolutionName && wizardName !== wizardSolutionName && (
                    <p className="mt-1 text-xs text-gray-400">
                      Detected from file: <button className="underline" onClick={() => setWizardName(wizardSolutionName)}>{wizardSolutionName}</button>
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Infrastructure Definition (SCID JSON)
                    <span className="ml-1 text-red-500">*</span>
                  </label>
                  <p className="text-xs text-gray-500 mb-3">
                    Upload the <strong>infra-layout.json</strong> or <strong>base-configuration.json</strong> file for this solution.
                    Aegis will parse its hierarchical structure to identify all component types (servers, switches, storage, PDUs)
                    present in the solution.
                  </p>

                  {/* Drop zone */}
                  <div
                    className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer
                      ${wizardFileName ? 'border-green-400 bg-green-50' : 'border-gray-300 bg-gray-50 hover:border-aegis-dark hover:bg-aegis-dark/5'}`}
                    onClick={() => wizardFileRef.current?.click()}
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={(e) => {
                      e.preventDefault()
                      const file = e.dataTransfer.files[0]
                      if (file) {
                        setWizardParseError('')
                        parseFile(
                          file,
                          (comps, solutionName) => {
                            setWizardComponents(comps)
                            setWizardFileName(file.name)
                            setWizardSelectedIds([])
                            if (!wizardName && solutionName) setWizardName(solutionName)
                            setWizardSolutionName(solutionName)
                          },
                          setWizardParseError,
                        )
                      }
                    }}
                  >
                    <input ref={wizardFileRef} type="file" accept=".json" className="hidden" onChange={handleWizardFileUpload} />

                    {wizardFileName ? (
                      <>
                        <svg className="w-10 h-10 mx-auto mb-2 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                        </svg>
                        <p className="text-sm font-semibold text-green-700">{wizardFileName}</p>
                        <p className="text-xs text-green-600 mt-1">
                          {wizardComponents.length} unique component type{wizardComponents.length !== 1 ? 's' : ''} discovered across {wizardCategories.length} categor{wizardCategories.length !== 1 ? 'ies' : 'y'}
                        </p>
                        <button
                          className="mt-3 text-xs text-gray-500 underline"
                          onClick={(e) => { e.stopPropagation(); setWizardFileName(''); setWizardComponents([]); setWizardSelectedIds([]) }}
                        >
                          Replace file
                        </button>
                      </>
                    ) : (
                      <>
                        <svg className="w-10 h-10 mx-auto mb-2 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                        </svg>
                        <p className="text-sm font-medium text-gray-600">Drag & drop or click to upload</p>
                        <p className="text-xs text-gray-400 mt-1">Accepts infra-layout.json, base-configuration.json</p>
                      </>
                    )}
                  </div>
                  {wizardParseError && <p className="mt-2 text-xs text-red-600">{wizardParseError}</p>}
                </div>

                <div className="flex justify-end gap-3 mt-auto pt-4 border-t">
                  <button onClick={closeWizard} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">
                    Cancel
                  </button>
                  <button
                    disabled={!wizardName.trim() || !wizardFileName || wizardComponents.length === 0}
                    onClick={() => setWizardStep('select-components')}
                    className="px-5 py-2 bg-aegis-dark text-white text-sm rounded hover:bg-aegis-dark/90 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    Next — Select Components
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </button>
                </div>
              </div>
            )}

            {/* ── Step 2: Component selection ── */}
            {wizardStep === 'select-components' && (
              <div className="flex flex-col flex-1 min-h-0">
                <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-start gap-3">
                  <svg className="w-5 h-5 text-blue-500 mt-0.5 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                  <div className="text-sm text-blue-800">
                    <strong>Parsed from {wizardFileName}</strong>
                    {wizardSolutionName && <span className="ml-1">({wizardSolutionName})</span>}
                    <span className="ml-1">—</span> select the component types that need security hardening.
                    Aegis will generate Evaluation, Remediation and Rollback code for each selected type.
                  </div>
                </div>

                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm text-gray-600">
                    {wizardSelectedIds.length} of {wizardComponents.length} type{wizardComponents.length !== 1 ? 's' : ''} selected
                  </span>
                  <div className="flex gap-3 text-xs">
                    <button
                      className="text-aegis-dark underline"
                      onClick={() => setWizardSelectedIds(wizardComponents.map((c) => c.id))}
                    >Select all</button>
                    <button
                      className="text-gray-500 underline"
                      onClick={() => setWizardSelectedIds([])}
                    >Clear all</button>
                  </div>
                </div>

                <div className="overflow-y-auto flex-1 space-y-5 pr-1">
                  {wizardCategories.map((category) => {
                    const comps = wizardComponents.filter((c) => c.category === category)
                    const cardBase = CATEGORY_CARD[category] ?? 'bg-gray-50 border-gray-200'
                    const badge = CATEGORY_BADGE[category] ?? 'bg-gray-100 text-gray-800'
                    const allChecked = comps.every((c) => wizardSelectedIds.includes(c.id))
                    return (
                      <div key={category}>
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-500">{category}</h4>
                          <button
                            className="text-xs text-aegis-dark underline"
                            onClick={() => allChecked ? clearCategory(category) : selectAllInCategory(category)}
                          >
                            {allChecked ? 'Deselect all' : 'Select all'}
                          </button>
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                          {comps.map((comp) => {
                            const checked = wizardSelectedIds.includes(comp.id)
                            return (
                              <label
                                key={comp.id}
                                className={`flex items-start gap-3 p-3 rounded-lg border-2 cursor-pointer transition-colors ${
                                  checked ? 'border-aegis-dark bg-aegis-dark/5' : `${cardBase} hover:border-gray-400`
                                }`}
                              >
                                <input
                                  type="checkbox"
                                  checked={checked}
                                  onChange={() => toggleWizardComponent(comp.id)}
                                  className="w-4 h-4 mt-0.5 shrink-0"
                                />
                                <div className="min-w-0">
                                  <span className="text-sm font-medium block leading-snug">{comp.label}</span>
                                  <span className={`mt-1 inline-block text-xs px-1.5 py-0.5 rounded font-medium ${badge}`}>{comp.category}</span>
                                  <span className="ml-1 text-xs text-gray-400">×{comp.instanceCount}</span>
                                  {comp.jsonPaths.length > 0 && (
                                    <span className="block mt-1 text-xs font-mono text-gray-400 truncate" title={comp.jsonPaths.join('\n')}>
                                      {comp.jsonPaths[0]}{comp.jsonPaths.length > 1 ? ` +${comp.jsonPaths.length - 1}` : ''}
                                    </span>
                                  )}
                                </div>
                              </label>
                            )
                          })}
                        </div>
                      </div>
                    )
                  })}
                </div>

                <div className="flex items-center justify-between pt-4 border-t mt-4">
                  <button
                    onClick={() => setWizardStep('name-and-file')}
                    className="flex items-center gap-1.5 text-sm text-gray-600 hover:text-gray-800"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                    </svg>
                    Back
                  </button>
                  <div className="flex gap-3">
                    <button onClick={closeWizard} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">
                      Cancel
                    </button>
                    <button
                      disabled={wizardSelectedIds.length === 0 || createAndConfigureMut.isPending}
                      onClick={() => createAndConfigureMut.mutate()}
                      className="px-5 py-2 bg-aegis-dark text-white text-sm rounded hover:bg-aegis-dark/90 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                      {createAndConfigureMut.isPending ? (
                        <>
                          <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                          </svg>
                          Creating…
                        </>
                      ) : (
                        <>Create Solution Type ({wizardSelectedIds.length} component{wizardSelectedIds.length !== 1 ? 's' : ''})</>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── EXISTING SOLUTION TYPE VIEW ── */}
        {!wizardOpen && selected && (() => {
          const storedIds = selected.component_selection ?? []

          // Build a lookup from parsedComponents for when JSON is loaded
          const parsedMap = new Map(parsedComponents.map((c) => [c.id, c]))

          // Derive display items: if JSON loaded use parsed data; otherwise humanize stored IDs
          const displayItems: { id: string; label: string; category: string; instanceCount: number }[] =
            parsedComponents.length > 0
              ? parsedComponents.map((c) => ({ ...c }))
              : storedIds.map((id) => {
                  const h = humanizeId(id)
                  return { id, label: h.label, category: h.category, instanceCount: 1 }
                })

          const displayCategories = sortCategories(Array.from(new Set(displayItems.map((c) => c.category))))

          // Toggle: if JSON loaded, can add/remove anything; otherwise only toggle stored ids
          const handleToggle = (componentId: string) => {
            const current = storedIds
            const next = current.includes(componentId)
              ? current.filter((c) => c !== componentId)
              : [...current, componentId]
            updateMut.mutate({ id: selected.id, ids: next })
          }

          const allSelected = displayItems.every((c) => storedIds.includes(c.id))
          const selectAll = () => updateMut.mutate({ id: selected.id, ids: displayItems.map((c) => c.id) })
          const clearAll = () => updateMut.mutate({ id: selected.id, ids: [] })

          return (
            <div className="flex flex-col h-full">
              {/* Header */}
              <div className="mb-4 flex items-start justify-between gap-4">
                <div>
                  <h3 className="text-lg font-semibold text-aegis-dark">{selected.name}</h3>
                  <p className="text-sm text-gray-500 mt-1">
                    {storedIds.length > 0
                      ? `${storedIds.length} component type${storedIds.length !== 1 ? 's' : ''} selected for hardening.`
                      : 'No components selected yet.'
                    }
                    {parsedComponents.length === 0 && ' Upload the SCID JSON to see all available components and add more.'}
                  </p>
                </div>
                {displayItems.length > 0 && (
                  <div className="flex gap-3 text-xs shrink-0 mt-1">
                    <button className="text-aegis-dark underline" onClick={selectAll} disabled={allSelected}>Select all</button>
                    <button className="text-gray-500 underline" onClick={clearAll} disabled={storedIds.length === 0}>Clear all</button>
                  </div>
                )}
              </div>

              {/* Upload strip */}
              <div className="mb-5 p-3 bg-gray-50 border border-dashed border-gray-300 rounded-lg flex items-center gap-3 flex-wrap">
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="bg-white border border-gray-300 text-gray-700 rounded px-3 py-1.5 text-sm hover:bg-gray-50 flex items-center gap-2 shrink-0"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                  </svg>
                  {parsedComponents.length > 0 ? 'Replace SCID JSON' : 'Upload SCID JSON to edit'}
                </button>
                <input ref={fileInputRef} type="file" accept=".json" className="hidden" onChange={handleFileUpload} />
                {scidFileName ? (
                  <span className="text-sm text-gray-600 flex items-center gap-1.5">
                    <svg className="w-4 h-4 text-green-500 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    <span className="font-medium">{scidFileName}</span>
                    <span className="text-gray-400">— {parsedComponents.length} type{parsedComponents.length !== 1 ? 's' : ''} found</span>
                  </span>
                ) : (
                  <span className="text-sm text-gray-400 italic">
                    {parsedComponents.length === 0 && 'Upload the SCID JSON to see all available components including unselected ones'}
                  </span>
                )}
                {parseError && <p className="w-full text-xs text-red-600">{parseError}</p>}
              </div>

              {/* Component grid */}
              {displayItems.length > 0 ? (
                <div className="overflow-y-auto flex-1 space-y-5 pr-1">
                  {displayCategories.map((category) => {
                    const comps = displayItems.filter((c) => c.category === category)
                    const cardBase = CATEGORY_CARD[category] ?? 'bg-gray-50 border-gray-200'
                    const badge = CATEGORY_BADGE[category] ?? 'bg-gray-100 text-gray-800'
                    const allCatChecked = comps.every((c) => storedIds.includes(c.id))

                    return (
                      <div key={category}>
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-500 flex items-center gap-2">
                            {category}
                            <span className="normal-case font-normal text-gray-400">
                              {comps.filter((c) => storedIds.includes(c.id)).length}/{comps.length} selected
                            </span>
                          </h4>
                          <button
                            className="text-xs text-aegis-dark underline"
                            onClick={() => {
                              const ids = comps.map((c) => c.id)
                              if (allCatChecked) {
                                updateMut.mutate({ id: selected.id, ids: storedIds.filter((x) => !ids.includes(x)) })
                              } else {
                                updateMut.mutate({ id: selected.id, ids: Array.from(new Set([...storedIds, ...ids])) })
                              }
                            }}
                          >
                            {allCatChecked ? 'Deselect all' : 'Select all'}
                          </button>
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                          {comps.map((comp) => {
                            const checked = storedIds.includes(comp.id)
                            const parsed = parsedMap.get(comp.id)
                            return (
                              <label
                                key={comp.id}
                                className={`flex items-start gap-3 p-3 rounded-lg border-2 cursor-pointer transition-colors ${
                                  checked ? 'border-aegis-dark bg-aegis-dark/5' : `${cardBase} hover:border-gray-400`
                                }`}
                              >
                                <input
                                  type="checkbox"
                                  checked={checked}
                                  onChange={() => handleToggle(comp.id)}
                                  className="w-4 h-4 mt-0.5 shrink-0"
                                />
                                <div className="min-w-0">
                                  <span className="text-sm font-medium block leading-snug">{comp.label}</span>
                                  <span className={`mt-1 inline-block text-xs px-1.5 py-0.5 rounded font-medium ${badge}`}>{comp.category}</span>
                                  {(parsed?.instanceCount ?? comp.instanceCount) > 1 && (
                                    <span className="ml-1 text-xs text-gray-400">×{parsed?.instanceCount ?? comp.instanceCount}</span>
                                  )}
                                  {(parsed?.jsonPaths ?? []).length > 0 && (
                                    <span className="block mt-1 text-xs font-mono text-gray-400 truncate" title={(parsed!.jsonPaths).join('\n')}>
                                      {parsed!.jsonPaths[0]}{parsed!.jsonPaths.length > 1 ? ` +${parsed!.jsonPaths.length - 1}` : ''}
                                    </span>
                                  )}
                                </div>
                              </label>
                            )
                          })}
                        </div>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <div className="text-center py-14 text-gray-400">
                  <svg className="w-12 h-12 mx-auto mb-3 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <p className="text-sm">No components configured yet. Upload a SCID infrastructure JSON to discover what's available for hardening.</p>
                </div>
              )}
            </div>
          )
        })()}

        {/* ── EMPTY STATE ── */}
        {!wizardOpen && !selected && (
          <div className="flex flex-col items-center justify-center h-full text-gray-400 py-20">
            <svg className="w-16 h-16 mb-4 opacity-20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            {workspaceId
              ? <p className="text-sm">Click <strong className="text-gray-600">New Solution Type</strong> to define a new solution, or select an existing one from the list.</p>
              : <p className="text-sm">Select a workspace to get started.</p>
            }
          </div>
        )}
      </div>
    </div>
  )
}
