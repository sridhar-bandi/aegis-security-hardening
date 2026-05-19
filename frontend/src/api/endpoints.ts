import api from './client'
import type {
  ComplianceReport,
  EnforcementJob,
  HardeningBlueprint,
  Policy,
  PolicyRule,
  PolicyProfile,
  BlueprintRule,
  SolutionInstance,
  SolutionType,
  TokenResponse,
  User,
  Workspace,
} from '../types'

// Auth
export const login = (identifier: string, password: string) =>
  api.post<TokenResponse>('/auth/login', { identifier, password }).then((r) => r.data)

export const register = (email: string, username: string, password: string) =>
  api.post<User>('/auth/register', { email, username, password }).then((r) => r.data)

export const getMe = () => api.get<User>('/users/me').then((r) => r.data)

// Users
export const listUsers = () => api.get<User[]>('/users').then((r) => r.data)
export const updateUserRole = (userId: string, role: string) =>
  api.patch<User>(`/users/${userId}/role`, { role }).then((r) => r.data)
export const deactivateUser = (userId: string) =>
  api.delete(`/users/${userId}`)

// Workspaces
export const listWorkspaces = () => api.get<Workspace[]>('/workspaces').then((r) => r.data)
export const createWorkspace = (name: string, description?: string) =>
  api.post<Workspace>('/workspaces', { name, description }).then((r) => r.data)
export const deleteWorkspace = (id: string) => api.delete(`/workspaces/${id}`)

// Policies
export const listPolicies = (workspaceId: string) =>
  api.get<Policy[]>('/policies', { params: { workspace_id: workspaceId } }).then((r) => r.data)
export const listPolicyRules = (policyId: string) =>
  api.get<PolicyRule[]>(`/policies/${policyId}/rules`).then((r) => r.data)
export const deletePolicy = (policyId: string) => api.delete(`/policies/${policyId}`)
export const generatePolicyCodes = (policyId: string, ruleIds?: string[]) =>
  api.post<{ task_id: string; channel: string }>(`/policies/${policyId}/generate-codes`, { rule_ids: ruleIds ?? null }).then((r) => r.data)

// Policy Rule Review
export const updatePolicyRuleCode = (policyId: string, ruleId: string, codes: Partial<Pick<PolicyRule, 'evaluation_code' | 'remediation_code' | 'rollback_code'>>) =>
  api.patch<PolicyRule>(`/policies/${policyId}/rules/${ruleId}/code`, codes).then((r) => r.data)
export const approvePolicyRule = (policyId: string, ruleId: string) =>
  api.post<PolicyRule>(`/policies/${policyId}/rules/${ruleId}/approve`).then((r) => r.data)
export const rejectPolicyRule = (policyId: string, ruleId: string, reason?: string) =>
  api.post<PolicyRule>(`/policies/${policyId}/rules/${ruleId}/reject`, { reason }).then((r) => r.data)
export const importPolicyRuleCode = (policyId: string, ruleId: string, codeType: string, file: File) => {
  const form = new FormData()
  form.append('file', file)
  return api.post<PolicyRule>(`/policies/${policyId}/rules/${ruleId}/import`, form, {
    params: { code_type: codeType },
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then((r) => r.data)
}

// Policy Profiles
export const createProfile = (policyId: string, data: { name: string; description?: string; profile_type?: string; included_rule_ids?: string[] }) =>
  api.post<PolicyProfile>(`/profiles/policies/${policyId}/profiles`, data).then((r) => r.data)
export const listProfiles = (policyId: string) =>
  api.get<PolicyProfile[]>(`/profiles/policies/${policyId}/profiles`).then((r) => r.data)
export const getProfile = (profileId: string) =>
  api.get<PolicyProfile>(`/profiles/${profileId}`).then((r) => r.data)
export const updateProfile = (profileId: string, data: { name?: string; description?: string; included_rule_ids?: string[] }) =>
  api.patch<PolicyProfile>(`/profiles/${profileId}`, data).then((r) => r.data)
export const deleteProfile = (profileId: string) => api.delete(`/profiles/${profileId}`)
export const promoteProfile = (profileId: string) =>
  api.post<PolicyProfile>(`/profiles/${profileId}/promote`).then((r) => r.data)
export const newProfileVersion = (profileId: string) =>
  api.post<PolicyProfile>(`/profiles/${profileId}/new-version`).then((r) => r.data)
export const listLockedProfiles = (workspaceId: string) =>
  api.get<PolicyProfile[]>(`/profiles/workspace/${workspaceId}`, { params: { status_filter: 'locked' } }).then((r) => r.data)

// Solution Types
export const listSolutionTypes = (workspaceId: string) =>
  api.get<SolutionType[]>('/solution-types', { params: { workspace_id: workspaceId } }).then((r) => r.data)
export const createSolutionType = (workspaceId: string, name: string, description?: string) =>
  api.post<SolutionType>('/solution-types', { workspace_id: workspaceId, name, description }).then((r) => r.data)
export const updateComponentSelection = (stId: string, selected_component_ids: string[]) =>
  api.patch<SolutionType>(`/solution-types/${stId}/components`, { selected_component_ids }).then((r) => r.data)
export const deleteSolutionType = (stId: string) => api.delete(`/solution-types/${stId}`)

// Blueprints
export const listBlueprints = (solutionTypeId: string) =>
  api.get<HardeningBlueprint[]>('/blueprints', { params: { solution_type_id: solutionTypeId } }).then((r) => r.data)
export const listAllBlueprints = (workspaceId: string) =>
  api.get<HardeningBlueprint[]>('/blueprints', { params: { workspace_id: workspaceId } }).then((r) => r.data)
export const createBlueprint = (name: string, solutionTypeId: string, componentProfileMap: Record<string, string>) =>
  api.post<HardeningBlueprint>('/blueprints', { name, solution_type_id: solutionTypeId, component_profile_map: componentProfileMap }).then((r) => r.data)
export const getBlueprint = (blueprintId: string) =>
  api.get<HardeningBlueprint>(`/blueprints/${blueprintId}`).then((r) => r.data)
export const listBlueprintRules = (blueprintId: string) =>
  api.get<BlueprintRule[]>(`/blueprints/${blueprintId}/rules`).then((r) => r.data)
export const updateRuleCode = (blueprintId: string, ruleId: string, codes: Partial<Pick<BlueprintRule, 'evaluation_code' | 'remediation_code' | 'rollback_code'>>) =>
  api.patch<BlueprintRule>(`/blueprints/${blueprintId}/rules/${ruleId}/code`, codes).then((r) => r.data)
export const approveRule = (blueprintId: string, ruleId: string) =>
  api.post<BlueprintRule>(`/blueprints/${blueprintId}/rules/${ruleId}/approve`).then((r) => r.data)
export const rejectRule = (blueprintId: string, ruleId: string) =>
  api.post<BlueprintRule>(`/blueprints/${blueprintId}/rules/${ruleId}/reject`).then((r) => r.data)
export const triggerCodeGen = (blueprintId: string, ruleIds?: string[]) =>
  api.post<{ task_id: string }>(`/blueprints/${blueprintId}/generate-codes`, { rule_ids: ruleIds ?? null }).then((r) => r.data)
export const deleteBlueprint = (blueprintId: string) => api.delete(`/blueprints/${blueprintId}`)

// Instances
export const listInstances = (workspaceId: string) =>
  api.get<SolutionInstance[]>('/instances', { params: { workspace_id: workspaceId } }).then((r) => r.data)
export const createInstance = (workspaceId: string, name: string, solutionTypeId?: string, blueprintId?: string) =>
  api.post<SolutionInstance>('/instances', { workspace_id: workspaceId, name, solution_type_id: solutionTypeId, blueprint_id: blueprintId }).then((r) => r.data)
export const createInstanceWithScid = (workspaceId: string, name: string, scidFile?: File, solutionTypeId?: string, blueprintId?: string) => {
  const form = new FormData()
  form.append('workspace_id', workspaceId)
  form.append('name', name)
  if (solutionTypeId) form.append('solution_type_id', solutionTypeId)
  if (blueprintId) form.append('blueprint_id', blueprintId)
  if (scidFile) form.append('scid_file', scidFile)
  return api.post<SolutionInstance>('/instances/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then((r) => r.data)
}
export const uploadScid = (instanceId: string, scidFile: File) => {
  const form = new FormData()
  form.append('scid_file', scidFile)
  return api.put<SolutionInstance>(`/instances/${instanceId}/scid`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then((r) => r.data)
}
export const evaluateInstance = (instanceId: string) =>
  api.post<EnforcementJob>(`/instances/${instanceId}/evaluate`).then((r) => r.data)
export const remediateInstance = (instanceId: string, ruleIds?: string[]) =>
  api.post<EnforcementJob>(`/instances/${instanceId}/remediate`, { rule_ids: ruleIds ?? null }).then((r) => r.data)
export const rollbackInstance = (instanceId: string, ruleIds?: string[]) =>
  api.post<EnforcementJob>(`/instances/${instanceId}/rollback`, { rule_ids: ruleIds ?? null }).then((r) => r.data)
export const dryRunInstance = (instanceId: string) =>
  api.post<EnforcementJob>(`/instances/${instanceId}/dry-run`).then((r) => r.data)
export const listJobs = (instanceId: string) =>
  api.get<EnforcementJob[]>(`/instances/${instanceId}/jobs`).then((r) => r.data)
export const deleteInstance = (instanceId: string) => api.delete(`/instances/${instanceId}`)
export const pushToNautobot = (instanceId: string, deviceName: string, ruleIds?: string[]) =>
  api.post<{ task_id: string; status: string }>(`/instances/${instanceId}/push-nautobot`, null, {
    params: { device_name: deviceName, rule_ids: ruleIds?.join(',') || undefined },
  }).then((r) => r.data)

// Golden Config Generation
export const generateGoldenConfig = (policyId: string, ruleIds?: string[], configFormat: string = 'cli') =>
  api.post<{ task_id: string; channel: string }>(`/policies/${policyId}/generate-golden-config`, {
    rule_ids: ruleIds ?? null,
    config_format: configFormat,
  }).then((r) => r.data)

// Evaluation Method
export const updateEvaluationMethod = (policyId: string, ruleId: string, evaluationMethod: 'script' | 'nautobot_golden_config') =>
  api.patch<PolicyRule>(`/policies/${policyId}/rules/${ruleId}/evaluation-method`, {
    evaluation_method: evaluationMethod,
  }).then((r) => r.data)
