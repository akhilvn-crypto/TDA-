---
description: Validate the saved test cases - one file per story - for canonical format, IDs, test data and env references, dependencies, expected results, and the story traceability. Validate everything or just one story's file. Reports findings; changes nothing unless you approve a safe fix.
argument-hint: "[project root] [story ID]"
disable-model-invocation: true
---

# /test-design-pipeline:validate

Arguments: `$ARGUMENTS`

1. Load the `test-case-validation` skill (`${CLAUDE_PLUGIN_ROOT}/skills/test-case-validation/SKILL.md`; if the variable is not expanded, find the installed `test-design-pipeline` plugin folder) and read `${CLAUDE_PLUGIN_ROOT}/rules/test-case-format.md`.
2. Project root: the first argument if it is a folder, otherwise the nearest ancestor of the working directory containing a `test-design/test-cases/` folder. An optional story ID (for example `US-001`) limits the check to that story's file. If no root is found, ask.
3. Run, with `python` (or `python3` / `py -3`):
   - Everything: `validate-test-cases.py --dir "<root>/test-design/test-cases"` (each `<USER_STORY_ID>-testcase.md` against its own story, plus IDs unique across files) and `validate-traceability.py --test-cases-dir "<root>/test-design/test-cases" --traceability "<root>/test-design/state/traceability.json" --fingerprints "<root>/test-design/state/source-fingerprints.json"`.
   - One story: `validate-test-cases.py "<root>/test-design/test-cases/<story>-testcase.md" --story-id <story> --check-file-name --traceability "<root>/test-design/state/traceability.json"` and `validate-traceability.py --test-cases "<that file>" --traceability ...`. Nothing else is opened.
   - Skip the traceability call with a note if the state files do not exist, for example for hand-written cases. A legacy `test-cases.md` is validated and reported with `LEGACY_CONSOLIDATED_FILE`; offer `safe-file-operations.py split-legacy` (dry run first) but change nothing without a yes.
4. Report concisely: files and case counts, errors and warnings grouped by code with the file and case IDs, and the coverage warnings (stories or criteria without a case). Explain each error in one line using the skill's finding table.
5. Do not edit anything. If there are formatting-only findings, offer a safe fix: produce a normalised copy with `--fix-safe --fix-output`, show what would change, and only after the user agrees replace that one file with `safe-file-operations.py write --expect-sha256 <current hash> ...` (a backup is kept). Never invent IDs, expected results or behaviour; errors that need information from the story are listed for the user to decide.
6. Hand edits the user made to the file are theirs: report problems in them, never rewrite their text without asking.
