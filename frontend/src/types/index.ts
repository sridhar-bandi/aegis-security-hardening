// Central TypeScript types for all API entities

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface User {
  id: string
  email: string
  username: string
  role: 'admin' | 'security_officer' | 'auditor' | 'user'
  is_active: boolean
  created_at: string
}

export interface Workspace {
  id: string
  name: string
  description: string | null
  owner_id: string
  created_at: string
}

export interface Policy {
  id: string
  workspace_id: string
  name: string
  description: string | null
  standard: string
  format: string
  code_status: 'pending' | 'generating' | 'generated' | 'reviewed' | 'approved' | 'rejected'
  created_at: string
  rule_count: number
  target_component_types: string[]
}

export interface PolicyRule {
  id: string
  policy_id: string
  rule_id: string
  title: string
  description: string | null
  rationale: string | null
  severity: 'critical' | 'high' | 'medium' | 'low' | 'informational'
  category: string | null
  target_component_types: string[] | null
  check_content: string | null
  fix_text: string | null
  created_at: string
}

export interface SolutionType {
  id: string
  workspace_id: string
  name: string
  description: string | null
  component_selection: string[] | null
  created_at: string
}

export interface HardeningProfile {
  id: string
  name: string
  solution_type_id: string
  policy_id: string | null
  component_policy_map: Record<string, string> | null
  status: 'draft' | 'generating' | 'ready'
  created_at: string
}

export interface ProfileRule {
  id: string
  profile_id: string
  policy_rule_id: string
  component_type: string
  evaluation_code: string | null
  remediation_code: string | null
  rollback_code: string | null
  code_status: 'pending' | 'generated' | 'reviewed' | 'approved' | 'rejected'
  risk_score: number
  created_at: string
  updated_at: string
  rule_title: string | null
  rule_short_id: string | null
}

export interface HITLComment {
  id: string
  profile_rule_id: string
  author_id: string | null
  comment_text: string
  comment_type: 'review' | 'approval' | 'rejection'
  created_at: string
}

export interface SolutionInstance {
  id: string
  workspace_id: string
  name: string
  solution_type_id: string | null
  profile_id: string | null
  owner_id: string
  created_at: string
  scid_json: Record<string, unknown> | null
  scid_filename: string | null
}

export interface EnforcementJob {
  id: string
  instance_id: string
  job_type: 'evaluate' | 'remediate' | 'rollback' | 'dry_run' | 'impact_assessment'
  status: 'pending' | 'running' | 'completed' | 'failed'
  celery_task_id: string | null
  result_summary: Record<string, unknown> | null
  created_at: string
  completed_at: string | null
}

export interface ComplianceReport {
  id: string
  instance_id: string
  job_id: string | null
  report_type: 'arf' | 'html' | 'summary'
  file_path: string | null
  summary: Record<string, unknown> | null
  created_at: string
}

export type ComplianceLevel = 'red' | 'orange' | 'green'

export function complianceLevel(passPercent: number): ComplianceLevel {
  if (passPercent >= 80) return 'green'
  if (passPercent >= 50) return 'orange'
  return 'red'
}
