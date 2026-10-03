import { Link } from 'react-router-dom'
import type { PostedLine, PostedTb } from '@/api/types'
import { AssumptionChip } from '@/components/AssumptionChip'
import { InvariantList } from '@/components/InvariantList'
import { Money } from '@/components/Money'
import { SectionHeading } from '@/components/PageHeader'
import { StatStrip, type Stat } from '@/components/StatStrip'
import { absAmount, formatMoney, isZero } from '@/lib/money'
import { absExceeds } from './decimal'

interface TranslationDiff {
  account: PostedLine
  amount: string
}

/** The system line that absorbed the translated source TB's imbalance (assumption A3), if any. */
function findTranslationDiff(lines: readonly PostedLine[]): TranslationDiff | null {
  for (const line of lines) {
    const ref = line.lineage.find((r) => r.kind === 'TRANSLATION_DIFF')
    if (ref?.amount) return { account: line, amount: ref.amount }
  }
  return null
}

function TranslationNote({
  runId,
  diff,
  onOpenAccount,
}: {
  runId: string
  diff: TranslationDiff
  onOpenAccount: (code: string) => void
}) {
  const { account } = diff
  return (
    <div className="flex flex-col gap-1.5 rounded-sm border border-ledger-amber/50 bg-ledger-amber-tint px-4 py-3 text-sm">
      <p className="font-medium text-ink">Translation difference posted to {account.account_code}</p>
      <p className="max-w-prose text-ink">
        After FX translation the source trial balance was out by{' '}
        <span className="num font-medium">{formatMoney(absAmount(diff.amount))}</span> (
        <Link to={`/runs/${encodeURIComponent(runId)}/health`} className="font-mono text-act underline">
          H-TB-01
        </Link>
        ). That amount is posted to{' '}
        <span className="num">{account.account_code}</span> {account.account_name} as a flagged
        system line, so the adjusted TB balances. It is not a plug: open account{' '}
        <button
          type="button"
          className="num rounded-sm text-act underline"
          onClick={() => onOpenAccount(account.account_code)}
        >
          {account.account_code}
        </button>{' '}
        to see it in the lineage.
      </p>
      <div>
        <AssumptionChip id="A3" />
      </div>
    </div>
  )
}

export interface LedgerTotalsProps {
  runId: string
  tb: PostedTb
  /** Imbalance tolerance from the health report (stricter of abs / pct). Null when unknown. */
  materiality: string | null
  onOpenAccount: (code: string) => void
}

export function LedgerTotals({ runId, tb, materiality, onOpenAccount }: LedgerTotalsProps) {
  const { totals } = tb
  const imbalanceZero = isZero(totals.imbalance)
  // Unknown materiality: be conservative and treat any non-zero imbalance as material.
  const material = !imbalanceZero && (materiality == null || absExceeds(totals.imbalance, materiality))
  const diff = findTranslationDiff(tb.lines)

  const stats: Stat[] = [
    { label: 'Total debits', value: <Money value={totals.debit} tone="none" dimZero={false} /> },
    { label: 'Total credits', value: <Money value={totals.credit} tone="none" dimZero={false} /> },
    {
      label: 'Imbalance (Dr − Cr)',
      value: <Money value={totals.imbalance} tone="none" dimZero={false} />,
      tone: imbalanceZero ? 'green' : material ? 'red' : 'amber',
      note: imbalanceZero
        ? 'balanced'
        : material
          ? `above materiality ${materiality ? formatMoney(materiality) : ''}`.trim()
          : `within materiality ${materiality ? formatMoney(materiality) : ''}`.trim(),
    },
    {
      label: 'Human decisions applied',
      value: <span className="num">{tb.human_decisions}</span>,
      note: tb.human_decisions === 0 ? 'system decisions only' : 'approved entries posted',
    },
  ]

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_26rem]">
      <div className="flex flex-col gap-3">
        <StatStrip stats={stats} className="grid-cols-1 sm:grid-cols-2 2xl:grid-cols-4" />
        {diff ? <TranslationNote runId={runId} diff={diff} onOpenAccount={onOpenAccount} /> : null}
      </div>
      <section aria-labelledby="ledger-invariants" className="rounded-sm border border-rule bg-surface px-4 py-3">
        <SectionHeading id="ledger-invariants" className="pb-2">
          Invariants
        </SectionHeading>
        <InvariantList invariants={tb.invariants} />
      </section>
    </div>
  )
}
