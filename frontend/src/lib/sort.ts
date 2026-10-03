import { compareDecimal } from '@/lib/money'

/** Comparator builders. Money is compared exactly on its digits, never as a float. */
export const sortBy = {
  string:
    <T,>(get: (row: T) => string | null | undefined) =>
    (a: T, b: T) =>
      (get(a) ?? '').localeCompare(get(b) ?? '', 'en', { numeric: true }),
  decimal:
    <T,>(get: (row: T) => string | null | undefined) =>
    (a: T, b: T) =>
      compareDecimal(get(a), get(b)),
  number:
    <T,>(get: (row: T) => number | null | undefined) =>
    (a: T, b: T) =>
      (get(a) ?? 0) - (get(b) ?? 0),
}
