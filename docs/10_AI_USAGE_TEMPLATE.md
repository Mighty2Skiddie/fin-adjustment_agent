# 10 — AI tool usage log (fill as you build; becomes `docs/AI_USAGE.md`)

The brief scores "AI tool fluency: uses AI to move faster without offloading judgment".
Log facts, not marketing. One line per event. Three columns matter: what the tool did,
whether it was right, what I did about it.

## Tools used

| Tool | Role in this project |
|---|---|
| Claude (chat) | Data audit, decomposition, spec kit, architecture draft |
| Claude Code | Implementation from the spec, tests, frontend |
| (Cursor / Copilot if used) | … |
| Gemini / Groq free tier (if used) | Recording LLM cassettes for the three roles |

## Log

| Phase | What the AI did | Right? | What I did |
|---|---|---|---|
| Planning | Audited the raw data and found defects beyond the listed ones (JE-003 double-count, unbalanced prior TB, 8000/3300 headers) | Yes | Verified each number with Decimal in a REPL before trusting it |
| Planning | Suggested the P&L+BS slice because it "demos better" | No — would require 3 slices | Chose the adjustments slice; documented why |
| 1 | … | | |
| 2 | … | | |
| 3 | … | | |
| 6 | … | | |
| 7 | … | | |

## Patterns observed

*(Write 3–5 bullets at the end. Examples of the kind of thing to note:)*
- Tends to reach for `float` and `pandas` arithmetic unless told otherwise.
- Resolves ambiguity by picking the option that makes the code simpler, not the one that
  is accounting-correct — every policy decision needed a human.
- Excellent at mirroring a precise spec into tests; weak at noticing when the spec itself
  had an arithmetic slip.
- Prompt it with ground truth and it is fast; prompt it with intent and it is confident.

## Where AI led me wrong (be specific — this is what they want to read)

- …
