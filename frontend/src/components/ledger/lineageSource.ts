import type { JsonObject, JsonValue, LineageComponent } from '@/api/types'

/** Narrowing helpers for the kind-dependent `source` object of a lineage component. */

export function asObject(v: JsonValue | undefined): JsonObject | null {
  return v != null && typeof v === 'object' && !Array.isArray(v) ? v : null
}

export function asText(v: JsonValue | undefined): string | null {
  if (v == null) return null
  if (typeof v === 'string') return v
  if (typeof v === 'number' || typeof v === 'boolean') return String(v)
  return null
}

/** True when the FX rate used is a fallback for a missing rate (policy A4). */
export function isFallbackRate(c: LineageComponent): boolean {
  const rate = asObject(c.source.rate)
  if (rate?.is_fallback === true) return true
  return /fallback/i.test(c.note ?? '')
}
