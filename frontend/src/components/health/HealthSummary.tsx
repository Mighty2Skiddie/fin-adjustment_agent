import type { HealthResponse } from '@/api/types'
import { StatStrip, type Stat } from '@/components'
import { formatCount } from '@/lib/money'

/** The four headline numbers. `data` undefined renders the same strip with skeleton values. */
export function HealthSummary({ data }: { data: HealthResponse | undefined }) {
  const found = data?.findings.length ?? 0
  const critical = data?.by_severity.CRITICAL ?? 0
  const filesAffected = data?.files.filter((f) => f.found > 0).length ?? 0
  const filesTotal = data?.files.length ?? 0
  const brief = data?.brief_listed_total ?? 0

  const stats: Stat[] = [
    {
      label: 'Defects found',
      value: formatCount(found),
      note: data
        ? `${formatCount(data.findings.filter((f) => f.severity !== 'INFO').length)} above info level`
        : undefined,
    },
    {
      label: 'Critical',
      value: formatCount(critical),
      tone: critical > 0 ? 'red' : 'default',
      note: data ? `plus ${formatCount(data.by_severity.HIGH ?? 0)} high` : undefined,
    },
    {
      label: 'Files affected',
      value: formatCount(filesAffected),
      note: filesTotal > 0 ? `of ${formatCount(filesTotal)} input files` : undefined,
    },
    {
      label: 'Listed in brief vs found by us',
      value: (
        <span>
          {formatCount(brief)}
          <span className="px-1.5 text-lg font-normal text-ink-muted">vs</span>
          {formatCount(found)}
        </span>
      ),
      note: found > brief ? `${formatCount(found - brief)} not in the brief` : undefined,
    },
  ]

  return <StatStrip stats={stats} loading={!data} />
}
