import { CircleCheck, OctagonX } from 'lucide-react'
import type { EvalReport } from '@/api/types'
import { cn } from '@/lib/utils'

/** The CI gate verdict, with the exact condition it checks. */
export function EvalGateBanner({ report, mismatches }: { report: EvalReport; mismatches: number }) {
  const ok = report.passed
  return (
    <div
      role="status"
      className={cn(
        'flex flex-col gap-1 rounded-sm border px-4 py-3',
        ok ? 'border-ledger-green/50 bg-ledger-green-tint' : 'border-ledger-red/50 bg-ledger-red-tint',
      )}
    >
      <p className={cn('flex items-center gap-2 text-lg font-semibold', ok ? 'text-ledger-green' : 'text-ledger-red')}>
        {ok ? <CircleCheck className="size-5" aria-hidden /> : <OctagonX className="size-5" aria-hidden />}
        Gate {ok ? 'PASSED' : 'FAILED'}
      </p>
      <p className="text-sm text-ink">
        Condition: <span className="font-mono">{report.gate}</span>
      </p>
      <p className="text-sm text-ink-muted">
        {mismatches === 0
          ? `All ${report.entries.length} cases match their expected decision and findings.`
          : `${mismatches} of ${report.entries.length} cases differ from the expectation — marked in the table below.`}
      </p>
    </div>
  )
}
