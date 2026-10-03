/** Display helpers for labels, timestamps and codes. Money lives in ./money. */

const FX_POLICY_LABELS: Record<string, string> = {
  fallback_average: 'Missing rate → period average',
  fallback_opening: 'Missing rate → opening rate',
  block: 'Missing rate → block posting',
}

/** "fallback_average" -> "Missing rate → period average". */
export function fxPolicyLabel(policy: string | null | undefined): string {
  if (!policy) return 'Not set'
  return FX_POLICY_LABELS[policy] ?? humanize(policy)
}

const LLM_MODE_LABELS: Record<string, string> = {
  cassette: 'Cassette (recorded)',
  live: 'Live',
  off: 'Off',
  record: 'Recording',
}

export function llmModeLabel(mode: string | null | undefined): string {
  if (!mode) return 'Unknown'
  return LLM_MODE_LABELS[mode] ?? humanize(mode)
}

/** "expected_avg_basis" -> "Expected avg basis"; leaves codes like "R007b" alone. */
export function humanize(key: string): string {
  if (!/[_\s]/.test(key) && /\d/.test(key)) return key
  const words = key.replace(/[_.]+/g, ' ').trim()
  if (!words) return key
  return words.charAt(0).toUpperCase() + words.slice(1)
}

/** ISO timestamp -> "2026-10-01 15:34:06 UTC" (stable, timezone-explicit, sortable). */
export function formatTimestamp(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return `${d.toISOString().slice(0, 19).replace('T', ' ')} UTC`
}

/** ISO date or timestamp -> "2024-12-31". */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  return iso.slice(0, 10)
}

/** "approved by Priya" -> "Approved by Priya"; "system" -> "System". */
export function effectiveStateLabel(state: string): string {
  if (!state) return ''
  return state.charAt(0).toUpperCase() + state.slice(1)
}

/** True when the finding came from the LLM Intent Reviewer rather than a deterministic rule. */
export function isLlmFinding(producedBy: string): boolean {
  return producedBy.startsWith('llm')
}

/** Splits the plain-text explanation into summary, bullets and next step. */
export function parseExplanation(text: string | null): {
  summary: string
  details: string[]
  nextStep: string | null
} {
  if (!text) return { summary: '', details: [], nextStep: null }
  const lines = text.split('\n').map((l) => l.trim()).filter(Boolean)
  let summary = ''
  const details: string[] = []
  let nextStep: string | null = null
  for (const line of lines) {
    if (line.startsWith('- ')) details.push(line.slice(2))
    else if (/^next step:/i.test(line)) nextStep = line.replace(/^next step:\s*/i, '')
    else if (!summary) summary = line
    else details.push(line)
  }
  return { summary, details, nextStep }
}
