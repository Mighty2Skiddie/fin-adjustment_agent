import type { FxVariant } from '@/api/types'
import { Chip, Money } from '@/components'
import { fxPolicyLabel } from '@/lib/format'
import { formatMoney } from '@/lib/money'
import { cn } from '@/lib/utils'

/** True for "0.00", "-0.00" and missing values; amounts stay strings, never floats. */
const isZeroAmount = (s: string | null | undefined): boolean =>
  s == null || /^-?0+(\.0+)?$/.test(s)

/** API labels use "->"; show a real arrow. */
function variantLabel(label: string): string {
  return label.replace(/\s*->\s*/g, ' → ')
}

/**
 * "TB balance under each FX policy". A table, not a chart: the controller needs the exact
 * imbalance per policy, and the active policy is the one the run posted under.
 */
export function FxPolicyPanel({
  variants,
  fxPolicy,
  materiality,
  loading = false,
}: {
  variants: FxVariant[] | undefined
  fxPolicy: string | null | undefined
  materiality: string | null | undefined
  loading?: boolean
}) {
  return (
    <section
      aria-labelledby="fx-policy-heading"
      className="flex flex-col gap-3 rounded-sm border border-rule bg-surface p-4"
    >
      <div className="flex flex-col gap-1">
        <h2 id="fx-policy-heading" className="text-lg font-semibold text-ink">
          TB balance under each FX policy
        </h2>
        <p className="text-sm text-ink-muted">
          Debits minus credits after translation. The highlighted row is the policy this run used:{' '}
          {fxPolicyLabel(fxPolicy).toLowerCase()}.
        </p>
      </div>

      <div className="relative overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <caption className="sr-only">
            Trial balance debits, credits and imbalance under each FX translation policy
          </caption>
          <thead>
            <tr className="border-b border-rule text-ink-muted">
              <th scope="col" className="py-1.5 pr-2 text-left font-medium">
                Policy
              </th>
              <th scope="col" className="px-2 py-1.5 text-right font-medium">
                Debits / credits
              </th>
              <th scope="col" className="py-1.5 pl-2 text-right font-medium">
                Δ<span className="sr-only"> (imbalance)</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {loading || !variants
              ? Array.from({ length: 4 }, (_, i) => (
                  <tr key={i} className="h-12 border-b border-rule last:border-b-0" aria-hidden>
                    <td colSpan={3} className="py-2">
                      <span className="block h-3.5 w-full rounded-sm bg-band" />
                    </td>
                  </tr>
                ))
              : variants.map((v) => (
                  <tr
                    key={v.key}
                    aria-current={v.active ? 'true' : undefined}
                    className={cn(
                      'border-b border-rule align-top last:border-b-0',
                      v.active && 'bg-act-tint',
                    )}
                  >
                    <th
                      scope="row"
                      className={cn(
                        'w-[40%] py-2 pr-2 text-left font-normal',
                        v.active && 'border-l-2 border-act pl-2',
                      )}
                    >
                      <span className="block text-ink">{variantLabel(v.label)}</span>
                      <span className="mt-0.5 flex flex-wrap items-center gap-1.5">
                        <span className="font-mono text-xs text-ink-muted">{v.key}</span>
                        {v.active ? (
                          <Chip tone="act" variant="fill">
                            In effect
                          </Chip>
                        ) : null}
                      </span>
                    </th>
                    <td className="px-2 py-2 text-right whitespace-nowrap">
                      <span className="block">
                        <span className="sr-only">Debits </span>
                        <Money value={v.debit} tone="none" />
                      </span>
                      <span className="block text-ink-muted">
                        <span className="sr-only">Credits </span>
                        <Money value={v.credit} tone="none" />
                      </span>
                    </td>
                    <td className="py-2 pl-2 text-right whitespace-nowrap">
                      {/* Any non-zero imbalance is a defect, whatever its sign. */}
                      <Money
                        value={v.delta}
                        signed
                        dimZero={false}
                        tone="none"
                        className={isZeroAmount(v.delta) ? undefined : 'font-medium text-ledger-red'}
                      />
                    </td>
                  </tr>
                ))}
          </tbody>
        </table>
      </div>

      {materiality ? (
        <p className="text-xs text-ink-muted">
          Materiality tolerance <span className="num">{formatMoney(materiality)}</span>. The active
          imbalance is posted to a flagged translation-difference line, never absorbed.
        </p>
      ) : null}
    </section>
  )
}
