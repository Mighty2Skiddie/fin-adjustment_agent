# How I used AI tools

> **Drafted from the build session log. The candidate should review it and add personal notes.**
> Every event below comes from the build session record. Most numbers come from files in
> `output/`, `evals/`, `docs/` and `frontend/dist/`. Two numbers are in no file: the 33% first
> fallback rate and the old 767 kB bundle size. Those come from the session record.
> Nothing here was estimated later.

The brief scores "AI tool fluency: uses AI to move faster without offloading judgment".
This log lists facts: what the tool did, whether it was right, and what I did about it.

## Short summary

I used Claude Code as my coding assistant. It also ran separate AI helpers. Some helpers wrote
parts of the code. Others tried to find mistakes in that code. I made the decisions when the
spec was unclear.

## Tools used

| Tool | What it did in this project |
|---|---|
| Claude (chat) | Looked at the data, split the work, wrote the specs (`docs/01`–`docs/08`) and a first architecture draft |
| Claude Code (Opus 5.5) | Main coding assistant. Wrote the core code. Combined and checked the helpers' work |
| Separate AI helpers (run by Claude Code) | Some wrote code. Some re-checked it. One tried to attack the AI part. One tested the web pages in a browser |
| Gemini (`gemini-2.5-flash`) | The product's main AI model. Used to record the answers of the three AI roles and the AI judge |
| Groq (`openai/gpt-oss-120b`) | The product's backup AI model. Never needed. Every recording in `evals/cassettes/` was answered by Gemini, and the run manifest shows `provider_fallbacks: 0` |

## Who did what

- **Main assistant.** Wrote the parts where a mistake would be silent and costly:
  - money and the account tree (`domain/`),
  - loading data and FX translation (currency conversion),
  - posting and lineage (where each number came from),
  - the pipeline, the AI layer and its safety checks,
  - the workflow graph and the web API.

  It also ran every end-of-step check: tests (`pytest`), code style (`ruff`), type checks
  (`pyright`, strict on `src/`), and the frontend build and lint.
- **20 data health checks.** 4 helpers wrote the checks, one file each. 4 other helpers
  recomputed each check's numbers on their own and tried to break it.
- **Rules R002–R012.** Same setup: 4 helpers wrote, 4 helpers checked. The main assistant wrote
  R001 and the shared rule code.
- **Tests for the AI part.** 2 helpers wrote tests. 1 more helper tried to attack the AI
  boundary (prompts, safety checks, recorded answers).
- **Frontend.** 1 helper built the base (data layer, typed client, layout). 3 helpers built the
  pages. 1 helper tested the pages in a headless browser (a browser with no screen) using
  Playwright. It took the screenshots in `docs/screenshots/`.
- **Me (human).** I decided every spec conflict (the R009 rule, the account count) and the
  model and provider choice. After Phase 1 I asked for no more commits ("build locally and
  test"). So the history has three commits: spec kit, scaffold, Phase 1.

**Final state:** 407 Python tests, all passing. `ruff` and `pyright` clean. Frontend builds.
Lint has 0 errors and 2 warnings, both in generated shadcn files (`button.tsx`, `toggle.tsx`).

## Log of events

| Date | Step | What the AI did | Was it right? | What was done |
|---|---|---|---|---|
| 2026-10-01 | Planning | Recomputed every expected number in the spec (§6, §8) with exact decimals, before any code. Trial balance gap by FX policy: −4,800.00 / −1,242,500.00 / +182,460.20 / +177,100.30. Revaluation: 10,730.20 / 19,809.60 | Yes. All matched the spec exactly | These numbers became the expected values in the tests |
| 2026-10-01 | Planning | Compared spec §4's R009 rule (each line as a % of the account balance) with the expected results in §7 | Found a real spec error. §4 did not give §7's results. JE-001 line 2120: 850,000 / 1,150,000 = 73.9%, a warning, but §7 showed none. JE-007 8200 (31.7%) and JE-010 2140 (25.0%) also got a note (INFO), where §7 showed none | No single rule matched both, so it stopped and asked me. I chose "Option A": measure per account, on the entry's net movement. §7's rule ids were corrected. Decisions did not change (D4) |
| 2026-10-01 | Phase 0 | Created the frontend with `npm create vite` | Partly. Vite gave React 19 (the spec said 18). Its TypeScript settings did not turn on `strict` | Kept React 19, because current shadcn/ui needs it (D1). Turned `strict` on by hand |
| 2026-10-01 | Phase 1 | The data spec said the chart of accounts has "73 rows" | No. The file has 72 accounts (73 lines with the header) | Asked me. Spec corrected to 72 (D15) |
| 2026-10-01 | Phase 1 | Used a `sed` command to edit `health_audit.py` | No. The command treated `\\|` as a pattern and broke the file | Seen on the very next read. File restored. Some shell commands also failed on quoting. From then on, multi-line edits used the file-writing tools |
| 2026-10-01 | Phase 1–2 | Checker helpers recomputed every health-check and rule number, apart from the helpers that wrote them | Yes | The final audit finds 20 defects, against 10 listed in the brief. 2 are critical (`output/DEFECT_LOG.md`) |
| 2026-10-01 | Phase 3 | Set the plan's Groq model `llama-3.3-70b-versatile` as the backup model | No. The provided key could not use it | Listed the models the key can use. Set the backup to `openai/gpt-oss-120b` (D17) |
| 2026-10-01 | Phase 3 | Wrote the safety check that only allows known numbers in AI answers | No. It treated 4-digit account codes like "6100" and "6310" as invented amounts. On the first live recording, 33% of AI answers were replaced by a fixed template. Intent reviews that named accounts were rejected | Found by reading the safety-check events in the trace (the run log). Now a plain 4-digit number is checked as an account code. An invented "3600" still fails, because it is not in the chart of accounts (D22). Fallback rate went to 0% (`guardrail_fallback_rate 0.0000` in `output/evals/report.md`) |
| 2026-10-01 | Phase 3 | A separate helper attacked the AI boundary that was already built | Yes. It found 5 real holes | (a) A memo containing `</untrusted_data>` could close the safe wrapper and inject instructions. Now `<` and `>` are made harmless. (b) On retry, the error text re-sent the injected sentence without the wrapper. Fixed. (c) Amounts stuck to letters ("USD3600", "3_600") got past the number check. Fixed. (d) A fix could use an invented small amount: a debit/credit 5.00 "fix" for JE-002 passed as a solution. Fix amounts now use a stricter money-only list (D21). (e) A broken recorded-answer file crashed the run. Now handled |
| 2026-10-01 | Phase 5 | The eval tool ran the 17 synthetic (made-up) test cases through the safety checks | It found a false alarm. "SYN-11" was read as the number −11, because the ID pattern only knew `JE-` | Fixed narrowly. `JE-`/`SYN-` IDs and short codes like `ABC-123` (3 digits or fewer) count as IDs (D30). So "USD-3600" is not a way around the check |
| 2026-10-01 | Phase 5 | The Intent Reviewer (Gemini) raised three synthetic entries that the rules had already REJECTED | Mixed. SYN-05 (circular payroll entry): correct. SYN-09 (an injection attempt): it ignored the injected instruction and treated the description as empty, which is what we want. SYN-10 ("Insurance prepayment" not touching cash): open to debate | Allowed in the eval cases as `llm_allowed`. Shown in the report as "R013 (allowed)" (D27). Decisions did not change. The AI can only raise severity, never lower it |
| 2026-10-01 | Phase 5 | The Explainer (Gemini) wrote the JE-003 explanation | Partly wrong. It says the system translates the EUR and GBP balances of account 1110 "at the period-end rate". The R007 rule message adds "or the configured fallback where one is missing". That is what happens to GBP: there is no GBP period-end rate, so the period-average rate is used (assumption A4) | Left as is and documented. The safety checks test numbers and account codes, not meaning, so this passes. It is text only. The QUARANTINED decision comes from fixed rules and does not change |
| 2026-10-01 | Phase 6 | The browser-testing helper used the built frontend in a headless browser (Playwright), including a 420 px wide screen | Yes. Found real bugs: the page scrolled sideways at 420 px (hidden screen-reader text leaked out of scroll areas), totals were cut off, a side panel did not stretch, and the main code file the browser downloads (the bundle) was 767 kB | Fixed the layout bugs. Split the bundle. The main file is now 468 kB |
| 2026-10-02 | Phase 7 | Drafted this log and `REFLECTION.md` from the build session record | To be checked | Marked for the candidate to review before sending |

## What I noticed

- **Fast and exact when the expected answers are known. It needed me when the spec
  contradicted itself.** Tables of expected decisions became tests in one pass. The tool found
  the R009 conflict by checking numbers. But I decided which rule was correct.
- **The bugs were in its own code at the AI boundary.** The main assistant wrote the safety
  checks. It still shipped the 4-digit code false alarm, five attack holes, and the "SYN-11"
  false alarm. Each was found by a separate check after the code was written: the trace, the
  attacking helper, and the eval tool.
- **Separate writers and checkers worked.** Checkers recomputed numbers from scratch. That is
  why the defect log and rule results can be trusted. Attacking the code found more than
  writing more tests.
- **The safety checks test numbers, not meaning.** The JE-003 "period-end rate" wording has
  every number and code right, and is still wrong about GBP. No check in this build can catch
  that.
- **Tool slips are cheap if every edit is re-read.** The `sed` mistake was caught on the next
  read of the file. Every step ended with the full set of checks.

## Where AI led me wrong

- The safety check rejected good explanations. 33% of calls fell back to the template in the
  first live recording, until the trace showed why.
- The first version of the AI boundary let a memo containing `</untrusted_data>` inject
  instructions. It also accepted a fix for JE-002 with an invented 5.00 amount.
- The plan named a Groq model the key could not use.
- The starter project's defaults (React 19, TypeScript not strict) differed from the spec. The
  tool that created them did not point this out.
- The JE-003 explanation still says "period-end rate" for GBP. It is in the current run output
  (`output/runs/0f6fe063474d/decisions.json`).
