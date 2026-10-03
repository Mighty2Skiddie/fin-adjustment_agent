import { useArchitectureDoc } from '@/api/queries'
import { ErrorState, PageHeader, SectionHeading, SkeletonLines } from '@/components'
import {
  AboutLinks,
  AssumptionsRegister,
  ClarifyingQuestions,
  MarkdownDoc,
  useHashScroll,
} from '@/components/about'

function ArchitectureDoc() {
  const doc = useArchitectureDoc()
  if (doc.isPending) return <SkeletonLines lines={12} />
  if (doc.isError) {
    return (
      <ErrorState
        error={doc.error}
        onRetry={() => void doc.refetch()}
        title="Couldn't load the architecture document"
      />
    )
  }
  return <MarkdownDoc markdown={doc.data} />
}

export default function AboutPage() {
  const doc = useArchitectureDoc()
  // Re-scroll once the document has rendered: anchors below it move when it arrives.
  const anchor = useHashScroll(doc.isSuccess)

  return (
    <>
      <PageHeader
        title="About this prototype"
        description="How the adjustments agent is built, what we asked before building it, and every assumption it runs on."
      />
      <div className="flex flex-col gap-10">
        <AboutLinks />

        <section id="architecture" aria-label="Architecture" className="scroll-mt-24">
          <ArchitectureDoc />
        </section>

        <section id="clarifying-questions" aria-labelledby="clarifying-heading" className="scroll-mt-24">
          <SectionHeading id="clarifying-heading" aside="from docs/07_CLARIFYING_QUESTIONS.md">
            The three clarifying questions
          </SectionHeading>
          <p className="max-w-[75ch] pb-3 text-sm text-ink-muted">
            Sent before the build. Each states the fallback the system uses until finance answers, so nothing was
            blocked and every guess is visible.
          </p>
          <ClarifyingQuestions activeAnchor={anchor} />
        </section>

        <section id="assumptions" aria-labelledby="assumptions-heading" className="scroll-mt-24">
          <SectionHeading id="assumptions-heading">Assumptions</SectionHeading>
          <AssumptionsRegister activeAnchor={anchor} />
        </section>
      </div>
    </>
  )
}
