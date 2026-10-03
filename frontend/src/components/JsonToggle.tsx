import { Check, ChevronRight, Copy } from 'lucide-react'
import { useId, useState } from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export interface JsonToggleProps {
  data: unknown
  /** What the JSON is, used in the button text: "Show {label}". Default "raw JSON". */
  label?: string
  defaultOpen?: boolean
  /** Max height of the code block before it scrolls. */
  maxHeight?: string
  className?: string
}

/** Disclosure for the raw server payload, with a copy button. */
export function JsonToggle({
  data,
  label = 'raw JSON',
  defaultOpen = false,
  maxHeight = '24rem',
  className,
}: JsonToggleProps) {
  const [open, setOpen] = useState(defaultOpen)
  const [copied, setCopied] = useState(false)
  const id = useId()
  const text = open ? JSON.stringify(data, null, 2) : ''

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(data, null, 2))
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1500)
    } catch {
      setCopied(false)
    }
  }

  return (
    <div className={cn('flex flex-col gap-2', className)}>
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          aria-expanded={open}
          aria-controls={id}
          onClick={() => setOpen((o) => !o)}
          className="-ml-2 text-ink-muted hover:text-ink"
        >
          <ChevronRight
            aria-hidden
            className={cn('transition-transform duration-150', open && 'rotate-90')}
          />
          {open ? `Hide ${label}` : `Show ${label}`}
        </Button>
        {open ? (
          <Button variant="ghost" size="sm" onClick={() => void copy()} className="text-ink-muted">
            {copied ? <Check aria-hidden /> : <Copy aria-hidden />}
            {copied ? 'Copied' : 'Copy'}
          </Button>
        ) : null}
      </div>
      {open ? (
        <pre
          id={id}
          tabIndex={0}
          className="overflow-auto rounded-sm border border-rule bg-band p-3 text-xs leading-relaxed"
          style={{ maxHeight }}
        >
          {text}
        </pre>
      ) : null}
    </div>
  )
}
