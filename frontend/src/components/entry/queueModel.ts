/** Pure helpers for the Review Queue (no React). Money stays a string; sums use BigInt. */
import type { Decision, EntryView } from '@/api/types'
import { DECISION_ORDER, severityRank } from '@/lib/status'

export type QueueFilter = 'all' | 'review' | 'rejected' | 'accepted'

export const QUEUE_FILTERS: { id: QueueFilter; label: string; decision: Decision | null }[] = [
  { id: 'all', label: 'All', decision: null },
  { id: 'review', label: 'Needs review', decision: 'QUARANTINED' },
  { id: 'rejected', label: 'Rejected', decision: 'REJECTED' },
  { id: 'accepted', label: 'Accepted', decision: 'ACCEPTED' },
]

export function parseQueueFilter(value: string | null): QueueFilter {
  return QUEUE_FILTERS.some((f) => f.id === value) ? (value as QueueFilter) : 'all'
}

/** Filters act on the effective decision: an approved entry is no longer "needs review". */
export function matchesFilter(entry: EntryView, filter: QueueFilter): boolean {
  const decision = QUEUE_FILTERS.find((f) => f.id === filter)?.decision
  return decision == null || entry.effective_decision === decision
}

export function filterCounts(entries: EntryView[]): Record<QueueFilter, number> {
  const counts: Record<QueueFilter, number> = { all: 0, review: 0, rejected: 0, accepted: 0 }
  for (const e of entries) {
    counts.all += 1
    for (const f of QUEUE_FILTERS) {
      if (f.decision && e.effective_decision === f.decision) counts[f.id] += 1
    }
  }
  return counts
}

/** Entries the system accepted with no human involved (for the empty "needs review" copy). */
export function autoAcceptedCount(entries: EntryView[]): number {
  return entries.filter((e) => e.decision === 'ACCEPTED' && e.human_decision == null).length
}

export function worstSeverityRank(entry: EntryView): number {
  return entry.findings.reduce((max, f) => Math.max(max, severityRank(f.severity)), 0)
}

export function worstFinding(entry: EntryView) {
  let worst: EntryView['findings'][number] | undefined
  for (const f of entry.findings) {
    if (!worst || severityRank(f.severity) > severityRank(worst.severity)) worst = f
  }
  return worst
}

/** Needs review → rejected → accepted, then most severe finding first, then JE id (stable). */
export function queueOrder(entries: EntryView[]): EntryView[] {
  return entries
    .map((e, i) => ({ e, i }))
    .sort(
      (a, b) =>
        DECISION_ORDER[a.e.effective_decision] - DECISION_ORDER[b.e.effective_decision] ||
        worstSeverityRank(b.e) - worstSeverityRank(a.e) ||
        a.e.entry.id.localeCompare(b.e.entry.id, 'en', { numeric: true }) ||
        a.i - b.i,
    )
    .map((x) => x.e)
}

const DECIMAL_RE = /^([+-]?)(\d*)(?:\.(\d*))?$/

/** Exact sum of decimal strings (BigInt on the digits; never floating point). */
export function sumDecimals(values: string[]): string {
  const parsed = values
    .map((v) => DECIMAL_RE.exec(v.trim()))
    .filter((m): m is RegExpExecArray => m !== null && (m[2] !== '' || (m[3] ?? '') !== ''))
  const places = Math.max(2, ...parsed.map((m) => (m[3] ?? '').length))
  let total = 0n
  for (const m of parsed) {
    const digits = BigInt(`${m[2] || '0'}${(m[3] ?? '').padEnd(places, '0')}`)
    total += m[1] === '-' ? -digits : digits
  }
  const negative = total < 0n
  const abs = (negative ? -total : total).toString().padStart(places + 1, '0')
  return `${negative ? '-' : ''}${abs.slice(0, -places)}.${abs.slice(-places)}`
}

export function totalDebits(entry: EntryView): string {
  return sumDecimals(entry.entry.lines.map((l) => l.debit))
}

/** DOM id of an entry's in-place expansion (target of the row's aria-controls). */
export function panelId(jeId: string): string {
  return `entry-panel-${jeId}`
}
