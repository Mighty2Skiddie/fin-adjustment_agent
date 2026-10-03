import { Chip } from '@/components/Chip'

export function MappedCell({ mapped }: { mapped: boolean }) {
  return mapped ? (
    <span className="text-ink-muted">mapped</span>
  ) : (
    <Chip tone="amber" title="Not mapped to a COA node; excluded from COA subtotals (A6)">
      UNMAPPED
    </Chip>
  )
}
