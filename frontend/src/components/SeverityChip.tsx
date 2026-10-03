import { CircleAlert, CircleCheck, Info, OctagonX, TriangleAlert } from 'lucide-react'
import type { ReactNode } from 'react'
import type { AnySeverity } from '@/lib/status'
import { Chip, type ChipTone } from './Chip'

interface SeverityStyle {
  tone: ChipTone
  variant: 'fill' | 'outline'
  label: string
  icon: ReactNode
}

const STYLE: Record<AnySeverity, SeverityStyle> = {
  BLOCK: { tone: 'red', variant: 'fill', label: 'Block', icon: <OctagonX aria-hidden /> },
  ESCALATE: {
    tone: 'amber',
    variant: 'fill',
    label: 'Escalate',
    icon: <TriangleAlert aria-hidden />,
  },
  WARN: { tone: 'amber', variant: 'outline', label: 'Warn', icon: <CircleAlert aria-hidden /> },
  INFO: { tone: 'muted', variant: 'outline', label: 'Info', icon: <Info aria-hidden /> },
  CRITICAL: { tone: 'red', variant: 'fill', label: 'Critical', icon: <OctagonX aria-hidden /> },
  HIGH: { tone: 'red', variant: 'outline', label: 'High', icon: <TriangleAlert aria-hidden /> },
  MEDIUM: {
    tone: 'amber',
    variant: 'outline',
    label: 'Medium',
    icon: <CircleAlert aria-hidden />,
  },
  LOW: { tone: 'neutral', variant: 'outline', label: 'Low', icon: <Info aria-hidden /> },
  PASS: { tone: 'green', variant: 'outline', label: 'Pass', icon: <CircleCheck aria-hidden /> },
}

export function SeverityChip({
  severity,
  className,
}: {
  severity: AnySeverity | (string & {})
  className?: string
}) {
  const style: SeverityStyle = STYLE[severity as AnySeverity] ?? {
    tone: 'neutral',
    variant: 'outline',
    label: severity,
    icon: null,
  }
  return (
    <Chip
      tone={style.tone}
      variant={style.variant}
      icon={style.icon}
      className={className}
      title={`Severity: ${severity}`}
    >
      {style.label}
    </Chip>
  )
}
