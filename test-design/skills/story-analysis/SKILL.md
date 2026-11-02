---
name: story-analysis
description: Read and understand one user story at a time and extract the behaviour needed for test design (ID, intent, acceptance criteria, business rules, NFRs, preconditions, dependencies, ambiguities) without producing an analysis report. Use for every story before coverage design.
user-invocable: false
---

# Story analysis

Goal: a compact, transient picture of one story that is accurate enough to design tests from. Nothing here is saved except the criterion labels in `traceability.json`.

## Procedure

1. **Locate the story.** Use the story's `startLine`/`endLine` from `source-fingerprints.json` and read only that range of its file (Read with offset/limit). Never load the whole collection.
2. **Extract**, in the story's own words:
   - `id`, `title`, one-sentence `intent` (who needs what, why).
   - `criteria`: each acceptance criterion as a labelled item `AC-1`, `AC-2`... in source order.
   - `rules`: business rules and constraints with exact values (limits, durations, formats) as `BR-1`...
   - `nfrs`: testable non-functional requirements with their measurable targets as `NFR-1`... Ignore vague NFRs ("should be fast") unless a target is given.
   - `preconditions`, `roles`, `data` the story names (accounts, plans, records).
   - `dependencies`: other story IDs, systems, or data the story needs.
   - `messages`: exact UI texts, URLs or values the story states, so expected results can quote them.
3. **Load related stories only when needed**: a dependency whose behaviour you must know to write a precondition or a shared journey step. Find it by ID in `source-fingerprints.json`, read just its line range, and take only what the current story relies on. Do not analyse it.
4. **Decide testability.** If the story states no observable behaviour (a pure heading, a placeholder), report `testable: false` with the reason; the orchestrator records `no_testable_behaviour`.
5. **Raise ambiguity sparingly.** Return a `clarifications` item only when the ambiguity stops you writing an assertable expected result for a stated criterion (for example "locked for a while" with no duration, or a message that is not given and cannot be observed otherwise). Each item: the question in one sentence, why it blocks, and what tests it blocks. Do not ask about missing detail that merely limits depth; list it under `notes` instead.
6. **Return** a single JSON object to the orchestrator (not a file, not a report):

```json
{
  "id": "US-001", "title": "Registered user login", "sourceFile": "auth/login.md",
  "intent": "A registered user signs in to reach the dashboard.",
  "criteria": [{"label": "AC-1", "text": "Valid credentials reach the dashboard"}],
  "rules":    [{"label": "BR-1", "text": "Account locked 15 minutes after 5 consecutive failures"}],
  "nfrs": [], "preconditions": ["A registered, active account exists"],
  "dependencies": [], "messages": ["Invalid email or password"],
  "testable": true, "clarifications": [], "notes": []
}
```

## Never

- Invent a requirement, value or message. If the story does not say it, it is not there.
- Repeat BA gap analysis, grade story quality, or rewrite the story.
- Edit the source file.
