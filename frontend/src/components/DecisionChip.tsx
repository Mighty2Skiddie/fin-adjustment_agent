import { CircleCheck, CirclePause, OctagonX } from 'lucide-react'
import type { ReactNode } from 'react'
import type { Decision } from '@/api/types'
import { Chip, type ChipTone } from './Chip'

const STYLE: Record<Decision, { tone: ChipTone; label: string; icon: ReactNode }> = {
  ACCEPTED: { tone: 'green', label: 'Accepted', icon: <CircleCheck aria-hidden /> },
  QUARANTINED: { tone: 'amber', label: 'Quarantined', icon: <CirclePause aria-hidden /> },
  REJECTED: { tone: 'red', label: 'Rejected', icon: <OctagonX aria-hidden /> },
}

export function DecisionChip({ decision, className }: { decision: Decision; className?: string }) {
  const style = STYLE[decision] ?? { tone: 'neutral' as const, label: decision, icon: null }
  return (
    <Chip tone={style.tone} icon={style.icon} className={className}>
      {style.label}
    </Chip>
  )
}
