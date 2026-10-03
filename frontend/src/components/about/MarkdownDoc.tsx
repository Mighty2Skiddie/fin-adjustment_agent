import { Children, isValidElement, type ReactNode } from 'react'
import ReactMarkdown, { type Components } from 'react-markdown'
import { cn } from '@/lib/utils'
import { splitBlocks, type Align, type TableBlock } from './markdownBlocks'

function textOf(node: ReactNode): string {
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(textOf).join('')
  if (isValidElement<{ children?: ReactNode }>(node)) return textOf(node.props.children)
  return Children.toArray(node).map(textOf).join('')
}

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

/** Inline elements, shared by prose and table cells. Headings shift down one level under the page h1. */
const INLINE: Components = {
  a: ({ href, children }) => (
    <a href={href} className="text-act underline underline-offset-2">
      {children}
    </a>
  ),
  code: ({ children, className }) => (
    <code className={cn('rounded-sm bg-band px-1 py-px font-mono text-[13px] text-ink', className)}>{children}</code>
  ),
  strong: ({ children }) => <strong className="font-semibold text-ink">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
}

/* Box-drawing diagrams need a mono font that ships U+2500 glyphs; IBM Plex Mono does not,
   so code blocks use the system mono stack to keep columns aligned. */
const BLOCK: Components = {
  ...INLINE,
  h1: ({ children }) => (
    <h2 id={`doc-${slugify(textOf(children))}`} className="scroll-mt-24 pt-2 text-2xl font-semibold tracking-tight text-ink">
      {children}
    </h2>
  ),
  h2: ({ children }) => (
    <h3
      id={`doc-${slugify(textOf(children))}`}
      className="mt-6 scroll-mt-24 border-t border-rule pt-5 text-lg font-semibold text-ink"
    >
      {children}
    </h3>
  ),
  h3: ({ children }) => <h4 className="mt-4 text-base font-semibold text-ink">{children}</h4>,
  h4: ({ children }) => <h5 className="mt-3 text-base font-medium text-ink">{children}</h5>,
  p: ({ children }) => <p className="max-w-[75ch] leading-relaxed text-ink">{children}</p>,
  ul: ({ children }) => <ul className="flex max-w-[75ch] list-disc flex-col gap-1.5 pl-5 leading-relaxed">{children}</ul>,
  ol: ({ children }) => (
    <ol className="flex max-w-[75ch] list-decimal flex-col gap-1.5 pl-5 leading-relaxed">{children}</ol>
  ),
  li: ({ children }) => <li className="pl-1 marker:text-ink-muted">{children}</li>,
  blockquote: ({ children }) => (
    <blockquote className="max-w-[75ch] border-l-2 border-rule pl-4 text-ink-muted">{children}</blockquote>
  ),
  hr: () => <hr className="border-rule" />,
  pre: ({ children }) => (
    <pre
      tabIndex={0}
      className="overflow-x-auto rounded-sm border border-rule bg-surface p-4 font-[ui-monospace,'Cascadia_Mono','Cascadia_Code',Consolas,'SF_Mono',Menlo,'DejaVu_Sans_Mono',monospace] text-[13px] leading-[1.35] whitespace-pre text-ink [&>code]:bg-transparent [&>code]:p-0 [&>code]:font-[inherit]"
    >
      {children}
    </pre>
  ),
}

const CELL: Components = { ...INLINE, p: ({ children }) => <>{children}</> }

const ALIGN: Record<Exclude<Align, null>, string> = {
  left: 'text-left',
  right: 'text-right',
  center: 'text-center',
}

/** Cells are inline-only: escape a leading block marker so "#" or "-" stays literal text. */
function Cell({ text }: { text: string }) {
  return <ReactMarkdown components={CELL}>{text.replace(/^([#>+-]|\d+[.)]|\*\s)/, '\\$1')}</ReactMarkdown>
}

function MdTable({ table }: { table: TableBlock }) {
  return (
    <div className="relative overflow-x-auto rounded-sm border border-rule bg-surface">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr>
            {table.header.map((h, i) => (
              <th
                key={i}
                scope="col"
                className={cn(
                  'border-b border-rule bg-band px-3 py-2 align-bottom font-medium text-ink-muted',
                  ALIGN[table.align[i] ?? 'left'],
                )}
              >
                <Cell text={h} />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row, r) => (
            <tr key={r} className="border-b border-rule last:border-b-0">
              {table.header.map((_, c) => (
                <td key={c} className={cn('px-3 py-2 align-top leading-snug', ALIGN[table.align[c] ?? 'left'])}>
                  <Cell text={row[c] ?? ''} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** Renders a trusted markdown document (ARCHITECTURE.md) with the page's typographic styles. */
export function MarkdownDoc({ markdown, className }: { markdown: string; className?: string }) {
  const blocks = splitBlocks(markdown)
  return (
    <div className={cn('flex flex-col gap-4 text-base', className)}>
      {blocks.map((b, i) =>
        b.type === 'table' ? (
          <MdTable key={i} table={b} />
        ) : (
          <div key={i} className="flex flex-col gap-4">
            <ReactMarkdown components={BLOCK}>{b.text}</ReactMarkdown>
          </div>
        ),
      )}
    </div>
  )
}
