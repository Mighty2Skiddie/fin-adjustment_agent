import { Bot, ChevronRight } from 'lucide-react'
import { useId, useState } from 'react'
import type { Finding } from '@/api/types'
import { Button } from '@/components/ui/button'
import { isLlmFinding } from '@/lib/format'
import { cn } from '@/lib/utils'
import { AssumptionChip } from '../AssumptionChip'
import { Chip } from '../Chip'
import { EvidenceTable } from '../EvidenceTable'
import { severityRank } from '@/lib/status'
import { SeverityChip } from '../SeverityChip'

function FindingItem({ finding }: { finding: Finding }) {
  const [open, setOpen] = useState(false)
  const id = useId()
  return (
    <li className="flex flex-col gap-1.5 border-b border-rule/70 py-2.5 first:pt-0 last:border-b-0">
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="font-mono text-sm font-medium">{finding.rule_id}</span>
        <SeverityChip severity={finding.severity} />
        {isLlmFinding(finding.produced_by) ? (
          <Chip tone="act" variant="outline" icon={<Bot aria-hidden />} title={finding.produced_by}>
            reviewer
          </Chip>
        ) : null}
        {finding.assumption ? <AssumptionChip id={finding.assumption} /> : null}
      </div>
      <p className="font-medium text-ink">{finding.title}</p>
      <p className="text-sm text-ink">{finding.message}</p>
      {finding.suggested_action ? (
        <p className="text-sm text-ink-muted">
          <span className="font-medium text-ink">Suggested: </span>
          {finding.suggested_action}
        </p>
      ) : null}
      <div>
        <Button
          variant="ghost"
          size="xs"
          aria-expanded={open}
          aria-controls={id}
          onClick={() => setOpen((o) => !o)}
          className="-ml-2 text-ink-muted hover:text-ink"
        >
          <ChevronRight
            aria-hidden
            className={cn('transition-transform duration-150', open && 'rotate-90')}
          />
          {open ? 'Hide evidence' : 'Show evidence'}
        </Button>
        {open ? (
          <div id={id} className="mt-1 rounded-sm border border-rule bg-paper">
            <EvidenceTable
              evidence={finding.evidence}
              caption={`Evidence for ${finding.rule_id}`}
            />
          </div>
        ) : null}
      </div>
    </li>
  )
}

/** Findings, most severe first (stable within a severity). */
export function FindingList({ findings, className }: { findings: Finding[]; className?: string }) {
  if (findings.length === 0) {
    return <p className="text-sm text-ink-muted">No findings — every rule passed.</p>
  }
  const ordered = findings
    .map((f, i) => ({ f, i }))
    .sort((a, b) => severityRank(b.f.severity) - severityRank(a.f.severity) || a.i - b.i)
    .map((x) => x.f)
  return (
    <ul className={cn('flex flex-col', className)}>
      {ordered.map((f, i) => (
        <FindingItem key={`${f.rule_id}-${i}`} finding={f} />
      ))}
    </ul>
  )
}
