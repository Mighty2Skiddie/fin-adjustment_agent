import { CircleCheck, Info, OctagonX } from 'lucide-react'
import { useEffect, useId, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { toast } from 'sonner'
import { useDecision } from '@/api/queries'
import type { EntryView, HumanAction } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { formatTimestamp } from '@/lib/format'
import { useLocalStorage } from '@/hooks/useLocalStorage'
import { cn } from '@/lib/utils'

export const MIN_REASON_LENGTH = 10
export const MAX_ACTOR_LENGTH = 200
export const MAX_REASON_LENGTH = 2000
export const ACTOR_STORAGE_KEY = 'finagent.reviewer'

const COPY: Record<HumanAction, { confirm: string; toast: string; heading: string }> = {
  APPROVED: { confirm: 'Approve and post', toast: 'Approved and posted', heading: 'Approve and post' },
  REJECTED: { confirm: 'Reject entry', toast: 'Rejected', heading: 'Reject entry' },
}

interface DecisionFormProps {
  runId: string
  jeId: string
  action: HumanAction
  onCancel: () => void
  onDone?: () => void
}

/** Inline form: reviewer name (remembered), reason (≥ 10 characters), confirm. */
export function DecisionForm({ runId, jeId, action, onCancel, onDone }: DecisionFormProps) {
  const [actor, setActor] = useLocalStorage(ACTOR_STORAGE_KEY, '')
  const [reason, setReason] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const mutation = useDecision(runId)
  // isPending only flips after a re-render; a ref blocks synchronous repeat clicks.
  const inFlight = useRef(false)
  const actorRef = useRef<HTMLInputElement>(null)
  const reasonRef = useRef<HTMLTextAreaElement>(null)
  const ids = { actor: useId(), reason: useId(), actorErr: useId(), reasonErr: useId() }

  useEffect(() => {
    if (actorRef.current && !actorRef.current.value) actorRef.current.focus()
    else reasonRef.current?.focus()
  }, [action])

  const actorError = actor.trim() ? null : 'Enter your name so the decision is attributable.'
  const reasonLength = reason.trim().length
  const reasonError =
    reasonLength >= MIN_REASON_LENGTH
      ? null
      : `Give a reason of at least ${MIN_REASON_LENGTH} characters; it goes into the audit log.`

  const submit = (e: FormEvent) => {
    e.preventDefault()
    setSubmitted(true)
    if (actorError || reasonError || inFlight.current) return
    inFlight.current = true
    mutation.mutate(
      { jeId, action, actor: actor.trim(), reason: reason.trim() },
      {
        onSuccess: () => {
          toast.success(COPY[action].toast, { description: `${jeId} · ${actor.trim()}` })
          onDone?.()
        },
        onSettled: () => {
          inFlight.current = false
        },
      },
    )
  }

  const showActorError = submitted && actorError
  const showReasonError = submitted && reasonError

  return (
    <form
      onSubmit={submit}
      onKeyDown={(e) => {
        if (e.key === 'Escape' && !mutation.isPending) {
          e.preventDefault()
          onCancel()
        }
      }}
      noValidate
      aria-label={`${COPY[action].heading}: ${jeId}`}
      className="flex flex-col gap-3 rounded-sm border border-rule bg-paper p-3"
    >
      <div className="grid gap-3 sm:grid-cols-[minmax(0,14rem)_minmax(0,1fr)]">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor={ids.actor}>Your name</Label>
          <Input
            ref={actorRef}
            id={ids.actor}
            value={actor}
            onChange={(e) => setActor(e.target.value)}
            autoComplete="name"
            maxLength={MAX_ACTOR_LENGTH}
            aria-invalid={showActorError ? true : undefined}
            aria-describedby={showActorError ? ids.actorErr : undefined}
          />
          {showActorError ? (
            <p id={ids.actorErr} className="text-xs text-ledger-red">
              {actorError}
            </p>
          ) : null}
        </div>
        <div className="flex flex-col gap-1.5">
          <div className="flex items-baseline justify-between gap-2">
            <Label htmlFor={ids.reason}>Reason</Label>
            <span
              className={cn(
                'font-mono text-xs',
                reasonLength >= MIN_REASON_LENGTH ? 'text-ink-muted' : 'text-ledger-amber-ink',
              )}
              aria-hidden
            >
              {reasonLength}/{MIN_REASON_LENGTH}+
            </span>
          </div>
          <Textarea
            ref={reasonRef}
            id={ids.reason}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={2}
            maxLength={MAX_REASON_LENGTH}
            aria-invalid={showReasonError ? true : undefined}
            aria-describedby={showReasonError ? ids.reasonErr : undefined}
          />
          {showReasonError ? (
            <p id={ids.reasonErr} className="text-xs text-ledger-red">
              {reasonError}
            </p>
          ) : null}
        </div>
      </div>
      {mutation.error ? (
        <p role="alert" className="text-sm text-ledger-red">
          {mutation.error.messageForUser}
        </p>
      ) : null}
      <div className="flex flex-wrap gap-2">
        <Button
          type="submit"
          variant={action === 'APPROVED' ? 'default' : 'outline'}
          disabled={mutation.isPending}
          className={action === 'REJECTED' ? 'border-ledger-red/50 text-ledger-red' : undefined}
        >
          {mutation.isPending ? 'Saving…' : COPY[action].confirm}
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel} disabled={mutation.isPending}>
          Cancel
        </Button>
      </div>
    </form>
  )
}

function Note({ tone, children }: { tone: 'green' | 'red' | 'muted'; children: ReactNode }) {
  const Icon = tone === 'green' ? CircleCheck : tone === 'red' ? OctagonX : Info
  return (
    <p className="flex items-start gap-2 text-sm">
      <Icon
        aria-hidden
        className={cn(
          'mt-0.5 size-4 shrink-0',
          tone === 'green' && 'text-ledger-green',
          tone === 'red' && 'text-ledger-red',
          tone === 'muted' && 'text-ink-muted',
        )}
      />
      <span className="min-w-0 [overflow-wrap:anywhere]">{children}</span>
    </p>
  )
}

export interface DecisionPanelProps {
  runId: string
  entry: EntryView
  /** Controlled open form (lets pages bind the `a` / `r` shortcuts). */
  formAction?: HumanAction | null
  onFormActionChange?: (action: HumanAction | null) => void
  className?: string
}

/**
 * The action bar under an entry. Only QUARANTINED entries without a human decision can be
 * decided; everything else explains why not. No optimistic update: the new state appears
 * when the server confirms it.
 */
export function DecisionPanel({
  runId,
  entry,
  formAction,
  onFormActionChange,
  className,
}: DecisionPanelProps) {
  const [localAction, setLocalAction] = useState<HumanAction | null>(null)
  const action = formAction !== undefined ? formAction : localAction
  const setAction = (a: HumanAction | null) => {
    if (onFormActionChange) onFormActionChange(a)
    else setLocalAction(a)
  }
  const human = entry.human_decision
  const jeId = entry.entry.id

  let body: ReactNode
  if (human) {
    body = (
      <Note tone={human.action === 'APPROVED' ? 'green' : 'red'}>
        {human.action === 'APPROVED' ? 'Approved and posted' : 'Rejected'} by{' '}
        <span className="font-medium">{human.actor}</span> on{' '}
        <span className="font-mono">{formatTimestamp(human.ts)}</span>. Reason: “{human.reason}”.
        Decisions are final; resubmit a new version to change it.
      </Note>
    )
  } else if (entry.decision === 'REJECTED') {
    body = (
      <Note tone="red">
        Rejected entries can't be approved. Edit the entry and resubmit as a new version.
      </Note>
    )
  } else if (entry.decision === 'ACCEPTED') {
    body = <Note tone="green">Posted automatically — all checks passed.</Note>
  } else if (action) {
    body = (
      <DecisionForm
        runId={runId}
        jeId={jeId}
        action={action}
        onCancel={() => setAction(null)}
        onDone={() => setAction(null)}
      />
    )
  } else {
    body = (
      <div className="flex flex-wrap items-center gap-2">
        <Button onClick={() => setAction('APPROVED')} aria-keyshortcuts="a">
          Approve and post
        </Button>
        <Button variant="outline" onClick={() => setAction('REJECTED')} aria-keyshortcuts="r">
          Reject
        </Button>
        <span className="text-sm text-ink-muted">Needs a reviewer's decision.</span>
      </div>
    )
  }

  return (
    <div
      role="group"
      aria-label={`Decision for ${jeId}`}
      className={cn('border-t border-rule pt-3', className)}
    >
      {body}
    </div>
  )
}
