import { CircleCheck, OctagonX } from 'lucide-react'
import type { EvalSummary, JsonValue } from '@/api/types'
import { DataTable, type Column } from '@/components/DataTable'
import { decimalEquals } from '@/components/ledger/decimal'
import { humanize, llmModeLabel } from '@/lib/format'
import { formatCount, formatPct } from '@/lib/money'

type Kind = 'ratio' | 'count' | 'text' | 'cases' | 'mode'

interface MetricDef {
  key: string
  label: string
  kind: Kind
  /** Part of the CI gate: must be exactly 100%. */
  gate?: boolean
  hint?: string
}

const METRICS: MetricDef[] = [
  { key: 'cases', label: 'Cases evaluated', kind: 'cases' },
  { key: 'decision_accuracy_golden', label: 'Decision accuracy · golden entries', kind: 'ratio', gate: true },
  { key: 'decision_accuracy_synthetic_rules', label: 'Decision accuracy · synthetic rule cases', kind: 'ratio' },
  { key: 'decision_accuracy_intent', label: 'Decision accuracy · intent cases', kind: 'ratio' },
  { key: 'intent_reviewer_agreement_golden', label: 'Intent reviewer agreement · golden', kind: 'ratio' },
  {
    key: 'explanation_faithfulness_numbers',
    label: 'Explanation faithfulness · numbers',
    kind: 'ratio',
    gate: true,
    hint: 'every number in the prose appears in the findings',
  },
  {
    key: 'explanation_faithfulness_codes',
    label: 'Explanation faithfulness · account codes',
    kind: 'ratio',
    gate: true,
    hint: 'every account code in the prose appears in the findings',
  },
  { key: 'outputs_checked_for_faithfulness', label: 'LLM outputs checked for faithfulness', kind: 'count' },
  { key: 'schema_validity', label: 'Schema validity', kind: 'ratio', hint: 'LLM outputs that parsed into their schema' },
  { key: 'guardrail_fallback_rate', label: 'Guardrail fallback rate', kind: 'ratio' },
  { key: 'cassette_miss_rate', label: 'Cassette miss rate', kind: 'ratio' },
  { key: 'adversarial_echo_free', label: 'Adversarial memos not echoed', kind: 'ratio' },
  { key: 'llm_calls', label: 'LLM calls', kind: 'count' },
  { key: 'llm_mode', label: 'LLM mode', kind: 'mode' },
  { key: 'llm_judge_clarity', label: 'LLM-as-judge clarity', kind: 'text' },
]

interface Row {
  def: MetricDef
  value: JsonValue | undefined
}

const DECIMAL = /^-?\d+(\.\d+)?$/

function guessKind(value: JsonValue | undefined): Kind {
  if (typeof value === 'number') return 'count'
  if (typeof value === 'string' && DECIMAL.test(value)) return 'ratio'
  return 'text'
}

function formatValue(kind: Kind, value: JsonValue | undefined): string {
  if (value == null) return '—'
  if (kind === 'cases' && typeof value === 'object' && !Array.isArray(value)) {
    const parts = Object.entries(value).map(([k, n]) => `${String(n)} ${k}`)
    const total = Object.values(value).reduce<number>((s, n) => s + (typeof n === 'number' ? n : 0), 0)
    return `${total} (${parts.join(' · ')})`
  }
  if (kind === 'ratio' && typeof value === 'string' && DECIMAL.test(value)) return formatPct(value)
  if (kind === 'count' && typeof value === 'number') return formatCount(value)
  if (kind === 'mode' && typeof value === 'string') return llmModeLabel(value)
  return typeof value === 'object' ? JSON.stringify(value) : String(value)
}

function GateCell({ row }: { row: Row }) {
  if (!row.def.gate) return <span className="text-ink-muted">—</span>
  const ok = typeof row.value === 'string' && DECIMAL.test(row.value) && decimalEquals(row.value, '1')
  return ok ? (
    <span className="inline-flex items-center gap-1 text-ledger-green">
      <CircleCheck className="size-4" aria-hidden /> must be 100% · met
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 font-medium text-ledger-red">
      <OctagonX className="size-4" aria-hidden /> must be 100% · not met
    </span>
  )
}

const COLUMNS: Column<Row>[] = [
  {
    id: 'metric',
    header: 'Metric',
    rowHeader: true,
    cell: (r) => (
      <span className="flex flex-col">
        <span>{r.def.label}</span>
        {r.def.hint ? <span className="text-xs text-ink-muted">{r.def.hint}</span> : null}
      </span>
    ),
  },
  {
    id: 'value',
    header: 'Value',
    align: 'right',
    width: '12rem',
    cell: (r) => <span className="num">{formatValue(r.def.kind, r.value)}</span>,
  },
  { id: 'gate', header: 'Gate', width: '14rem', cell: (r) => <GateCell row={r} /> },
]

/** Headline metrics from report.summary; keys we do not know yet are still shown, humanised. */
export function EvalSummaryTable({ summary }: { summary: EvalSummary }) {
  const known = new Set(METRICS.map((m) => m.key))
  const rows: Row[] = [
    ...METRICS.filter((m) => summary[m.key] !== undefined).map((def) => ({ def, value: summary[def.key] })),
    ...Object.keys(summary)
      .filter((k) => !known.has(k))
      .map((k) => ({ def: { key: k, label: humanize(k), kind: guessKind(summary[k]) }, value: summary[k] })),
  ]
  return <DataTable columns={COLUMNS} rows={rows} getRowId={(r) => r.def.key} caption="Evaluation summary metrics" />
}
