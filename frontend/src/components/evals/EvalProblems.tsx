import { CircleCheck } from 'lucide-react'
import type { EvalReport } from '@/api/types'
import { JsonToggle } from '@/components/JsonToggle'

/** Faithfulness violations, schema errors and adversarial echoes, if the report has any. */
export function EvalProblems({ report }: { report: EvalReport }) {
  const groups = [
    {
      key: 'faithfulness',
      label: 'Faithfulness violations',
      count: Object.keys(report.faithfulness_violations ?? {}).length,
      data: report.faithfulness_violations,
    },
    { key: 'schema', label: 'Schema errors', count: report.schema_errors?.length ?? 0, data: report.schema_errors },
    {
      key: 'echo',
      label: 'Adversarial memo echoes',
      count: report.adversarial_echo_cases?.length ?? 0,
      data: report.adversarial_echo_cases,
    },
  ]
  const total = groups.reduce((s, g) => s + g.count, 0)
  if (total === 0) {
    return (
      <p className="flex items-center gap-2 text-sm text-ink">
        <CircleCheck className="size-4 text-ledger-green" aria-hidden />
        No faithfulness violations, schema errors or adversarial memo echoes.
      </p>
    )
  }
  return (
    <ul className="flex flex-col gap-3">
      {groups.map((g) => (
        <li key={g.key} className="rounded-sm border border-rule bg-surface px-4 py-3">
          <p className={g.count > 0 ? 'font-medium text-ledger-red' : 'text-ink-muted'}>
            {g.label}: <span className="num">{g.count}</span>
          </p>
          {g.count > 0 ? <JsonToggle data={g.data} label="details" /> : null}
        </li>
      ))}
    </ul>
  )
}
