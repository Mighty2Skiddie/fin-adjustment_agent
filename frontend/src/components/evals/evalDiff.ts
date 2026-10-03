import type { EvalEntry } from '@/api/types'

/** Rule ids compared as multisets: order does not matter, repeats do (R009 twice on JE-004). */
export function sameRuleIds(a: readonly string[], b: readonly string[]): boolean {
  if (a.length !== b.length) return false
  const x = [...a].sort()
  const y = [...b].sort()
  return x.every((v, i) => v === y[i])
}

/**
 * LLM findings pass when every required one is present and anything extra is in the
 * allowed list (see D27 in docs/08_ASSUMPTIONS.md).
 */
export function llmRulesOk(e: EvalEntry): boolean {
  const actual = new Set(e.actual_llm_rule_ids)
  const allowed = new Set([...e.expected_llm_rule_ids, ...e.llm_extra_allowed])
  return (
    e.expected_llm_rule_ids.every((id) => actual.has(id)) &&
    e.actual_llm_rule_ids.every((id) => allowed.has(id))
  )
}

export interface EntryDiff {
  decision: boolean
  rules: boolean
  llm: boolean
}

/** Which cells of a case differ from the expectation (true = differs). */
export function entryDiff(e: EvalEntry): EntryDiff {
  return {
    decision: e.expected_decision !== e.actual_decision,
    rules: !sameRuleIds(e.expected_rule_ids, e.actual_rule_ids),
    llm: !llmRulesOk(e),
  }
}
