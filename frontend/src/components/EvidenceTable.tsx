import type { JsonValue } from '@/api/types'
import { humanize } from '@/lib/format'
import { cn } from '@/lib/utils'

type JsonRecord = { [key: string]: JsonValue }

function isRecord(v: JsonValue): v is JsonRecord {
  return typeof v === 'object' && v !== null && !Array.isArray(v)
}

function isPrimitive(v: JsonValue): v is string | number | boolean | null {
  return v === null || typeof v !== 'object'
}

function Primitive({ value }: { value: string | number | boolean | null }) {
  if (value === null) return <span className="font-mono text-ink-muted">null</span>
  if (value === '') return <span className="font-mono text-ink-muted">""</span>
  return <span className="font-mono break-words">{String(value)}</span>
}

/** A list of records with a small shared key set reads best as a mini table. */
function RecordList({ items, depth }: { items: JsonRecord[]; depth: number }) {
  const keys = Array.from(new Set(items.flatMap((i) => Object.keys(i))))
  if (keys.length > 6) {
    return (
      <ol className="flex flex-col gap-2">
        {items.map((item, i) => (
          <li key={i}>
            <EvidenceTable evidence={item} depth={depth + 1} />
          </li>
        ))}
      </ol>
    )
  }
  return (
    <div className="relative max-w-full overflow-x-auto">
      <table className="border-collapse text-xs">
        <thead>
          <tr>
            {keys.map((k) => (
              <th
                key={k}
                scope="col"
                title={k}
                className="border-b border-rule px-2 py-1 text-left font-medium whitespace-nowrap text-ink-muted"
              >
                {humanize(k)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((item, i) => (
            <tr key={i} className="border-b border-rule/60 last:border-b-0">
              {keys.map((k) => (
                <td key={k} className="px-2 py-1 align-top">
                  {k in item ? (
                    <EvidenceValue value={item[k] ?? null} depth={depth + 1} />
                  ) : (
                    <span className="text-ink-muted">—</span>
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function EvidenceValue({ value, depth }: { value: JsonValue; depth: number }) {
  if (isPrimitive(value)) return <Primitive value={value} />
  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="font-mono text-ink-muted">[ ]</span>
    if (value.every(isPrimitive)) {
      return (
        <span className="flex flex-wrap gap-1">
          {value.map((v, i) => (
            <span key={i} className="rounded-sm border border-rule bg-band px-1 font-mono">
              {v === null ? 'null' : String(v)}
            </span>
          ))}
        </span>
      )
    }
    if (value.every(isRecord)) return <RecordList items={value} depth={depth} />
    return (
      <ol className="flex flex-col gap-1">
        {value.map((v, i) => (
          <li key={i}>
            <EvidenceValue value={v} depth={depth + 1} />
          </li>
        ))}
      </ol>
    )
  }
  return <EvidenceTable evidence={value} depth={depth + 1} />
}

export interface EvidenceTableProps {
  /** The finding's `evidence` object (exact values the rule used; decimals are strings). */
  evidence: JsonRecord
  /** Internal: nesting level. */
  depth?: number
  /** Accessible caption for the outermost table. */
  caption?: string
  className?: string
}

/**
 * Key / value view of evidence. Values are shown exactly as the server sent them (mono, not
 * reformatted) because evidence is the audit record; nested objects become nested tables.
 */
export function EvidenceTable({ evidence, depth = 0, caption, className }: EvidenceTableProps) {
  const entries = Object.entries(evidence)
  if (entries.length === 0) return <span className="text-sm text-ink-muted">No evidence.</span>
  return (
    <table
      className={cn(
        'w-full border-collapse text-sm',
        depth > 0 && 'rounded-sm border border-rule bg-paper text-xs',
        className,
      )}
    >
      {caption && depth === 0 ? <caption className="sr-only">{caption}</caption> : null}
      <tbody>
        {entries.map(([key, value]) => (
          <tr key={key} className="border-b border-rule/70 last:border-b-0">
            <th
              scope="row"
              title={key}
              className="w-[38%] px-2 py-1 text-left align-top font-normal text-ink-muted"
            >
              {humanize(key)}
            </th>
            <td className="px-2 py-1 align-top">
              <EvidenceValue value={value} depth={depth} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
