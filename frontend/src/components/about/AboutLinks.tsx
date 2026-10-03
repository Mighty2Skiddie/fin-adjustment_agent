import { ExternalLink } from 'lucide-react'

function langfuseUrl(): string | null {
  const raw: unknown = import.meta.env.VITE_LANGFUSE_TRACE_URL
  if (typeof raw !== 'string' || raw.trim() === '') return null
  try {
    const url = new URL(raw.trim())
    return url.protocol === 'https:' || url.protocol === 'http:' ? url.toString() : null
  } catch {
    return null
  }
}

const SECTIONS = [
  { href: '#architecture', label: 'Architecture' },
  { href: '#clarifying-questions', label: 'Clarifying questions' },
  { href: '#assumptions', label: 'Assumptions' },
]

/** Where to find the code and the evidence, plus in-page navigation. */
export function AboutLinks() {
  const trace = langfuseUrl()
  return (
    <div className="flex flex-col gap-4">
      <dl className="grid max-w-3xl grid-cols-1 gap-x-6 gap-y-2 text-sm sm:grid-cols-[max-content_minmax(0,1fr)]">
        <dt className="text-ink-muted">Repository</dt>
        <dd className="text-ink">
          Start with <code className="font-mono">README.md</code> at the repository root; specs and deliverables are in{' '}
          <code className="font-mono">docs/</code> (architecture, assumptions, clarifying questions).
        </dd>
        {trace ? (
          <>
            <dt className="text-ink-muted">Langfuse trace</dt>
            <dd>
              <a
                href={trace}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-act underline underline-offset-2"
              >
                Open the public trace of a pipeline run
                <ExternalLink className="size-3.5" aria-hidden />
                <span className="sr-only">(opens in a new tab)</span>
              </a>
            </dd>
          </>
        ) : null}
        <dt className="text-ink-muted">Local traces</dt>
        <dd className="text-ink">
          Every run writes a JSONL trace under <code className="font-mono">output/traces/</code>; each entry&apos;s
          timeline is on its entry page.
        </dd>
      </dl>
      <nav aria-label="On this page">
        <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
          {SECTIONS.map((s) => (
            <li key={s.href}>
              <a href={s.href} className="text-act underline underline-offset-2">
                {s.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  )
}
