import { ChevronDown, ChevronRight } from 'lucide-react'
import { Fragment, useState } from 'react'
import type { HealthFileSummary, HealthFinding } from '@/api/types'
import { AssumptionChip, DataTable, EvidenceTable, SeverityChip, type Column } from '@/components'
import { Button } from '@/components/ui/button'
import { formatCount } from '@/lib/money'

function evidenceId(id: string): string {
  return `evidence-${id}`
}

function FindingDetail({ finding }: { finding: HealthFinding }) {
  return (
    <div id={evidenceId(finding.id)} className="flex flex-col gap-3 bg-paper px-4 py-3">
      <div>
        <p className="pb-1 text-xs font-medium text-ink-muted">Evidence</p>
        <div className="max-w-4xl rounded-sm border border-rule bg-surface">
          <EvidenceTable evidence={finding.evidence} caption={`Evidence for ${finding.id}`} />
        </div>
      </div>
      {finding.suggested_action ? (
        <p className="max-w-prose text-sm">
          <span className="font-medium">Suggested action: </span>
          {finding.suggested_action}
        </p>
      ) : null}
    </div>
  )
}

function PolicyCell({ finding }: { finding: HealthFinding }) {
  if (!finding.policy_applied && !finding.assumption) {
    return <span className="text-ink-muted">Reported only</span>
  }
  return (
    <span className="flex flex-col items-start gap-1">
      {finding.policy_applied ? (
        <span className="font-mono text-xs [overflow-wrap:anywhere]">
          {/* Offer line breaks after config-key separators before falling back to mid-word. */}
          {finding.policy_applied.split(/(?<=[._=,])/).map((part, i) => (
            <Fragment key={i}>
              {part}
              <wbr />
            </Fragment>
          ))}
        </span>
      ) : null}
      {finding.assumption ? <AssumptionChip id={finding.assumption} /> : null}
    </span>
  )
}

/** One input file's defects, in the server's order (most severe first). */
export function FileFindingsTable({
  file,
  findings,
}: {
  file: HealthFileSummary
  findings: HealthFinding[]
}) {
  const [open, setOpen] = useState<ReadonlySet<string>>(() => new Set())
  const toggle = (id: string) =>
    setOpen((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })

  const columns: Column<HealthFinding>[] = [
    {
      id: 'id',
      header: 'ID',
      width: '5.75rem',
      rowHeader: true,
      className: 'align-top font-mono whitespace-nowrap',
      cell: (f) => f.id,
    },
    {
      id: 'severity',
      header: 'Severity',
      width: '6.5rem',
      className: 'align-top',
      cell: (f) => <SeverityChip severity={f.severity} />,
    },
    {
      id: 'title',
      header: 'Defect',
      className: 'align-top',
      cell: (f) => (
        <span className="flex flex-col gap-0.5 py-0.5">
          <span className="font-medium text-ink">{f.title}</span>
          <span className="text-ink-muted">{f.message}</span>
          <span className="pt-1 lg:hidden">
            <span className="sr-only">Policy applied: </span>
            <PolicyCell finding={f} />
          </span>
        </span>
      ),
    },
    {
      id: 'evidence',
      header: 'Evidence',
      width: '5.5rem',
      className: 'align-top',
      cell: (f) => {
        const expanded = open.has(f.id)
        return (
          <Button
            variant="ghost"
            size="sm"
            aria-expanded={expanded}
            aria-controls={expanded ? evidenceId(f.id) : undefined}
            aria-label={`${expanded ? 'Hide' : 'Show'} evidence for ${f.id}`}
            onClick={() => toggle(f.id)}
            className="-ml-2"
          >
            {expanded ? <ChevronDown aria-hidden /> : <ChevronRight aria-hidden />}
            {expanded ? 'Hide' : 'Show'}
          </Button>
        )
      },
    },
    {
      id: 'policy',
      header: 'Policy applied',
      // Below lg the policy moves into the defect cell so the defect text keeps its width.
      className: 'align-top max-lg:hidden',
      headerClassName: 'w-44 max-lg:hidden',
      cell: (f) => <PolicyCell finding={f} />,
    },
  ]

  const headingId = `file-${file.file.replace(/[^a-z0-9]+/gi, '-')}`

  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-2">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h2 id={headingId} className="text-lg font-semibold text-ink">
          {file.label}{' '}
          <span className="font-mono text-sm font-normal text-ink-muted">{file.file}</span>
        </h2>
        <p className="text-sm text-ink-muted">
          <span className="num text-ink">{formatCount(file.found)}</span> found ·{' '}
          <span className="num">{formatCount(file.listed_in_brief)}</span> listed in brief
        </p>
      </div>
      <DataTable
        columns={columns}
        rows={findings}
        getRowId={(f) => f.id}
        caption={`Defects found in ${file.label} (${file.file})`}
        renderAfterRow={(f) => (open.has(f.id) ? <FindingDetail finding={f} /> : null)}
        empty={<span className="text-ink-muted">No defects found in this file.</span>}
        className="lg:[&>table]:table-fixed"
      />
    </section>
  )
}
