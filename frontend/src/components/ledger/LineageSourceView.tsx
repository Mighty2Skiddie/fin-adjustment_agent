import { Link } from 'react-router-dom'
import type { JsonObject, LineageComponent } from '@/api/types'
import { AssumptionChip } from '@/components/AssumptionChip'
import { formatTimestamp } from '@/lib/format'
import { asObject, asText } from './lineageSource'

function Fields({ rows }: { rows: [string, string | null][] }) {
  const present = rows.filter((r): r is [string, string] => r[1] != null && r[1] !== '')
  if (present.length === 0) return null
  return (
    <dl className="grid grid-cols-[max-content_minmax(0,1fr)] gap-x-3 gap-y-0.5 text-xs">
      {present.map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="text-ink-muted">{k}</dt>
          <dd className="font-mono break-words text-ink">{v}</dd>
        </div>
      ))}
    </dl>
  )
}

function Raw({ label, text }: { label: string; text: string }) {
  return (
    <figure className="flex flex-col gap-1">
      <figcaption className="text-xs text-ink-muted">{label}</figcaption>
      <pre
        tabIndex={0}
        className="overflow-x-auto rounded-sm border border-rule bg-band px-2.5 py-1.5 text-xs leading-relaxed whitespace-pre text-ink"
      >
        {text}
      </pre>
    </figure>
  )
}

function TbRowSource({ source }: { source: JsonObject }) {
  const file = asText(source.file) ?? 'source file'
  const index = asText(source.row_index)
  const raw = asText(source.raw)
  return raw ? (
    <Raw label={`${file}${index != null ? ` · data row ${index} (0-based, as delivered)` : ''}`} text={raw} />
  ) : (
    <p className="text-xs text-ledger-red">The raw CSV row could not be found for this reference.</p>
  )
}

function FxSource({ source }: { source: JsonObject }) {
  const rate = asObject(source.rate)
  if (!rate) return <p className="text-xs text-ledger-red">The FX rate record could not be found.</p>
  const requested = asText(rate.requested_rate_type)
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs text-ink-muted">FX rate record (fx_rates.csv)</span>
      <Fields
        rows={[
          ['id', asText(rate.id)],
          ['currency', asText(rate.currency)],
          ['rate type', asText(rate.rate_type)],
          ['rate', asText(rate.rate)],
          ['period', asText(rate.period)],
          ['requested', requested ? `${requested} (missing)` : null],
        ]}
      />
    </div>
  )
}

function JeSource({ runId, source }: { runId: string; source: JsonObject }) {
  const entryId = asText(source.entry_id)
  const lineNo = asText(source.line_number)
  const description = asText(source.description)
  const line = asObject(source.line)
  return (
    <div className="flex flex-col gap-1.5">
      <p className="text-xs">
        {entryId ? (
          <Link
            to={`/runs/${encodeURIComponent(runId)}/entries/${encodeURIComponent(entryId)}`}
            className="font-mono font-medium text-act underline"
          >
            {entryId}
          </Link>
        ) : null}
        {lineNo ? <span className="text-ink-muted"> · line {lineNo}</span> : null}
        {description ? <span className="text-ink"> — {description}</span> : null}
      </p>
      {line ? (
        <Raw label="JE line as submitted (manual_adjustments.json)" text={JSON.stringify(line, null, 2)} />
      ) : (
        <p className="text-xs text-ledger-red">The submitted JE line could not be found.</p>
      )}
    </div>
  )
}

function HumanSource({ source }: { source: JsonObject }) {
  const d = asObject(source.decision)
  if (!d) return <p className="text-xs text-ledger-red">The decision record could not be found.</p>
  const ts = asText(d.ts)
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs text-ink-muted">Decision record (human_decisions.json)</span>
      <Fields
        rows={[
          ['decision', asText(d.id)],
          ['entry', `${asText(d.entry_id) ?? ''} v${asText(d.entry_version) ?? '?'}`],
          ['action', asText(d.action)],
          ['actor', asText(d.actor)],
          ['reason', asText(d.reason)],
          ['recorded', ts ? formatTimestamp(ts) : null],
          ['before', asText(d.before_decision)],
        ]}
      />
    </div>
  )
}

function TranslationSource({ runId, source }: { runId: string; source: JsonObject }) {
  return (
    <div className="flex flex-col gap-1.5 text-xs">
      <p className="text-ink">
        {asText(source.note) ?? 'System-generated line.'} It balances the translated source TB; see{' '}
        <Link to={`/runs/${encodeURIComponent(runId)}/health`} className="font-mono text-act underline">
          H-TB-01
        </Link>{' '}
        for the imbalance under each FX policy.
      </p>
      <div>
        <AssumptionChip id="A3" />
      </div>
    </div>
  )
}

/** The raw source behind one lineage component, shown the way it was delivered. */
export function LineageSourceView({ runId, component }: { runId: string; component: LineageComponent }) {
  const { source } = component
  switch (component.kind) {
    case 'TB_ROW':
      return <TbRowSource source={source} />
    case 'FX':
      return <FxSource source={source} />
    case 'JE':
      return <JeSource runId={runId} source={source} />
    case 'HUMAN':
      return <HumanSource source={source} />
    case 'TRANSLATION_DIFF':
      return <TranslationSource runId={runId} source={source} />
    default:
      return null
  }
}
