import type { Impact } from '@/api/types'
import { cn } from '@/lib/utils'
import { AccountCode } from '../AccountCode'
import { Money } from '../Money'

const TOTALS: { key: keyof Omit<Impact, 'lines'>; label: string }[] = [
  { key: 'net_income_delta', label: 'Net income' },
  { key: 'total_assets_delta', label: 'Total assets' },
  { key: 'total_liabilities_delta', label: 'Total liabilities' },
  { key: 'total_equity_delta', label: 'Total equity' },
]

/**
 * What posting the entry would move: touched COA roots and their children (indented by depth),
 * then net income / assets / liabilities / equity deltas. Deltas are signed debit − credit.
 */
export function ImpactPreview({ impact, className }: { impact: Impact; className?: string }) {
  const lines = [...impact.lines].sort(
    (a, b) => a.account_code.localeCompare(b.account_code, 'en', { numeric: true }) || a.depth - b.depth,
  )
  return (
    <div className={cn('grid gap-4 md:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]', className)}>
      <table className="w-full border-collapse text-sm">
        <caption className="sr-only">Accounts the entry would move</caption>
        <thead>
          <tr className="border-b border-rule text-ink-muted">
            <th scope="col" className="py-1 pr-2 text-left font-medium">
              Account
            </th>
            <th scope="col" className="py-1 pl-2 text-right font-medium">
              Δ net
            </th>
          </tr>
        </thead>
        <tbody>
          {lines.length === 0 ? (
            <tr>
              <td colSpan={2} className="py-2 text-ink-muted">
                No balances move.
              </td>
            </tr>
          ) : (
            lines.map((l) => (
              <tr key={`${l.account_code}-${l.depth}`} className="border-b border-rule/70 last:border-b-0">
                <th scope="row" className="py-1 pr-2 text-left font-normal">
                  <span style={{ paddingLeft: `${l.depth * 1}rem` }} className="inline-block">
                    <AccountCode
                      code={l.account_code}
                      name={l.account_name}
                      className={l.depth === 0 ? 'font-medium' : undefined}
                    />
                  </span>
                </th>
                <td className="py-1 pl-2 text-right">
                  <Money value={l.delta_net} signed />
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
      <dl className="grid grid-cols-2 content-start gap-x-4 gap-y-2 text-sm">
        {TOTALS.map((t) => (
          <div key={t.key} className="flex flex-col">
            <dt className="text-ink-muted">{t.label}</dt>
            <dd>
              <Money value={impact[t.key]} signed />
            </dd>
          </div>
        ))}
      </dl>
    </div>
  )
}
