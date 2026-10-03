/**
 * Splits markdown into prose and pipe-table blocks. react-markdown only speaks CommonMark and
 * remark-gfm is not a dependency, so GFM tables are parsed here and rendered as real <table>s.
 * Fenced code blocks are passed through untouched (the topology diagram contains "│").
 */

export type Align = 'left' | 'right' | 'center' | null

export interface TableBlock {
  type: 'table'
  header: string[]
  align: Align[]
  rows: string[][]
}

export interface MarkdownBlock {
  type: 'markdown'
  text: string
}

export type Block = TableBlock | MarkdownBlock

const SEPARATOR = /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$/

/** Split a table row on unescaped pipes, dropping the outer empty cells. */
export function splitRow(line: string): string[] {
  const cells: string[] = []
  let current = ''
  let inCode = false
  for (let i = 0; i < line.length; i++) {
    const ch = line[i]
    if (ch === '\\' && line[i + 1] === '|') {
      current += '|'
      i++
      continue
    }
    if (ch === '`') inCode = !inCode
    if (ch === '|' && !inCode) {
      cells.push(current)
      current = ''
      continue
    }
    current += ch
  }
  cells.push(current)
  const trimmed = line.trim()
  if (trimmed.startsWith('|')) cells.shift()
  if (trimmed.endsWith('|') && !trimmed.endsWith('\\|')) cells.pop()
  return cells.map((c) => c.trim())
}

function alignOf(cell: string): Align {
  const left = cell.startsWith(':')
  const right = cell.endsWith(':')
  if (left && right) return 'center'
  if (right) return 'right'
  if (left) return 'left'
  return null
}

const isTableLine = (line: string | undefined) => line != null && line.trim().startsWith('|')

export function splitBlocks(markdown: string): Block[] {
  const lines = markdown.replace(/\r\n?/g, '\n').split('\n')
  const blocks: Block[] = []
  let prose: string[] = []
  let fence: string | null = null

  const flush = () => {
    if (prose.join('').trim()) blocks.push({ type: 'markdown', text: prose.join('\n') })
    prose = []
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i] ?? ''
    const fenceMatch = /^\s*(```|~~~)/.exec(line)
    if (fenceMatch) {
      const marker = fenceMatch[1] ?? '```'
      if (fence == null) fence = marker
      else if (marker === fence) fence = null
      prose.push(line)
      continue
    }
    if (fence == null && isTableLine(line) && SEPARATOR.test(lines[i + 1] ?? '')) {
      flush()
      const header = splitRow(line)
      const align = splitRow(lines[i + 1] ?? '').map(alignOf)
      const rows: string[][] = []
      i += 2
      while (isTableLine(lines[i])) {
        rows.push(splitRow(lines[i] ?? ''))
        i++
      }
      i--
      blocks.push({ type: 'table', header, align, rows })
      continue
    }
    prose.push(line)
  }
  flush()
  return blocks
}
