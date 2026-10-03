import type { ReactNode } from 'react'
import type { Manifest } from '@/api/types'
import { Chip, InvariantList, SectionHeading, SkeletonLines } from '@/components'
import { formatTimestamp, fxPolicyLabel, llmModeLabel } from '@/lib/format'

function Row({ term, children }: { term: string; children: ReactNode }) {
  return (
    <div className="grid grid-cols-1 gap-0.5 border-b border-rule py-2 last:border-b-0 sm:grid-cols-[10rem_minmax(0,1fr)] sm:gap-4">
      <dt className="text-sm text-ink-muted">{term}</dt>
      <dd className="min-w-0 text-sm text-ink">{children}</dd>
    </div>
  )
}

function StatusChip({ status }: { status: string }) {
  if (status === 'OK') return <Chip tone="green">OK</Chip>
  return <Chip tone="red">{status}</Chip>
}

/** What produced this run: code, inputs, config. Enough to reproduce it byte for byte. */
export function ManifestPanel({ manifest }: { manifest: Manifest | undefined }) {
  return (
    <section aria-labelledby="manifest-heading" className="flex flex-col">
      <SectionHeading id="manifest-heading">Run manifest</SectionHeading>
      <div className="grid grid-cols-1 gap-6 rounded-sm border border-rule bg-surface p-4 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        {!manifest ? (
          <>
            <SkeletonLines lines={8} />
            <SkeletonLines lines={6} />
          </>
        ) : (
          <>
            <dl className="min-w-0">
              <Row term="Run id">
                <span className="font-mono">{manifest.run_id}</span>
              </Row>
              <Row term="Created">
                <span className="num">{formatTimestamp(manifest.created_at)}</span>
              </Row>
              {manifest.period ? (
                <Row term="Period">
                  <span className="num">{manifest.period}</span>
                </Row>
              ) : null}
              <Row term="Code version">
                <span className="font-mono">{manifest.code_version}</span>
              </Row>
              <Row term="Config hash">
                <span className="font-mono break-all">{manifest.config_hash}</span>
              </Row>
              <Row term="LLM mode">
                {llmModeLabel(manifest.llm_mode)}{' '}
                <span className="font-mono text-xs text-ink-muted">{manifest.llm_mode}</span>
              </Row>
              <Row term="FX policy">
                {fxPolicyLabel(manifest.fx_policy)}{' '}
                {manifest.fx_policy ? (
                  <span className="font-mono text-xs text-ink-muted">{manifest.fx_policy}</span>
                ) : null}
              </Row>
              <Row term="Status">
                <StatusChip status={manifest.status} />
              </Row>
              <Row term="Input hashes">
                <ul className="flex flex-col gap-1.5">
                  {Object.entries(manifest.input_hashes).map(([file, hash]) => (
                    <li key={file} className="flex flex-col">
                      <span className="font-mono text-ink">{file}</span>
                      <span className="font-mono text-xs break-all text-ink-muted">
                        <span className="sr-only">sha256 </span>
                        {hash}
                      </span>
                    </li>
                  ))}
                </ul>
              </Row>
            </dl>
            <div className="min-w-0">
              <h3 className="pb-2 text-sm font-medium text-ink">Invariants</h3>
              {Object.keys(manifest.invariants).length ? (
                <InvariantList invariants={manifest.invariants} />
              ) : (
                <p className="text-sm text-ink-muted">This run recorded no invariants.</p>
              )}
            </div>
          </>
        )}
      </div>
    </section>
  )
}
