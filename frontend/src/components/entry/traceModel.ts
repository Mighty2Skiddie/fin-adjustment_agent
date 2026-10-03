/** Shapes the flat trace into a timeline: node enter/exit paired, PASS rule results batched. */
import { isTraceEvent, type RuleResultEvent, type TraceEvent } from '@/api/types'

export interface PassBatch {
  kind: 'passes'
  events: RuleResultEvent[]
}
export interface SingleEvent {
  kind: 'event'
  event: TraceEvent
}
export type NodeChild = PassBatch | SingleEvent

export interface NodeSpan {
  kind: 'node'
  node: string
  iteration: number | undefined
  enter: TraceEvent | null
  exit: TraceEvent | null
  durationMs: number | null
  children: NodeChild[]
}
export type TimelineItem = NodeSpan | SingleEvent

function pushChild(children: NodeChild[], event: TraceEvent) {
  if (isTraceEvent(event, 'rule.result') && event.severity === 'PASS') {
    const last = children[children.length - 1]
    if (last?.kind === 'passes') last.events.push(event)
    else children.push({ kind: 'passes', events: [event] })
    return
  }
  children.push({ kind: 'event', event })
}

/**
 * Events between a node's enter and exit become its children. An exit without an enter still
 * gets a span (so nothing is dropped); an enter without an exit shows "no exit recorded".
 */
export function buildTimeline(events: TraceEvent[]): TimelineItem[] {
  const items: TimelineItem[] = []
  const stack: NodeSpan[] = []
  for (const e of events) {
    if (isTraceEvent(e, 'node.enter')) {
      const span: NodeSpan = {
        kind: 'node',
        node: e.node,
        iteration: e.iteration,
        enter: e,
        exit: null,
        durationMs: null,
        children: [],
      }
      // Graph nodes run sequentially; a nested enter still gets its own top-level span.
      items.push(span)
      stack.push(span)
      continue
    }
    if (isTraceEvent(e, 'node.exit')) {
      let idx = -1
      for (let i = stack.length - 1; i >= 0; i--) {
        const s = stack[i]
        if (s && s.node === e.node && s.iteration === e.iteration) {
          idx = i
          break
        }
      }
      const span = idx >= 0 ? stack[idx] : undefined
      if (span) {
        span.exit = e
        span.durationMs = e.duration_ms
        stack.splice(idx)
      } else {
        items.push({
          kind: 'node',
          node: e.node,
          iteration: e.iteration,
          enter: null,
          exit: e,
          durationMs: e.duration_ms,
          children: [],
        })
      }
      continue
    }
    const open = stack[stack.length - 1]
    if (open) pushChild(open.children, e)
    else items.push({ kind: 'event', event: e })
  }
  return items
}

export interface TraceSummary {
  events: number
  rules: number
  rulesPassed: number
  llmCalls: number
  cassetteHits: number
  guardrailFailures: number
  nodeTimeMs: number
}

export function summarizeTrace(events: TraceEvent[]): TraceSummary {
  const s: TraceSummary = {
    events: events.length,
    rules: 0,
    rulesPassed: 0,
    llmCalls: 0,
    cassetteHits: 0,
    guardrailFailures: 0,
    nodeTimeMs: 0,
  }
  for (const e of events) {
    if (isTraceEvent(e, 'rule.result')) {
      s.rules += 1
      if (e.severity === 'PASS') s.rulesPassed += 1
    } else if (isTraceEvent(e, 'llm.call')) {
      s.llmCalls += 1
      if (e.cassette_hit) s.cassetteHits += 1
    } else if (isTraceEvent(e, 'guardrail.result')) {
      if (!e.passed) s.guardrailFailures += 1
    } else if (isTraceEvent(e, 'node.exit')) {
      s.nodeTimeMs += e.duration_ms
    }
  }
  return s
}

/** One JSON object per line, as the backend writes traces. */
export function toJsonl(events: TraceEvent[]): string {
  return events.map((e) => JSON.stringify(e)).join('\n') + (events.length ? '\n' : '')
}
