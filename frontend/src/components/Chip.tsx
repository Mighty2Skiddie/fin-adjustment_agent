import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

export type ChipTone = 'green' | 'red' | 'amber' | 'neutral' | 'act' | 'muted'

const TONES: Record<ChipTone, { fill: string; outline: string }> = {
  green: {
    fill: 'bg-ledger-green-tint text-ledger-green border-ledger-green/40',
    outline: 'text-ledger-green border-ledger-green/50',
  },
  red: {
    fill: 'bg-ledger-red-tint text-ledger-red border-ledger-red/40',
    outline: 'text-ledger-red border-ledger-red/50',
  },
  amber: {
    fill: 'bg-ledger-amber-tint text-ledger-amber-ink border-ledger-amber/50',
    outline: 'text-ledger-amber-ink border-ledger-amber/60',
  },
  neutral: { fill: 'bg-band text-ink border-rule', outline: 'text-ink border-rule' },
  act: { fill: 'bg-act-tint text-act border-act/40', outline: 'text-act border-act/50' },
  muted: { fill: 'bg-band text-ink-muted border-rule', outline: 'text-ink-muted border-rule' },
}

export interface ChipProps {
  tone?: ChipTone
  variant?: 'fill' | 'outline'
  icon?: ReactNode
  children: ReactNode
  className?: string
  title?: string
}

/** Small status label. Colour is never the only signal: pass an icon or a word. */
export function Chip({
  tone = 'neutral',
  variant = 'fill',
  icon,
  children,
  className,
  title,
}: ChipProps) {
  return (
    <span
      title={title}
      className={cn(
        'inline-flex h-5 shrink-0 items-center gap-1 rounded-sm border px-1.5 text-xs leading-none font-medium whitespace-nowrap',
        '[&>svg]:size-3 [&>svg]:shrink-0',
        TONES[tone][variant],
        className,
      )}
    >
      {icon}
      {children}
    </span>
  )
}
