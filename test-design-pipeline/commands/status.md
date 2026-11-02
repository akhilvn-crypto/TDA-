---
description: Show the current Test Design run - phase, per-story progress, generated test case counts, validation outcome, and whether your source stories changed since generation. Read-only.
argument-hint: "[project root]"
disable-model-invocation: true
---

# /test-design-pipeline:status

Arguments: `$ARGUMENTS`

Read-only: write nothing.

1. Load the `workflow-resume` skill (`${CLAUDE_PLUGIN_ROOT}/skills/workflow-resume/SKILL.md`; if the variable is not expanded, find the installed `test-design-pipeline` plugin folder) and follow its "Locate the run" and "Status report" sections.
2. Project root: `$ARGUMENTS` if given, otherwise the nearest ancestor of the working directory containing `test-design/state/workflow.json`. If none is found, say so and ask for the project root.
3. Read `workflow.json` and show: run ID and status, current phase and story, a per-story table (story ID, status, analysis status, test-case file, cases, validation), totals (stories processed of total, cases generated), unresolved clarifications, and output paths.
4. Check source drift with `fingerprint-sources.py compare ... --root <root> --traceability <root>/test-design/state/traceability.json --workflow <root>/test-design/state/workflow.json` and list changed, added or removed stories, the cases linked to them and the story files that are stale (`staleTestCaseFiles`). Also run `story-analysis-state.py plan --root <root>` (without `--apply`, so nothing is written) and list the stories whose saved analysis would be rerun or is invalidated, with the reason. If the state file is missing or corrupt, explain exactly what is wrong and what you would suggest; do not repair it.
5. End with the next step: `/test-design-pipeline:resume` for an incomplete run, `/test-design-pipeline:validate` to check the saved cases, or nothing if everything is complete.
