# Shared components (for page authors)

Import from `@/components` (barrel). Data comes from `@/api/queries`; types from `@/api/types`.
**Money is always a string**: render it with `<Money>` / `formatMoney`, sort with `sortBy.decimal`,
compare with `compareDecimal`. Never use `Number()` / `parseFloat` on amounts.

## Page skeleton

```tsx
import { useEntries } from '@/api/queries'
import { PageHeader, RunGate, ErrorState, DataTable } from '@/components'

export default function QueuePage() {
  return (
    <>
      <PageHeader title="Review queue" description="…" />
      <RunGate>{(runId) => <QueueContent runId={runId} />}</RunGate>
    </>
  )
}
```
`RunGate` resolves `:runId` ("latest" → concrete id) and renders loading / error / "run not
found" (with a link to the latest run). Inside, `runId` is always concrete. `AppShell` already
renders the rail, `RunTopBar` and `<main>`; pages render only their content.

## Data hooks (`@/api/queries`)

`useRunId()` → `{ runId, routeRunId, isLoading, notFound, latestRunId, error, refetch }`.
`useRuns()`, `useRun(runId)` (Manifest + metrics), `useHealth(runId)`, `useEntries(runId)`,
`useEntry(runId, jeId)` (adds `human_decisions`, `lineage_preview`), `usePostedTb(runId)`,
`useLineage(runId, account)` (disabled while `account` is null), `useTrace(runId, jeId)`,
`useAuditLog(runId)`, `useEvals(runId)` (404 `error.code === 'evals_missing'` → empty state),
`useArchitectureDoc()` (markdown string), `useDecision(runId)` mutation
(`mutate({ jeId, action: 'APPROVED'|'REJECTED', actor, reason })`; no optimistic update;
invalidates entries, entry, posted-tb, lineage, audit-log, trace). Errors are `ApiError`
(`status`, `code`, `messageForUser`, `detail`). Trace events: narrow with
`isTraceEvent(e, 'llm.call')` from `@/api/types`.

## Components

| Component | Props | Notes |
|---|---|---|
| `AppShell` | — | Layout route (already wired in `App.tsx`). |
| `RunTopBar` | `className?` | Run id, period, FX policy, LLM mode, counts. Already in `AppShell`. |
| `RunGate` | `children: (runId) => ReactNode` | Loading / error / not-found handling. |
| `PageHeader` | `title`, `description?`, `actions?`, `children?` | h1 at 24 px. |
| `SectionHeading` | `children`, `id?`, `aside?` | h2 at 18 px. |
| `DataTable<T>` | `columns: Column<T>[]`, `rows`, `getRowId`, `caption`, `showCaption?`, `loading?`, `skeletonRows?`, `empty?`, `initialSort?`, `onRowClick?`, `rowActionLabel?`, `selectedRowId?`, `rowClassName?`, `renderAfterRow?`, `maxHeight?`, `footer?` | 36 px rows, sticky header, stable sort, `aria-sort`. `Column`: `{ id, header, cell(row,i), sort?, align?, width?, rowHeader?, className?, headerClassName? }`. `renderAfterRow` returns a full-width row (use it for the queue's in-place expansion). Rows with `onRowClick` are focusable; Enter/Space activate; each `<tr>` has `data-row-id`. |
| `sortBy` | `.string(get)`, `.decimal(get)`, `.number(get)` | Comparator builders for `Column.sort`. |
| `Money` | `value`, `signed?`, `tone?: 'auto'\|'none'`, `dimZero?` | Mono, tabular, 2 dp, leading minus, red when negative. Right-align the cell. |
| `AccountCode` | `code`, `name?`, `orphan?`, `unmapped?` | Mono code; red + "not in COA" for orphans; "unmapped" tag. |
| `SeverityChip` | `severity` | Rule (BLOCK/ESCALATE/WARN/INFO), health (CRITICAL/HIGH/MEDIUM/LOW/INFO) and PASS. |
| `DecisionChip` | `decision` | ACCEPTED / QUARANTINED / REJECTED with icon. |
| `AssumptionChip` | `id` | Amber chip; tooltip shows the text from `lib/assumptions.ts`; links to `/about#assumption-<id>`. |
| `Chip` | `tone`, `variant: 'fill'\|'outline'`, `icon?`, `title?` | Base chip (green/red/amber/neutral/act/muted). |
| `EvidenceTable` | `evidence`, `caption?` | Key/value; exact values in mono; nested objects/lists as nested tables. |
| `JsonToggle` | `data`, `label?`, `defaultOpen?`, `maxHeight?` | "Show raw JSON" disclosure + copy. |
| `EmptyState` | `title`, `description?`, `action?`, `icon?` | Dashed box, plain copy. |
| `ErrorState` | `error`, `onRetry?`, `title?`, `action?` | Shows `messageForUser`, code + HTTP status, Retry. `role="alert"`. |
| `SkeletonRows` | `rows?`, `columns?`, `label?` | Static table placeholder (no spinners, no pulse). Also `SkeletonTableRows` (inside tbody) and `SkeletonLines`. |
| `StatStrip` | `stats: { label, value, note?, tone? }[]`, `loading?` | Headline numbers with labels beneath (`<dl>`). |
| `InvariantList` | `invariants: Record<string, boolean>` | Green/red ticks with readable labels. |
| `KeyboardHints` | `hints: { keys: string[], label }[]` | Also `Kbd`. Bind keys with `useHotkeys` (`@/hooks/useHotkeys`). |

### Entry content (Review Queue expansion and Entry detail share these)

| Component | Props | Notes |
|---|---|---|
| `EntryPanel` | `runId`, `entry: EntryView`, `llmMode?`, `traceHref?`, `formAction?`, `onFormActionChange?` | Lines, findings, explanation and fix candidates (4 columns at xl, stacked on narrow screens), then impact and the action bar. Pass `formAction`/`onFormActionChange` to bind the `a`/`r` keys (only when `canDecide(entry)`). |
| `EntryLines` | `result` | Orphan codes in red with "not in COA", same account on both sides highlighted. |
| `FindingList` | `findings` | Most severe first; "reviewer" badge on LLM findings; evidence toggle. |
| `ExplanationCard` | `result`, `llmMode?`, `traceHref?` | 18 px summary, bullets, next step, source chip (`LLM · model · mode` / `template fallback`). |
| `FixCandidates` | `candidates`, `needsHumanInput?` | Cards with Resolves / Does not resolve, "Copy as JSON", question shown as a quote. |
| `ImpactPreview` | `impact` | Touched accounts by depth with Δ, plus NI/A/L/E deltas. |
| `DecisionPanel` | `runId`, `entry`, `formAction?`, `onFormActionChange?` | Approve / reject for QUARANTINED; explanations for the other states; shows the final human decision. |
| `DecisionForm` | `runId`, `jeId`, `action`, `onCancel`, `onDone?` | Name (stored in localStorage `finagent.reviewer`), reason ≥ 10 chars, inline validation, server error inline, toast on success. |

## Helpers

- `@/lib/money`: `formatMoney(s, { signed?, places? })`, `isNegative`, `isZero`, `compareDecimal`, `formatPct("0.2432") → "24.3%"`, `formatCount`, `formatMs`.
- `@/lib/format`: `fxPolicyLabel`, `llmModeLabel`, `humanize`, `formatTimestamp` (UTC), `formatDate`, `effectiveStateLabel`, `isLlmFinding`, `parseExplanation`.
- `@/lib/status`: `SEVERITY_RANK`, `severityRank`, `DECISION_ORDER` (quarantined → rejected → accepted), `decisionLabel`, `invariantLabel`.
- `@/lib/entry`: `canDecide`, `orphanAccounts`, `bothSidesAccounts`, `accountNames`.
- `@/lib/assumptions`: `ASSUMPTIONS` (id → text), `assumptionText`, `assumptionAnchor(id)` → `"assumption-A3"` (the anchor ids used by the register on the About page).
- `@/hooks/useHotkeys(map, enabled)`: single-key shortcuts that are ignored while the user is typing. `@/hooks/useLocalStorage`. `@/hooks/useSamePageOnRun(target)`.

## Tokens (Tailwind utilities)

`bg-paper text-ink text-ink-muted border-rule bg-surface bg-band`,
`text-ledger-green|red|amber-ink`, `bg-ledger-*-tint`, `bg-act text-act-ink bg-act-tint`.
Use `text-ledger-amber-ink` for amber **text** (the spec amber is only 3.4:1 on paper). Type
scale: `text-sm`/`text-xs` = 13, `text-base` = 15, `text-lg` = 18, `text-2xl` = 24,
`text-3xl` = 32. `.num` / `font-mono` = Plex Mono with tabular figures. Toasts: `toast` from
`sonner` (Toaster is mounted). shadcn/ui components in `components/ui`: button, input, textarea, label, skeleton, tooltip,
sheet (the lineage drawer), toggle, toggle-group, sonner.
