---
description: Validate the saved test cases - canonical format, IDs, test data and env references, dependencies, expected results - and the story traceability. Reports findings; changes nothing unless you approve a safe fix.
argument-hint: "[project root]"
disable-model-invocation: true
---

# /test-design:validate

Arguments: `$ARGUMENTS`

1. Load the `test-case-validation` skill (`${CLAUDE_PLUGIN_ROOT}/skills/test-case-validation/SKILL.md`; if the variable is not expanded, find the installed `test-design` plugin folder) and read `${CLAUDE_PLUGIN_ROOT}/rules/test-case-format.md`.
2. Project root: `$ARGUMENTS` if given, otherwise the nearest ancestor of the working directory containing `test-design/test-cases/test-cases.md`. If none is found, ask.
3. Run, with `python` (or `python3` / `py -3`):
   - `validate-test-cases.py "<root>/test-design/test-cases/test-cases.md"`
   - `validate-traceability.py --test-cases ... --traceability "<root>/test-design/state/traceability.json" --fingerprints "<root>/test-design/state/source-fingerprints.json"` (skip with a note if the state files do not exist, for example for hand-written cases)
4. Report concisely: case count, errors and warnings grouped by code with the case IDs, and the coverage warnings (stories or criteria without a case). Explain each error in one line using the skill's finding table.
5. Do not edit anything. If there are formatting-only findings, offer a safe fix: produce a normalised copy with `--fix-safe --fix-output`, show what would change, and only after the user agrees replace the file with `safe-file-operations.py write --expect-sha256 <current hash> ...` (a backup is kept). Never invent IDs, expected results or behaviour; errors that need information from the story are listed for the user to decide.
6. Hand edits the user made to the file are theirs: report problems in them, never rewrite their text without asking.
