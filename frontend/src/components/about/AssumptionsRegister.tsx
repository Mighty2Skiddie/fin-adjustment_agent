import { cn } from '@/lib/utils'
import { ASSUMPTIONS, ASSUMPTIONS_SOURCE, assumptionAnchor } from '@/lib/assumptions'

const byId = (a: string, b: string) => a.localeCompare(b, 'en', { numeric: true })

function RegisterTable({ ids, caption, activeAnchor }: { ids: string[]; caption: string; activeAnchor?: string }) {
  return (
    <div className="relative overflow-x-auto rounded-sm border border-rule bg-surface">
      <table className="w-full border-collapse text-sm">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr>
            <th scope="col" className="w-16 border-b border-rule bg-band px-3 py-2 text-left font-medium text-ink-muted">
              ID
            </th>
            <th scope="col" className="border-b border-rule bg-band px-3 py-2 text-left font-medium text-ink-muted">
              {caption}
            </th>
          </tr>
        </thead>
        <tbody>
          {ids.map((id) => (
            <tr
              key={id}
              id={assumptionAnchor(id)}
              aria-current={activeAnchor === assumptionAnchor(id) ? 'location' : undefined}
              className={cn(
                'scroll-mt-24 border-b border-rule last:border-b-0',
                activeAnchor === assumptionAnchor(id) && 'bg-ledger-amber-tint',
              )}
            >
              <th scope="row" className="px-3 py-2 text-left align-top font-medium">
                <span className="num text-ledger-amber-ink">{id}</span>
              </th>
              <td className="max-w-[75ch] px-3 py-2 align-top leading-snug text-ink">{ASSUMPTIONS[id]}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/**
 * The assumptions register that every amber "assumption" chip links into
 * (/about#assumption-A3). Row ids come from assumptionAnchor so the links always land.
 */
export function AssumptionsRegister({ activeAnchor }: { activeAnchor?: string }) {
  const ids = Object.keys(ASSUMPTIONS)
  const assumptions = ids.filter((id) => id.startsWith('A')).sort(byId)
  const decisions = ids.filter((id) => !id.startsWith('A')).sort(byId)
  return (
    <div className="flex flex-col gap-4">
      <p className="max-w-[75ch] text-sm text-ink-muted">
        One line per assumption, from <code className="font-mono">{ASSUMPTIONS_SOURCE}</code>, which also records why
        each was needed, what changes if it is wrong, and our confidence.
      </p>
      <RegisterTable ids={assumptions} caption="Assumption" activeAnchor={activeAnchor} />
      {decisions.length > 0 ? (
        <>
          <h3 className="pt-2 text-base font-semibold text-ink">Build decisions referenced by findings</h3>
          <RegisterTable ids={decisions} caption="Decision" activeAnchor={activeAnchor} />
        </>
      ) : null}
    </div>
  )
}
