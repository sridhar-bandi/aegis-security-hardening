import api from './client'
import type {
  ComplianceReport,
  EnforcementJob,
  HardeningProfile,
  Policy,
  PolicyRule,
  ProfileRule,
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

// Solution Types
export const listSolutionTypes = (workspaceId: string) =>
  api.get<SolutionType[]>('/solution-types', { params: { workspace_id: workspaceId } }).then((r) => r.data)
export const createSolutionType = (workspaceId: string, name: string, description?: string) =>
  api.post<SolutionType>('/solution-types', { workspace_id: workspaceId, name, description }).then((r) => r.data)
export const updateComponentSelection = (stId: string, selected_component_ids: string[]) =>
  api.patch<SolutionType>(`/solution-types/${stId}/components`, { selected_component_ids }).then((r) => r.data)
export const deleteSolutionType = (stId: string) => api.delete(`/solution-types/${stId}`)

// Profiles
export const createProfile = (name: string, solutionTypeId: string, policyId: string) =>
  api.post<HardeningProfile>('/profiles', { name, solution_type_id: solutionTypeId, policy_id: policyId }).then((r) => r.data)
export const getProfile = (profileId: string) =>
  api.get<HardeningProfile>(`/profiles/${profileId}`).then((r) => r.data)
export const listProfileRules = (profileId: string) =>
  api.get<ProfileRule[]>(`/profiles/${profileId}/rules`).then((r) => r.data)
export const updateRuleCode = (profileId: string, ruleId: string, codes: Partial<Pick<ProfileRule, 'evaluation_code' | 'remediation_code' | 'rollback_code'>>) =>
  api.patch<ProfileRule>(`/profiles/${profileId}/rules/${ruleId}/code`, codes).then((r) => r.data)
export const approveRule = (profileId: string, ruleId: string) =>
  api.post<ProfileRule>(`/profiles/${profileId}/rules/${ruleId}/approve`).then((r) => r.data)
export const rejectRule = (profileId: string, ruleId: string) =>
  api.post<ProfileRule>(`/profiles/${profileId}/rules/${ruleId}/reject`).then((r) => r.data)
export const triggerCodeGen = (profileId: string, ruleIds?: string[]) =>
  api.post<{ task_id: string }>(`/profiles/${profileId}/generate-codes`, { rule_ids: ruleIds ?? null }).then((r) => r.data)
export const deleteProfile = (profileId: string) => api.delete(`/profiles/${profileId}`)

// Instances
export const listInstances = (workspaceId: string) =>
  api.get<SolutionInstance[]>('/instances', { params: { workspace_id: workspaceId } }).then((r) => r.data)
export const createInstance = (workspaceId: string, name: string, solutionTypeId?: string, profileId?: string) =>
  api.post<SolutionInstance>('/instances', { workspace_id: workspaceId, name, solution_type_id: solutionTypeId, profile_id: profileId }).then((r) => r.data)
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
