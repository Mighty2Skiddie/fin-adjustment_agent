import { cn } from '@/lib/utils'
import { AssumptionChip } from '@/components/AssumptionChip'

interface Question {
  n: number
  question: string
  why: string
  fallback: string
  assumptions: string[]
}

/** Summary of docs/07_CLARIFYING_QUESTIONS.md; until answered, the app uses each question's fallback answer. */
const QUESTIONS: Question[] = [
  {
    n: 1,
    question: 'Who owns FX revaluation — the ERP export or our system?',
    why: 'JE-003 revalues EUR cash that the system already translates at period-end, so it would count the gain twice; GBP has no period-end rate.',
    fallback:
      'Translate every row at period-end, quarantine JE-003 with the double-count explained, and fall back to the GBP period-average rate with every affected line flagged.',
    assumptions: ['A2', 'A4'],
  },
  {
    n: 2,
    question: 'Is prior_period_tb.csv pre- or post-close, and is 6905 a rename of 6900?',
    why: 'The prior TB does not balance under any rate policy and holds one P&L account.',
    fallback:
      'Use the prior TB for comparatives only (flagged unreliable) and propose 6905 → 6900 as a mapping a human must approve.',
    assumptions: ['A15', 'A16'],
  },
  {
    n: 3,
    question: 'What materiality applies, and is intercompany in scope?',
    why: 'The tolerance decides block versus flag for every imbalance; 2170 Intercompany Payable has no counterparty TB.',
    fallback:
      'Tolerance 1.00 absolute or 0.1% of debits; larger differences go to 3310 with a CRITICAL flag, never silently plugged. Intercompany balances are kept and flagged.',
    assumptions: ['A3', 'A14'],
  },
]

export function ClarifyingQuestions({ activeAnchor }: { activeAnchor?: string }) {
  return (
    <ol className="flex flex-col gap-3">
      {QUESTIONS.map((q) => (
        <li
          key={q.n}
          id={`question-${q.n}`}
          className={cn(
            'scroll-mt-24 rounded-sm border bg-surface px-4 py-3',
            activeAnchor === `question-${q.n}` ? 'border-act' : 'border-rule',
          )}
        >
          <p className="font-medium text-ink">
            <span className="num mr-2 text-ink-muted">Q{q.n}</span>
            {q.question}
          </p>
          <p className="mt-1 max-w-[75ch] text-sm text-ink-muted">{q.why}</p>
          <p className="mt-2 max-w-[75ch] text-sm text-ink">
            <span className="font-medium">Fallback used: </span>
            {q.fallback}
          </p>
          <p className="mt-2 flex flex-wrap gap-1.5">
            {q.assumptions.map((id) => (
              <AssumptionChip key={id} id={id} />
            ))}
          </p>
        </li>
      ))}
    </ol>
  )
}
