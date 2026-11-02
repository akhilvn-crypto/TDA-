---
description: Design automation-ready test cases from your Markdown user stories. Asks where the stories are, then analyses them one at a time, generates validated test cases in the canonical format, and saves them locally with story traceability.
argument-hint: "[story file | directory | file name]"
disable-model-invocation: true
---

# /test-design-pipeline:start

Arguments: `$ARGUMENTS`

1. Read `${CLAUDE_PLUGIN_ROOT}/agents/test-design-orchestrator.md` (if the variable is not expanded, find the installed `test-design-pipeline` plugin folder, the one whose `.claude-plugin/plugin.json` has name `test-design`) and **act as that orchestrator in this conversation**. Read the rules it names. Do not hand the user conversation to a subagent.
2. Story source:
   - If `$ARGUMENTS` is not empty, use it as the story location and **do not ask for it again**.
   - Otherwise ask exactly: "Where are your user stories located?" (a Markdown file path, a directory, or a file name).
3. If a previous run exists in the chosen project root, load the `workflow-resume` skill and offer to resume rather than starting over.
4. Follow the orchestrator workflow in order: discover and confirm sources and project root, verify access, then for each story analyse, design coverage, generate, validate and save, checkpointing as it specifies. Finish with its concise summary.
