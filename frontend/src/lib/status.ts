/** Ordering and labels for severities, decisions and invariants (shared by chips and pages). */
import type { Decision, HealthSeverity, Severity } from '@/api/types'

/** Rule severities (INFO/WARN/ESCALATE/BLOCK), health severities (CRITICAL…INFO), PASS from traces. */
export type AnySeverity = Severity | HealthSeverity | 'PASS'

/** Higher = more severe. Rule and health scales share one ladder for sorting. */
export const SEVERITY_RANK: Record<AnySeverity, number> = {
  PASS: 0,
  INFO: 1,
  LOW: 2,
  WARN: 3,
  MEDIUM: 3,
  ESCALATE: 4,
  HIGH: 4,
  BLOCK: 5,
  CRITICAL: 5,
}

export function severityRank(severity: string): number {
  return SEVERITY_RANK[severity as AnySeverity] ?? 0
}

/** Sort order: needs review first, then rejected, then accepted. */
export const DECISION_ORDER: Record<Decision, number> = {
  QUARANTINED: 0,
  REJECTED: 1,
  ACCEPTED: 2,
}

export function decisionLabel(decision: Decision): string {
  return DECISION_LABELS[decision] ?? decision
}

const DECISION_LABELS: Record<Decision, string> = {
  ACCEPTED: 'Accepted',
  QUARANTINED: 'Quarantined',
  REJECTED: 'Rejected',
}

const LABELS: Record<string, string> = {
  all_entries_decided: 'Every entry has a decision',
  every_line_has_lineage: 'Every ledger line has lineage',
  imbalance_unchanged: 'Posting did not change the TB imbalance',
  lineage_reconciles: 'Lineage components sum to each line',
  llm_outputs_guarded: 'Every LLM output passed guardrails or fell back',
  unmapped_not_in_coa_subtotals: 'Unmapped accounts kept out of COA subtotals',
  debits_equal_credits: 'Debits equal credits',
}

export function invariantLabel(key: string): string {
  return LABELS[key] ?? key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' ')
}
