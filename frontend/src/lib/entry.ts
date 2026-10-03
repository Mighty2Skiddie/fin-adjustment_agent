/** Pure helpers about one entry (no React). */
import type { EntryResult, EntryView } from '@/api/types'

/** Whether a reviewer may still decide this entry (system QUARANTINED, no human decision yet). */
export function canDecide(entry: Pick<EntryView, 'decision' | 'human_decision'>): boolean {
  return entry.decision === 'QUARANTINED' && entry.human_decision == null
}

/** Account codes the R002 rule found missing from the chart of accounts. */
export function orphanAccounts(result: Pick<EntryResult, 'findings'>): Set<string> {
  const out = new Set<string>()
  for (const f of result.findings) {
    const missing = f.evidence['missing_accounts']
    if (Array.isArray(missing)) {
      for (const code of missing) if (typeof code === 'string') out.add(code)
    }
  }
  return out
}

/** Accounts that are both debited and credited within the entry. */
export function bothSidesAccounts(result: Pick<EntryResult, 'entry'>): Set<string> {
  const debited = new Set<string>()
  const credited = new Set<string>()
  for (const ln of result.entry.lines) {
    if (!/^[+-]?0*(\.0*)?$/.test(ln.debit)) debited.add(ln.account)
    if (!/^[+-]?0*(\.0*)?$/.test(ln.credit)) credited.add(ln.account)
  }
  return new Set([...debited].filter((a) => credited.has(a)))
}

/** Account names known from the impact preview (entry lines carry only codes). */
export function accountNames(result: Pick<EntryResult, 'impact'>): Map<string, string> {
  return new Map(result.impact.lines.map((l) => [l.account_code, l.account_name]))
}
