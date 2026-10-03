import type { EntryResult } from '@/api/types'
import { accountNames, bothSidesAccounts, orphanAccounts } from '@/lib/entry'
import { cn } from '@/lib/utils'
import { AccountCode } from '../AccountCode'
import { Chip } from '../Chip'
import { Money } from '../Money'

/** The entry's lines: code + name, debit, credit, memo. Orphans and both-sides accounts flagged. */
export function EntryLines({ result, className }: { result: EntryResult; className?: string }) {
  const orphans = orphanAccounts(result)
  const both = bothSidesAccounts(result)
  const names = accountNames(result)
  return (
    <div className={cn('flex flex-col gap-2', className)}>
      <table className="w-full border-collapse text-sm">
        <caption className="sr-only">Lines of {result.entry.id}</caption>
        <thead>
          <tr className="border-b border-rule text-ink-muted">
            <th scope="col" className="py-1 pr-2 text-left font-medium">
              Account
            </th>
            <th scope="col" className="px-2 py-1 text-right font-medium">
              Debit
            </th>
            <th scope="col" className="py-1 pl-2 text-right font-medium">
              Credit
            </th>
          </tr>
        </thead>
        <tbody>
          {result.entry.lines.map((ln, i) => {
            const isBoth = both.has(ln.account)
            return (
              <tr
                key={i}
                className={cn(
                  'border-b border-rule/70 align-top last:border-b-0',
                  isBoth && 'bg-ledger-amber-tint',
                )}
              >
                <th scope="row" className="py-1.5 pr-2 text-left font-normal">
                  <AccountCode code={ln.account} orphan={orphans.has(ln.account)} />
                  {names.get(ln.account) ? (
                    <span className="block text-sm break-words">{names.get(ln.account)}</span>
                  ) : null}
                  {ln.memo ? (
                    <span className="block text-xs break-words text-ink-muted">{ln.memo}</span>
                  ) : null}
                  {isBoth ? (
                    <Chip tone="amber" variant="outline" className="mt-1 h-auto py-0.5 whitespace-normal">
                      same account both sides
                    </Chip>
                  ) : null}
                </th>
                <td className="px-2 py-1.5 text-right">
                  <Money value={ln.debit} />
                </td>
                <td className="py-1.5 pl-2 text-right">
                  <Money value={ln.credit} />
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
