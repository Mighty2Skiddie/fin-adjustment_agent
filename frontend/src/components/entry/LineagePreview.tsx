import { Link } from 'react-router-dom'
import type { EntryDetail } from '@/api/types'
import { Chip } from '@/components/Chip'
import { Money } from '@/components/Money'
import { SectionHeading } from '@/components/PageHeader'
import { formatTimestamp } from '@/lib/format'

const TH = 'h-9 border-b border-rule bg-band px-3 text-left font-medium text-ink-muted'
const TD = 'px-3 py-1.5'

function PostingTable({ runId, entry }: { runId: string; entry: EntryDetail }) {
  return (
    <div className="relative overflow-x-auto rounded-sm border border-rule bg-surface">
      <table className="w-full border-collapse text-sm">
        <caption className="sr-only">Whether each line of {entry.entry.id} is in the posted trial balance</caption>
        <thead>
          <tr>
            <th scope="col" className={TH}>Line</th>
            <th scope="col" className={TH}>Account</th>
            <th scope="col" className={TH}>In posted TB</th>
            <th scope="col" className={`${TH} text-right`}>Account balance after posting</th>
          </tr>
        </thead>
        <tbody>
          {entry.lineage_preview.map((l) => (
            <tr key={l.line} className="h-9 border-b border-rule last:border-b-0">
              <th scope="row" className={`${TD} text-left font-normal`}>
                <span className="num">{l.line}</span>
              </th>
              <td className={TD}>
                <Link
                  to={`/runs/${encodeURIComponent(runId)}/ledger?account=${encodeURIComponent(l.account)}`}
                  className="num font-medium text-act underline-offset-4 hover:underline"
                  aria-label={`Open lineage for account ${l.account}`}
                >
                  {l.account}
                </Link>
              </td>
              <td className={TD}>
                {l.posted ? (
                  <Chip tone="green" variant="outline">posted</Chip>
                ) : (
                  <Chip tone="muted" variant="outline">not posted</Chip>
                )}
              </td>
              <td className={`${TD} text-right`}>
                <Money value={l.account_balance} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function DecisionHistory({ entry }: { entry: EntryDetail }) {
  return (
    <div className="relative overflow-x-auto rounded-sm border border-rule bg-surface">
      <table className="w-full border-collapse text-sm">
        <caption className="sr-only">Reviewer decisions on {entry.entry.id}</caption>
        <thead>
          <tr>
            <th scope="col" className={TH}>When (UTC)</th>
            <th scope="col" className={TH}>Decision</th>
            <th scope="col" className={TH}>Reviewer</th>
            <th scope="col" className={TH}>Reason</th>
          </tr>
        </thead>
        <tbody>
          {entry.human_decisions.map((d) => (
            <tr key={d.id} className="border-b border-rule align-top last:border-b-0">
              <th scope="row" className={`${TD} text-left font-normal`}>
                <span className="num">{formatTimestamp(d.ts)}</span>
              </th>
              <td className={TD}>
                <Chip tone={d.action === 'APPROVED' ? 'green' : 'red'}>
                  {d.action === 'APPROVED' ? 'Approved' : 'Rejected'}
                </Chip>
              </td>
              <td className={`${TD} [overflow-wrap:anywhere]`}>{d.actor}</td>
              <td className={`${TD} [overflow-wrap:anywhere]`}>{d.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** Where the entry's lines landed in the posted TB, and who decided it. */
export function LineagePreview({ runId, entry }: { runId: string; entry: EntryDetail }) {
  return (
    <section aria-labelledby="posting-heading" className="flex flex-col gap-6">
      {entry.lineage_preview.length > 0 ? (
        <div>
          <SectionHeading
            id="posting-heading"
            aside="Select an account to trace its ledger balance to source"
          >
            Posting
          </SectionHeading>
          <PostingTable runId={runId} entry={entry} />
        </div>
      ) : null}
      {entry.human_decisions.length > 0 ? (
        <div>
          <SectionHeading id={entry.lineage_preview.length > 0 ? undefined : 'posting-heading'}>
            Reviewer decisions
          </SectionHeading>
          <DecisionHistory entry={entry} />
        </div>
      ) : null}
    </section>
  )
}
