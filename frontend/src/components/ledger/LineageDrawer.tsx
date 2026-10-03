import {
  ArrowLeftRight,
  CircleCheck,
  FileSpreadsheet,
  NotebookPen,
  OctagonX,
  Scale,
  UserCheck,
} from 'lucide-react'
import type { ReactNode } from 'react'
import { useLineage } from '@/api/queries'
import type { LineageComponent, LineageKind, LineageResponse } from '@/api/types'
import { Chip, type ChipTone } from '@/components/Chip'
import { JsonToggle } from '@/components/JsonToggle'
import { Money } from '@/components/Money'
import { SkeletonLines } from '@/components/SkeletonRows'
import { ErrorState } from '@/components/States'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { cn } from '@/lib/utils'
import { decimalEquals, sumDecimals } from './decimal'
import { isFallbackRate } from './lineageSource'
import { LineageSourceView } from './LineageSourceView'

const KIND: Record<LineageKind, { label: string; tone: ChipTone; variant: 'fill' | 'outline'; icon: ReactNode }> = {
  TB_ROW: { label: 'TB row', tone: 'neutral', variant: 'fill', icon: <FileSpreadsheet aria-hidden /> },
  FX: { label: 'FX rate', tone: 'muted', variant: 'fill', icon: <ArrowLeftRight aria-hidden /> },
  JE: { label: 'JE line', tone: 'neutral', variant: 'outline', icon: <NotebookPen aria-hidden /> },
  HUMAN: { label: 'Human decision', tone: 'green', variant: 'outline', icon: <UserCheck aria-hidden /> },
  TRANSLATION_DIFF: {
    label: 'Translation difference',
    tone: 'amber',
    variant: 'fill',
    icon: <Scale aria-hidden />,
  },
}

function KindBadge({ kind }: { kind: LineageKind }) {
  const k = KIND[kind] ?? { label: kind, tone: 'neutral' as const, variant: 'fill' as const, icon: null }
  return (
    <Chip tone={k.tone} variant={k.variant} icon={k.icon}>
      {k.label}
    </Chip>
  )
}

function NoAmount({ kind }: { kind: LineageKind }) {
  const text =
    kind === 'FX'
      ? 'rate applied to the row above'
      : kind === 'HUMAN'
        ? 'authorises the JE line above'
        : 'no amount'
  return <span className="text-xs text-ink-muted">{text}</span>
}

function ComponentItem({ runId, c, index }: { runId: string; c: LineageComponent; index: number }) {
  return (
    <li className="flex flex-col gap-2 border-b border-rule px-4 py-3 last:border-b-0">
      <div className="flex flex-wrap items-center gap-2">
        <span className="num w-5 text-xs text-ink-muted" aria-hidden>
          {index + 1}.
        </span>
        <KindBadge kind={c.kind} />
        {c.kind === 'FX' && isFallbackRate(c) ? (
          <Chip tone="amber" variant="outline" title="Policy fallback for a missing rate (A4)">
            fallback
          </Chip>
        ) : null}
        <span className="min-w-0 font-mono text-xs break-all text-ink-muted">{c.ref}</span>
        <span className="ml-auto text-right">
          <span className="sr-only">Contribution: </span>
          {c.amount != null ? <Money value={c.amount} signed className="font-medium" /> : <NoAmount kind={c.kind} />}
        </span>
      </div>
      {c.note ? <p className="pl-7 text-sm text-ink">{c.note}</p> : null}
      <div className="flex flex-col gap-1.5 pl-7">
        <LineageSourceView runId={runId} component={c} />
        <JsonToggle data={c.source} label="source record JSON" />
      </div>
    </li>
  )
}

function ReconcileFooter({ data }: { data: LineageResponse }) {
  const amounts = data.components.map((c) => c.amount)
  const counted = amounts.filter((a) => a != null).length
  const sum = sumDecimals(amounts)
  // Both our exact client-side sum and the server's own check must agree.
  const ok = decimalEquals(sum, data.line.net) && data.reconciles
  return (
    <div
      className={cn(
        'flex flex-wrap items-center justify-between gap-x-4 gap-y-1 border-t-2 px-4 py-3 text-sm',
        ok ? 'border-ledger-green/50 bg-ledger-green-tint' : 'border-ledger-red/50 bg-ledger-red-tint',
      )}
    >
      <span className="text-ink">
        Sum of {counted} contributing {counted === 1 ? 'component' : 'components'}
      </span>
      <span className="flex items-center gap-2">
        <Money value={sum} className="font-medium" />
        {ok ? (
          <span className="inline-flex items-center gap-1 font-medium text-ledger-green">
            = line amount
            <CircleCheck className="size-4" aria-hidden />
            <span className="sr-only">(reconciles)</span>
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 font-medium text-ledger-red">
            ≠ line amount <Money value={data.line.net} />
            <OctagonX className="size-4" aria-hidden />
            <span className="sr-only">(does not reconcile)</span>
          </span>
        )}
      </span>
    </div>
  )
}

function LineAmount({ data }: { data: LineageResponse }) {
  const { line } = data
  return (
    <dl className="grid grid-cols-1 gap-px overflow-hidden rounded-sm border border-rule bg-rule sm:grid-cols-3">
      {(
        [
          ['Debit', line.debit],
          ['Credit', line.credit],
          ['Line amount (net)', line.net],
        ] as const
      ).map(([label, value]) => (
        <div key={label} className="flex flex-col-reverse gap-0.5 bg-surface px-3 py-2">
          <dt className="text-xs text-ink-muted">{label}</dt>
          <dd className="text-lg font-medium">
            <Money value={value} dimZero={label !== 'Line amount (net)'} />
          </dd>
        </div>
      ))}
    </dl>
  )
}

function DrawerBody({ runId, account }: { runId: string; account: string }) {
  const q = useLineage(runId, account)
  if (q.isPending) {
    return (
      <div className="px-4">
        <SkeletonLines lines={6} />
      </div>
    )
  }
  if (q.isError) {
    return (
      <div className="px-4">
        <ErrorState error={q.error} onRetry={() => void q.refetch()} title="Couldn't load the lineage" />
      </div>
    )
  }
  const data = q.data
  return (
    <>
      <div className="flex flex-col gap-3 px-4">
        <LineAmount data={data} />
        {!data.line.mapped ? (
          <p className="text-sm text-ledger-amber-ink">
            Unmapped: this line is kept out of every COA subtotal until it is mapped.
          </p>
        ) : null}
        <h3 className="pt-1 text-base font-semibold text-ink">
          Components <span className="font-normal text-ink-muted">({data.components.length})</span>
        </h3>
      </div>
      <ol className="mx-4 rounded-sm border border-rule bg-surface">
        {data.components.map((c, i) => (
          <ComponentItem key={`${c.kind}-${c.ref}-${i}`} runId={runId} c={c} index={i} />
        ))}
      </ol>
      <div className="sticky bottom-0 mt-auto">
        <ReconcileFooter data={data} />
      </div>
    </>
  )
}

export interface LineageDrawerProps {
  runId: string
  /** Account code to show; null keeps the drawer closed. */
  account: string | null
  /** Name shown in the title before the lineage loads. */
  accountName?: string
  onClose: () => void
}

/** Right-hand drawer tracing one ledger line to its TB rows, rates, JE lines and decisions. */
export function LineageDrawer({ runId, account, accountName, onClose }: LineageDrawerProps) {
  return (
    <Sheet
      open={account != null}
      onOpenChange={(open) => {
        if (!open) onClose()
      }}
    >
      <SheetContent
        side="right"
        className="w-full gap-3 overflow-y-auto bg-paper p-0 pb-0 data-[side=right]:w-full data-[side=right]:sm:max-w-xl"
      >
        <SheetHeader className="border-b border-rule bg-surface px-4 py-3 pr-12">
          <SheetTitle className="text-lg font-semibold text-ink">
            Lineage · <span className="num">{account}</span>
            {accountName ? <span className="font-normal"> {accountName}</span> : null}
          </SheetTitle>
          <SheetDescription className="text-sm text-ink-muted">
            Every amount that makes up this line, with the source it came from.
          </SheetDescription>
        </SheetHeader>
        {account ? <DrawerBody runId={runId} account={account} /> : null}
      </SheetContent>
    </Sheet>
  )
}
