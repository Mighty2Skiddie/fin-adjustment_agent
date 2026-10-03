/**
 * Exact addition of decimal strings for client-side subtotals and the lineage footer.
 * Amounts are scaled to integers (cents, or finer when an input carries more places) and added
 * as BigInt, so a subtotal shown on screen is the exact sum of the strings the server sent.
 */

const DECIMAL_RE = /^([+-]?)(\d+)(?:\.(\d+))?$/

interface Scaled {
  negative: boolean
  int: string
  frac: string
}

function parse(value: string): Scaled | null {
  const m = DECIMAL_RE.exec(value.trim())
  if (!m) return null
  return { negative: m[1] === '-', int: m[2] ?? '0', frac: m[3] ?? '' }
}

function toBigInt(p: Scaled, scale: number): bigint {
  const v = BigInt(p.int + p.frac.padEnd(scale, '0'))
  return p.negative ? -v : v
}

function fromBigInt(v: bigint, scale: number): string {
  const negative = v < 0n
  const digits = (negative ? -v : v).toString().padStart(scale + 1, '0')
  const int = digits.slice(0, digits.length - scale)
  const frac = digits.slice(digits.length - scale)
  return `${negative ? '-' : ''}${int}${scale > 0 ? `.${frac}` : ''}`
}

/**
 * Sum decimal strings exactly. Null/undefined entries (e.g. FX components that carry a rate,
 * not an amount) are skipped. Throws on a malformed amount rather than guessing.
 */
export function sumDecimals(values: ReadonlyArray<string | null | undefined>, minScale = 2): string {
  const parsed: Scaled[] = []
  for (const value of values) {
    if (value == null) continue
    const p = parse(value)
    if (!p) throw new Error(`Not a decimal amount: ${value}`)
    parsed.push(p)
  }
  const scale = parsed.reduce((s, p) => Math.max(s, p.frac.length), minScale)
  const total = parsed.reduce((acc, p) => acc + toBigInt(p, scale), 0n)
  return fromBigInt(total, scale)
}

/** Exact equality of two decimal strings regardless of trailing zeros ("1.0" == "1.00"). */
export function decimalEquals(a: string, b: string): boolean {
  const pa = parse(a)
  const pb = parse(b)
  if (!pa || !pb) return false
  const scale = Math.max(pa.frac.length, pb.frac.length)
  return toBigInt(pa, scale) === toBigInt(pb, scale)
}

/** |value| > |limit|, exactly. Used for "imbalance above materiality". */
export function absExceeds(value: string, limit: string): boolean {
  const pv = parse(value)
  const pl = parse(limit)
  if (!pv || !pl) return false
  const scale = Math.max(pv.frac.length, pl.frac.length)
  const abs = (x: bigint) => (x < 0n ? -x : x)
  return abs(toBigInt(pv, scale)) > abs(toBigInt(pl, scale))
}
