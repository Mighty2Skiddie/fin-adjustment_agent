/**
 * String-only number formatting. Amounts arrive as decimal strings ("-2075000.00") and are
 * never converted to floating point: rounding is done on the digits with BigInt, half-up,
 * matching the backend's ROUND_HALF_UP.
 */

const DECIMAL_RE = /^([+-]?)(\d*)(?:\.(\d*))?$/

interface Parsed {
  negative: boolean
  int: string
  frac: string
}

function parse(value: string): Parsed | null {
  const m = DECIMAL_RE.exec(value.trim().replace(/,/g, ''))
  if (!m) return null
  const [, sign = '', int = '', frac = ''] = m
  if (int === '' && frac === '') return null
  return { negative: sign === '-', int: int || '0', frac }
}

/** Round |value| to `places` decimals (half-up) and return [integer digits, fraction digits]. */
function roundDigits(p: Parsed, places: number): [string, string] {
  const frac = p.frac.padEnd(places + 1, '0')
  const keep = frac.slice(0, places)
  const next = frac.charCodeAt(places) - 48
  let scaled = BigInt(p.int + keep)
  if (next >= 5) scaled += 1n
  const digits = scaled.toString().padStart(places + 1, '0')
  const intPart = places === 0 ? digits : digits.slice(0, -places)
  const fracPart = places === 0 ? '' : digits.slice(-places)
  return [intPart.replace(/^0+(?=\d)/, ''), fracPart]
}

function group(intDigits: string): string {
  return intDigits.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

function isZeroDigits(intPart: string, fracPart: string): boolean {
  return /^0*$/.test(intPart + fracPart)
}

export interface FormatOptions {
  /** Prefix positive values with "+" (for deltas). Default false. */
  signed?: boolean
  /** Decimal places. Default 2. */
  places?: number
}

/**
 * "1234567.891" -> "1,234,567.89"; "-850000" -> "-850,000.00".
 * Negatives use a leading minus, not brackets. Unparseable input is returned unchanged.
 */
export function formatMoney(value: string, options: FormatOptions = {}): string {
  const { signed = false, places = 2 } = options
  const p = parse(value)
  if (!p) return value
  const [intPart, fracPart] = roundDigits(p, places)
  const zero = isZeroDigits(intPart, fracPart)
  const body = group(intPart) + (places > 0 ? `.${fracPart}` : '')
  if (zero) return body
  if (p.negative) return `-${body}`
  return signed ? `+${body}` : body
}

/** True when the string is a negative, non-zero amount. */
export function isNegative(value: string | null | undefined): boolean {
  if (value == null) return false
  const p = parse(value)
  return !!p && p.negative && !isZero(value)
}

/** True when the amount is zero (any number of zero decimals). */
export function isZero(value: string | null | undefined): boolean {
  if (value == null) return false
  const p = parse(value)
  return !!p && /^0*$/.test(p.int + p.frac)
}

/** Absolute value as a string, without formatting. */
export function absAmount(value: string): string {
  return value.trim().replace(/^[+-]/, '')
}

/**
 * A ratio string to a percentage: "0.2432" -> "24.3%", "1.0000" -> "100.0%".
 * Shifts the decimal point on the digits; no floating point.
 */
export function formatPct(ratio: string, places = 1): string {
  const p = parse(ratio)
  if (!p) return ratio
  const frac = p.frac.padEnd(2, '0')
  const shifted: Parsed = {
    negative: p.negative,
    int: (p.int + frac.slice(0, 2)).replace(/^0+(?=\d)/, ''),
    frac: frac.slice(2),
  }
  const [intPart, fracPart] = roundDigits(shifted, places)
  const zero = isZeroDigits(intPart, fracPart)
  const body = intPart + (places > 0 ? `.${fracPart}` : '')
  return `${p.negative && !zero ? '-' : ''}${body}%`
}

/** Integer counts with thousands separators (counts and tokens, not money). */
export function formatCount(n: number): string {
  return Number.isFinite(n) ? Math.round(n).toLocaleString('en-US') : String(n)
}

/** Durations in ms (timings are plain numbers, not money). */
export function formatMs(ms: number): string {
  if (!Number.isFinite(ms)) return '—'
  if (ms < 1) return `${ms.toFixed(3)} ms`
  if (ms < 1000) return `${ms.toFixed(1)} ms`
  return `${(ms / 1000).toFixed(2)} s`
}

/** Exact comparison of two decimal strings (for sorting); unparseable values sort first. */
export function compareDecimal(a: string | null | undefined, b: string | null | undefined): number {
  const pa = a == null ? null : parse(a)
  const pb = b == null ? null : parse(b)
  if (!pa || !pb) return pa ? 1 : pb ? -1 : 0
  const places = Math.max(pa.frac.length, pb.frac.length)
  const toBig = (p: Parsed) => {
    const v = BigInt(p.int + p.frac.padEnd(places, '0'))
    return p.negative ? -v : v
  }
  const va = toBig(pa)
  const vb = toBig(pb)
  return va < vb ? -1 : va > vb ? 1 : 0
}
