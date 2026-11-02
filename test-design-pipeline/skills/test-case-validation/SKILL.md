---
name: test-case-validation
description: Validate drafted or saved test cases (structure, IDs, data and env references, dependencies, expected results, duplicates, traceability) with the deterministic scripts, interpret every finding code, apply safe fixes, and decide what may be saved. Use before every save and in /test-design-pipeline:validate.
user-invocable: false
---

# Test-case validation

Two layers. **Deterministic** (scripts, authoritative for structure) and **semantic** (the quality checker agent, for coverage, clarity and testability). A structurally valid case is not automatically a good test. `PY` / `SCRIPTS` as in `story-source-discovery`.

## Commands

- Draft: `PY SCRIPTS/validate-test-cases.py <draft> --existing "<root>/test-design/test-cases/test-cases.md"` (omit `--existing` on the first story). Exit 0 = no errors; 1 = errors (JSON in stdout either way). Add `--strict` to fail on warnings.
- Formatting fixes: `... --fix-safe --fix-output <fixed.md>` writes a normalised copy (trailing spaces, step numbering, bullet markers, spacing around `-> Expected:`, blank lines). It never edits the input and never changes meaning; it cannot invent IDs.
- Saved file: `PY SCRIPTS/validate-test-cases.py "<root>/test-design/test-cases/test-cases.md"` and
  `PY SCRIPTS/validate-traceability.py --test-cases "<root>/test-design/test-cases/test-cases.md" --traceability "<root>/test-design/state/traceability.json" --fingerprints "<root>/test-design/state/source-fingerprints.json"`.

Read `summary` and `findings` (each: `code`, `severity`, `message`, `line`, `caseId`) and the per-case `valid` flag.

## Finding codes

**Errors (block saving)**

| Code | Meaning / what to do |
|---|---|
| `ID_MISSING` | Case has no ID. Generate with `generate-stable-id.py`; never hand-type |
| `ID_FORMAT` | `AUTO-` ID not `AUTO-` + 8 lowercase hex. Regenerate |
| `DUPLICATE_ID` | Same ID twice, or already saved. Keep the existing one; ask before replacing |
| `TITLE_MISSING` | Empty title |
| `STEPS_MISSING` / `STEPS_EMPTY` / `STEP_FORMAT` | Steps section absent, empty, or lines not `1. text` |
| `EXPECTED_MISSING` / `EXPECTED_EMPTY` / `EXPECTED_WEAK` | No assertable outcome. Write what is observable, from the story; if the story does not say, ask |
| `PLACEHOLDER_TEXT` | TBD/TODO/`<...>` left in. Replace with real content or ask |
| `IMPLEMENTATION_DETAIL` | Selector or automation code in a step. Rewrite as the user action |
| `VARIABLE_UNDECLARED` | `{x}` used but not in Test Data. Declare it |
| `DATA_FORMAT` / `DUPLICATE_DATA` | Test Data line not `- name: value`, or declared twice |
| `ENV_REF_INVALID` | `env:` not followed by an UPPER_SNAKE_CASE name (the value is never echoed; do not repeat it) |
| `SECRET_PLAIN_VALUE` / `SECRET_DETECTED` | Credential-named variable with plain value, or token-shaped text. Use `env:` / `literal:` |
| `DEPENDENCY_UNKNOWN` / `DEPENDENCY_SELF` / `DEPENDENCY_CYCLE` / `DEPENDENCY_FORMAT` | Fix or drop the dependency; prefer independent cases |
| `DUPLICATE_SCENARIO` | Identical preconditions, data, steps and results as another case. Remove one or make the data differ meaningfully |
| `STRAY_CONTENT` / `UNKNOWN_FIELD` / `UNKNOWN_SECTION` / `UNKNOWN_HEADING` / `DUPLICATE_SECTION` / `DUPLICATE_FIELD` / `FIELD_EMPTY` / `BULLET_FORMAT` | Structure outside the contract. Remove or restructure |
| `NO_CASES` | File has no `## ID: Title` headings |

**Warnings (report, do not block)**: `STEP_NUMBERING` (auto-fixable), `SECTION_ORDER`, `PRIORITY_VALUE`, `EXPECTED_DUPLICATED` (inline expectation repeated under Expected Results; keep one), `EXPECTED_VAGUE` (vague words without a quoted value; improve if the story gives the value), `VARIABLE_UNUSED`, `DUPLICATE_TITLE` (same title in a module; make titles distinct).

**Traceability** (`validate-traceability.py`): errors `SCHEMA`, `ORPHAN_CASE` (case with no mapping or no ID), `NO_STORY`, `UNKNOWN_STORY`, `BAD_COVERS`; warnings `STALE_MAPPING`, `STORY_UNCOVERED`, `CRITERION_UNCOVERED`, `SOURCE_STORY_MISSING`.

## Procedure for a draft

1. Validate. If errors are only formatting-class (`STEP_FORMAT` numbering, spacing, bullet markers), run `--fix-safe` and validate the fixed copy.
2. Remaining errors that you can correct without inventing behaviour (declare a variable, replace a selector with the action, regenerate an ID): fix in the draft, re-validate. At most two repair rounds per story.
3. If an error needs information the story does not give (an expected message, a limit), do not guess: ask the user one focused question, or drop that case from the draft and report it.
4. Run the semantic check (quality checker agent). It may correct wording and formatting; it must not change what is being verified.
5. Save only a draft with `errors: 0`. Never save a case with an error; drop it (and any case that depends on it) and record the reason in `workflow.json` validation findings.
6. Warnings are recorded in the story's `validation.findings` and summarised to the user at the end.

## Semantic checks (quality checker)

Coverage of every `AC`/`BR`/`NFR` label; each step is one clear action; each expected result is observable and specific; data declared and secret-safe; dependencies genuine; no near-duplicate scenarios; no contradictory expectations across cases for the same story; no behaviour the story does not state.
