import { Check, CircleCheck, Copy, OctagonX, Quote } from 'lucide-react'
import { useState } from 'react'
import type { FixCandidate } from '@/api/types'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { AccountCode } from '../AccountCode'
import { Money } from '../Money'

function blockingRuleIds(c: FixCandidate): string[] {
  return c.revalidation
    .filter((f) => f.severity === 'BLOCK' || f.severity === 'ESCALATE')
    .map((f) => f.rule_id)
}

function CopyJsonButton({ candidate }: { candidate: FixCandidate }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(candidate.lines, null, 2))
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1500)
    } catch {
      setCopied(false)
    }
  }
  return (
    <Button variant="outline" size="sm" onClick={() => void copy()}>
      {copied ? <Check aria-hidden /> : <Copy aria-hidden />}
      {copied ? 'Copied' : 'Copy as JSON'}
    </Button>
  )
}

function CandidateCard({ candidate, index }: { candidate: FixCandidate; index: number }) {
  const blocking = blockingRuleIds(candidate)
  return (
    <li className="flex flex-col gap-2 rounded-sm border border-rule bg-paper p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <p className="font-medium">
          <span className="sr-only">Candidate {index + 1}: </span>
          {candidate.label}
        </p>
        {candidate.resolves ? (
          <span className="inline-flex items-center gap-1 text-sm font-medium text-ledger-green">
            <CircleCheck className="size-4" aria-hidden />
            Resolves
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-sm font-medium text-ledger-red">
            <OctagonX className="size-4" aria-hidden />
            Does not resolve
            {blocking.length > 0 ? (
              <span className="font-mono">: {blocking.join(', ')}</span>
            ) : null}
          </span>
        )}
      </div>
      <p className="text-sm text-ink-muted">{candidate.rationale}</p>
      <table className="w-full border-collapse text-sm">
        <caption className="sr-only">Proposed lines for {candidate.label}</caption>
        <thead>
          <tr className="border-b border-rule text-ink-muted">
            <th scope="col" className="py-1 pr-2 text-left font-medium">
              Account
            </th>
            <th scope="col" className="px-1.5 py-1 text-right font-medium">
              Debit
            </th>
            <th scope="col" className="py-1 pl-1.5 text-right font-medium">
              Credit
            </th>
          </tr>
        </thead>
        <tbody>
          {candidate.lines.map((ln, i) => (
            <tr key={i} className="border-b border-rule/70 last:border-b-0">
              <th scope="row" className="py-1 pr-2 text-left font-normal">
                <AccountCode code={ln.account} />
                {ln.memo ? (
                  <span className="block text-xs break-words text-ink-muted">{ln.memo}</span>
                ) : null}
              </th>
              <td className="px-1.5 py-1 text-right">
                <Money value={ln.debit} />
              </td>
              <td className="py-1 pl-1.5 text-right">
                <Money value={ln.credit} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div>
        <CopyJsonButton candidate={candidate} />
      </div>
    </li>
  )
}

/** A question the fix proposer could not answer and the preparer must. */
export function PreparerQuestion({ question, className }: { question: string; className?: string }) {
  return (
    <figure
      className={cn(
        'flex gap-2 border-l-2 border-ledger-amber bg-ledger-amber-tint px-3 py-2',
        className,
      )}
    >
      <Quote className="mt-0.5 size-4 shrink-0 text-ledger-amber-ink" aria-hidden />
      <div className="flex flex-col gap-0.5">
        <figcaption className="text-xs font-medium text-ledger-amber-ink">
          Question for the preparer
        </figcaption>
        <blockquote className="text-sm text-ink">{question}</blockquote>
      </div>
    </figure>
  )
}

export interface FixCandidatesProps {
  candidates: FixCandidate[]
  needsHumanInput?: string | null
  className?: string
}

/** Proposals only — never applied automatically (they can be copied into a resubmission). */
export function FixCandidates({ candidates, needsHumanInput, className }: FixCandidatesProps) {
  return (
    <div className={cn('flex flex-col gap-3', className)}>
      {needsHumanInput ? <PreparerQuestion question={needsHumanInput} /> : null}
      {candidates.length > 0 ? (
        <ol className="flex flex-col gap-3">
          {candidates.map((c, i) => (
            <CandidateCard key={`${c.label}-${i}`} candidate={c} index={i} />
          ))}
        </ol>
      ) : !needsHumanInput ? (
        <p className="text-sm text-ink-muted">No fix proposed.</p>
      ) : null}
    </div>
  )
}
