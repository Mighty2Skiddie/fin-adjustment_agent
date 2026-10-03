import { useSearchParams } from 'react-router-dom'
import { useHealth, usePostedTb } from '@/api/queries'
import type { PostedLine } from '@/api/types'
import { ErrorState, PageHeader, RunGate, SkeletonRows, StatStrip } from '@/components'
import { LedgerTable, LedgerTotals, LineageDrawer, type LedgerGrouping } from '@/components/ledger'

function LedgerContent({ runId }: { runId: string }) {
  const tb = usePostedTb(runId)
  const health = useHealth(runId)
  const [params, setParams] = useSearchParams()
  const account = params.get('account')
  const grouping: LedgerGrouping = params.get('group') === 'root' ? 'root' : 'flat'

  const update = (key: string, value: string | null) => {
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        if (value == null) next.delete(key)
        else next.set(key, value)
        return next
      },
      { replace: key === 'group' },
    )
  }

  if (tb.isPending) {
    return (
      <div className="flex flex-col gap-6">
        <StatStrip
          loading
          stats={[
            { label: 'Total debits', value: null },
            { label: 'Total credits', value: null },
            { label: 'Imbalance (Dr − Cr)', value: null },
            { label: 'Human decisions applied', value: null },
          ]}
        />
        <SkeletonRows rows={12} columns={7} label="Loading the adjusted trial balance" />
      </div>
    )
  }
  if (tb.isError) {
    return (
      <ErrorState
        error={tb.error}
        onRetry={() => void tb.refetch()}
        title="Couldn't load the adjusted trial balance"
      />
    )
  }

  const data = tb.data
  const selected: PostedLine | undefined = data.lines.find((l) => l.account_code === account)
  const openAccount = (code: string) => update('account', code)

  return (
    <div className="flex flex-col gap-8">
      <LedgerTotals
        runId={runId}
        tb={data}
        materiality={health.data?.materiality_tolerance ?? null}
        onOpenAccount={openAccount}
      />
      <LedgerTable
        lines={data.lines}
        totals={data.totals}
        grouping={grouping}
        onGroupingChange={(g) => update('group', g === 'root' ? 'root' : null)}
        selectedCode={account}
        onSelect={(line) => openAccount(line.account_code)}
      />
      <LineageDrawer
        runId={runId}
        account={account}
        accountName={selected?.account_name}
        onClose={() => update('account', null)}
      />
    </div>
  )
}

export default function LedgerPage() {
  return (
    <>
      <PageHeader
        title="Adjusted trial balance"
        description="The trial balance after posting accepted and approved entries. Select a line to trace it back to source rows, rates, entries and decisions."
      />
      <RunGate>{(runId) => <LedgerContent runId={runId} />}</RunGate>
    </>
  )
}
