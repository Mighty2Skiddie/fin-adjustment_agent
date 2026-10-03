/**
 * Mirrors the backend JSON exactly (src/finagent/domain/models.py + src/finagent/api).
 * Every money amount, rate and ratio arrives as a decimal STRING ("850000.00", "0.2667").
 * Never convert them with Number()/parseFloat for arithmetic; format them with lib/money.
 */

/** A decimal serialised as a string, e.g. "-2075000.00". */
export type DecimalString = string

export type JsonPrimitive = string | number | boolean | null
export type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue }
export type JsonObject = { [key: string]: JsonValue }

/* ----------------------------------------------------------------- enums */

export type Severity = 'INFO' | 'WARN' | 'ESCALATE' | 'BLOCK'
export type HealthSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO'
export type Decision = 'ACCEPTED' | 'QUARANTINED' | 'REJECTED'
export type HumanAction = 'APPROVED' | 'REJECTED'
export type LlmMode = 'cassette' | 'live' | 'off' | 'record' | (string & {})
export type ExplanationSource = 'llm' | 'template' | 'none' | (string & {})
export type LineageKind = 'TB_ROW' | 'FX' | 'JE' | 'TRANSLATION_DIFF' | 'HUMAN'

/* ------------------------------------------------------------------ runs */

export interface DecisionCounts {
  accepted: number
  quarantined: number
  rejected: number
}

/** GET /api/runs (newest first; `latest` marks the run that "latest" resolves to). */
export interface RunSummary {
  run_id: string
  created_at: string
  counts: DecisionCounts
  status: string
  llm_mode: LlmMode
  fx_policy: string | null
  period: string | null
  latest: boolean
}
/** Alias kept for readability in pages. */
export type Run = RunSummary

export interface RunMetrics {
  auto_accept_rate?: DecimalString
  quarantine_rate?: DecimalString
  reject_rate?: DecimalString
  guardrail_fallback_rate?: DecimalString
  cassette_hit_rate?: DecimalString
  llm_calls?: number
  llm_roles_run?: number
  /** Milliseconds; a plain JSON number (timing, not money). */
  p50_latency_ms?: number
  provider_fallbacks?: number
  langfuse?: string
  [key: string]: JsonValue | undefined
}

/** GET /api/runs/{id} */
export interface Manifest {
  run_id: string
  created_at: string
  code_version: string
  /** file name -> sha256 */
  input_hashes: Record<string, string>
  config_hash: string
  llm_mode: LlmMode
  counts: DecisionCounts
  invariants: Record<string, boolean>
  /** "OK" | "FAILED_INVARIANT" | "BLOCKED" */
  status: string
  metrics: RunMetrics
  fx_policy: string | null
  period: string | null
  latest: boolean
}

/* -------------------------------------------------------------- findings */

/** Exact values a rule used. Decimals are strings; nested objects and lists occur. */
export type Evidence = JsonObject

interface EvidenceBacked {
  title: string
  message: string
  evidence: Evidence
  suggested_action: string | null
  /** Assumption id from docs/08_ASSUMPTIONS.md (e.g. "A3", "D6"); shown as an amber chip. */
  assumption: string | null
}

export interface Finding extends EvidenceBacked {
  rule_id: string
  severity: Severity
  /** "rule" | "llm:intent_reviewer" */
  produced_by: string
}

export interface HealthFinding extends EvidenceBacked {
  /** e.g. "H-TB-01" */
  id: string
  severity: HealthSeverity
  /** source file name, e.g. "trial_balance.csv" */
  file: string
  policy_applied: string | null
}

/* ---------------------------------------------------------------- health */

export interface HealthFileSummary {
  file: string
  label: string
  listed_in_brief: number
  found: number
}

export interface FxVariant {
  /** "raw" | "usd_only" | "pe_gbp_avg" | "pe_gbp_open" */
  key: string
  label: string
  debit?: DecimalString
  credit?: DecimalString
  /** debit - credit under this policy */
  delta?: DecimalString
  active: boolean
}

/** GET /api/runs/{id}/health */
export interface HealthResponse {
  findings: HealthFinding[]
  by_file: Record<string, HealthFinding[]>
  by_severity: Partial<Record<HealthSeverity, number>>
  /** Files in display order. */
  files: HealthFileSummary[]
  brief_listed_total: number
  fx_variants: FxVariant[]
  fx_policy: string | null
  materiality_tolerance: DecimalString | null
}

/* --------------------------------------------------------------- entries */

export interface JeLine {
  account: string
  debit: DecimalString
  credit: DecimalString
  memo: string
}

export interface JournalEntry {
  id: string
  description: string
  date: string
  source: string
  lines: JeLine[]
  version: number
}

export interface FixCandidate {
  label: string
  rationale: string
  lines: JeLine[]
  /** Findings produced by re-running the rules on the proposed lines. */
  revalidation: Finding[]
  /** True iff revalidation has no BLOCK/ESCALATE finding. */
  resolves: boolean
}

export interface ImpactLine {
  account_code: string
  account_name: string
  delta_net: DecimalString
  /** 0 = COA root */
  depth: number
}

export interface Impact {
  lines: ImpactLine[]
  net_income_delta: DecimalString
  total_assets_delta: DecimalString
  total_liabilities_delta: DecimalString
  total_equity_delta: DecimalString
}

export interface ExplanationDetail {
  summary?: string
  details?: string[]
  next_step?: string
  [key: string]: JsonValue | undefined
}

export interface HumanDecision {
  id: string
  entry_id: string
  entry_version: number
  action: HumanAction
  actor: string
  reason: string
  ts: string
  before_decision: Decision
}

/** The stored system result for one entry. */
export interface EntryResult {
  entry: JournalEntry
  findings: Finding[]
  /** System decision (immutable). */
  decision: Decision
  /** Plain text: summary line, "- " bullets, "Next step: …". Null when no explanation ran. */
  explanation: string | null
  explanation_source: ExplanationSource
  explanation_detail: ExplanationDetail | null
  /** e.g. "gemini-2.5-flash" (llm source only) */
  explanation_model: string | null
  fix_candidates: FixCandidate[]
  /** A question for the preparer, when the fix proposer could not decide. */
  needs_human_input: string | null
  impact: Impact
  trace_id: string
}

/** GET /api/runs/{id}/entries item: system result with the human overlay. */
export interface EntryView extends EntryResult {
  /** System decision overlaid with the latest human decision. */
  effective_decision: Decision
  /** "system" | "approved by <actor>" | "rejected by <actor>" */
  effective_state: string
  human_decision: HumanDecision | null
  /** Present only on the single-entry endpoint. */
  human_decisions?: HumanDecision[]
  /** Present only on the single-entry endpoint. */
  lineage_preview?: LineagePreviewLine[]
}

export interface LineagePreviewLine {
  /** 1-based line number in the entry */
  line: number
  account: string
  /** Whether this line is included in the posted TB. */
  posted: boolean
  /** Net balance of the account in the posted TB, or null if the account has none. */
  account_balance: DecimalString | null
}

/** GET /api/runs/{id}/entries/{je} */
export interface EntryDetail extends EntryView {
  human_decisions: HumanDecision[]
  lineage_preview: LineagePreviewLine[]
}

export interface DecisionRequest {
  action: HumanAction
  actor: string
  reason: string
}

/** POST …/decision returns the updated entry view (no human_decisions / lineage_preview). */
export type DecisionResponse = EntryView

/* ---------------------------------------------------------------- ledger */

export interface LineageRef {
  kind: LineageKind
  /** "trial_balance.csv#3" | "GBP/period_average" | "JE-001#2" | "decision:<id>" */
  ref: string
  /** Functional-currency contribution, signed (debit positive). Null for FX rate refs. */
  amount: DecimalString | null
  note: string | null
}

export interface PostedLine {
  account_code: string
  account_name: string
  debit: DecimalString
  credit: DecimalString
  /** debit - credit */
  net: DecimalString
  /** False for the UNMAPPED bucket (e.g. 9999). */
  mapped: boolean
  lineage: LineageRef[]
}

export interface PostedTbTotals {
  debit: DecimalString
  credit: DecimalString
  imbalance: DecimalString
}

/** GET /api/runs/{id}/posted-tb */
export interface PostedTb {
  lines: PostedLine[]
  totals: PostedTbTotals
  /** imbalance_unchanged, every_line_has_lineage, lineage_reconciles, debits_equal_credits */
  invariants: Record<string, boolean>
  /** Number of human decisions overlaid. */
  human_decisions: number
}

/** One lineage component with the raw source it came from. `source` shape depends on kind:
 * TB_ROW: {file, row_index, raw, row}; FX: {rate}; JE: {entry_id, line_number, description, line};
 * HUMAN: decision record; TRANSLATION_DIFF: policy details. */
export interface LineageComponent extends LineageRef {
  source: JsonObject
}

/** GET /api/runs/{id}/lineage/{account} */
export interface LineageResponse {
  line: PostedLine
  components: LineageComponent[]
  components_total: DecimalString
  reconciles: boolean
}

/* ----------------------------------------------------------------- trace */

interface TraceBase {
  ts: string
  run_id?: string
  entry_id: string
}

export interface EntryStartEvent extends TraceBase {
  event: 'entry.start'
  trace_id: string
}
export interface NodeEnterEvent extends TraceBase {
  event: 'node.enter'
  node: string
  iteration?: number
}
export interface NodeExitEvent extends TraceBase {
  event: 'node.exit'
  node: string
  iteration?: number
  duration_ms: number
}
export interface RuleResultEvent extends TraceBase {
  event: 'rule.result'
  rule_id: string
  /** "PASS" when the rule produced no finding. */
  severity: Severity | 'PASS'
  duration_ms: number
  produced_by?: string
  evidence?: Evidence
}
export interface LlmCallEvent extends TraceBase {
  event: 'llm.call'
  role: string
  mode: LlmMode
  model: string
  provider: string
  prompt_hash: string
  cassette_key?: string
  cassette_hit?: boolean
  latency_ms: number
  /** Estimates (characters / 4). */
  input_tokens?: number
  output_tokens?: number
  recorded_at?: string
}
export interface GuardrailResultEvent extends TraceBase {
  event: 'guardrail.result'
  role: string
  attempt: number
  passed: boolean
  violations: string[]
}
export interface LlmRoleEvent extends TraceBase {
  event: 'llm.role'
  role: string
  source: ExplanationSource
  model: string | null
  attempts: number
  guardrail_fallback: boolean
  cassette_miss: boolean
  iteration?: number
  consistent?: boolean
  added_finding?: string | null
  candidates?: number
}
export interface DecisionEvent extends TraceBase {
  event: 'decision'
  decision: Decision
  by: string
}
export interface FixRevalidatedEvent extends TraceBase {
  event: 'fix.revalidated'
  label: string
  resolves: boolean
  rule_ids: string[]
}
export interface HumanDecisionEvent extends TraceBase {
  event: 'decision.human'
  action: HumanAction
  actor: string
  reason: string
}

export type KnownTraceEvent =
  | EntryStartEvent
  | NodeEnterEvent
  | NodeExitEvent
  | RuleResultEvent
  | LlmCallEvent
  | GuardrailResultEvent
  | LlmRoleEvent
  | DecisionEvent
  | FixRevalidatedEvent
  | HumanDecisionEvent

export type TraceEventName = KnownTraceEvent['event']

/** Events the tracer may add later; render them generically. */
export interface UnknownTraceEvent extends TraceBase {
  event: string
  [key: string]: JsonValue | undefined
}

/** GET /api/runs/{id}/trace/{je} items. Narrow with `isTraceEvent(e, 'llm.call')`. */
export type TraceEvent = KnownTraceEvent | UnknownTraceEvent

export function isTraceEvent<K extends TraceEventName>(
  e: TraceEvent,
  name: K,
): e is Extract<KnownTraceEvent, { event: K }> {
  return e.event === name
}

/* ----------------------------------------------------------------- audit */

/** GET /api/runs/{id}/audit-log items. Fields vary by event. */
export interface AuditEvent {
  ts: string
  /** "run.created" | "decision.system" | "decision.human" | "post.completed" | … */
  event: string
  run_id?: string
  entry_id?: string
  actor?: string
  reason?: string
  before?: Decision
  after?: Decision
  rule_ids?: string[]
  decision_id?: string
  lines?: number
  llm_mode?: LlmMode
  status?: string
  [key: string]: JsonValue | undefined
}

/* ----------------------------------------------------------------- evals */

export interface RulePrecisionRecall {
  tp: number
  fp: number
  fn: number
  precision: DecimalString
  recall: DecimalString
}

export interface EvalEntry {
  id: string
  /** "golden" | "synthetic" */
  source: string
  /** "rules" | "intent" | … */
  category: string
  expected_decision: Decision
  actual_decision: Decision
  expected_rule_ids: string[]
  actual_rule_ids: string[]
  expected_llm_rule_ids: string[]
  actual_llm_rule_ids: string[]
  llm_extra_allowed: string[]
  explanation_source: ExplanationSource
  match: boolean
}

export interface EvalSummary {
  cases?: Record<string, number>
  decision_accuracy_golden?: DecimalString
  decision_accuracy_synthetic_rules?: DecimalString
  decision_accuracy_intent?: DecimalString
  explanation_faithfulness_numbers?: DecimalString
  explanation_faithfulness_codes?: DecimalString
  schema_validity?: DecimalString
  guardrail_fallback_rate?: DecimalString
  cassette_miss_rate?: DecimalString
  adversarial_echo_free?: DecimalString
  intent_reviewer_agreement_golden?: DecimalString
  llm_calls?: number
  llm_judge_clarity?: string
  llm_mode?: LlmMode
  outputs_checked_for_faithfulness?: number
  [key: string]: JsonValue | undefined
}

/** GET /api/runs/{id}/evals (404 `evals_missing` when `finagent eval` has not run). */
export interface EvalReport {
  run_id: string
  passed: boolean
  gate: string
  summary: EvalSummary
  per_rule: Record<string, RulePrecisionRecall>
  entries: EvalEntry[]
  faithfulness_violations: Record<string, JsonValue>
  schema_errors: JsonValue[]
  adversarial_echo_cases: JsonValue[]
  judge: JsonValue | null
}

/* ---------------------------------------------------------------- errors */

/** Body of every non-2xx JSON response. */
export interface ApiErrorBody {
  error: {
    code: string
    message_for_user: string
    detail: JsonValue
  }
}
