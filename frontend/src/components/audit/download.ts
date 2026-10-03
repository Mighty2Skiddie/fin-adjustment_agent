import type { AuditEvent } from '@/api/types'

/** One JSON object per line, exactly as the server returned them (no re-formatting). */
export function toJsonl(events: AuditEvent[]): string {
  return events.map((e) => JSON.stringify(e)).join('\n') + (events.length ? '\n' : '')
}

/** Save the audit log as a .jsonl file from the browser; no extra request to the server. */
export function downloadJsonl(events: AuditEvent[], filename: string): void {
  const blob = new Blob([toJsonl(events)], { type: 'application/x-ndjson' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 0)
}
