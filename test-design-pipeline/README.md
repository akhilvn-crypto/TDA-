# Test Design Pipeline

A Claude plugin that turns Markdown user stories into **automation-ready test cases**. It analyses each story in its own isolated agent session, one at a time, designs coverage with the right techniques, writes concise test cases in a fixed Markdown format, keeps story-to-test traceability, and saves one test-case file per user story, and keeps everything local so an interrupted run can be resumed safely.

Test Design decides **what to validate**. The downstream Automation Builder decides how to automate and run it. This plugin does not repeat BA gap analysis, edit your stories, or write Playwright code.

## Install

The plugin is distributed through the `tda` marketplace in the GitHub repository `akhilvn-crypto/TDA-`.

```bash
# add the marketplace
claude plugin marketplace add akhilvn-crypto/TDA-

# install the plugin from it
claude plugin install test-design-pipeline@tda

# later, to update
claude plugin marketplace update tda
claude plugin update test-design-pipeline@tda
```

Inside Claude Code the same steps are `/plugin marketplace add akhilvn-crypto/TDA-` and `/plugin install test-design-pipeline@tda`. Then check that `/test-design-pipeline:start`, `/test-design-pipeline:status`, `/test-design-pipeline:resume` and `/test-design-pipeline:validate` are listed. See the repository's top-level README for the full install, update and flow guide.

To try it from a local checkout without installing: `claude --plugin-dir ./test-design-pipeline`.

**Requirements:** Python 3.9 or newer on the machine that runs Claude (standard library only; nothing is installed for you). Developed and tested on Python 3.14.

## Use

```text
/test-design-pipeline:start                         # asks: Where are your user stories located?
/test-design-pipeline:start docs/stories            # a directory (searched recursively for .md)
/test-design-pipeline:start docs/stories/login.md   # one file
/test-design-pipeline:start login                   # a bare file name
```

1. **Pick the stories.** A file, a directory, or a name. If several files match you choose which to process. Only `.md` is supported. The story folder is the default project root and you confirm the output location before anything is written.
2. **Per story:** analyse (in a fresh, isolated worker), design coverage, generate cases, validate, save. You see one progress line per story, and a question only when something blocks reliable test design (for example a limit the story mentions but never states).
3. **Summary:** stories processed, test-case files and cases generated, validation issues, output location, and the `env:` variables you need to provide.

| Command | What it does |
|---|---|
| `/test-design-pipeline:start [path]` | Run the workflow. Offers to resume if a run exists in that project |
| `/test-design-pipeline:status` | Phase, per-story progress, files and case counts, and which story files are stale because their story changed (read-only) |
| `/test-design-pipeline:resume` | Continue the last incomplete run. Asks, story by story, before touching a file affected by a changed story |
| `/test-design-pipeline:publish-zephyr <file>` | Publish one saved test-case file to Zephyr Scale Cloud and link every created case to a Jira story. Only when you run it; see "Publishing to Zephyr Scale" |
| `/test-design-pipeline:validate [root] [story]` | Check saved cases (format, IDs, data, dependencies, expected results) and traceability, for every story file or one story's. Changes nothing without your approval |

## Isolated story analysis

Every story is analysed by its **own fresh `story-analyser` invocation**, so one story's reasoning, wording or mistakes cannot leak into the next, and a long collection never fills a single context.

- **Sequential.** The orchestrator takes the stories in file order and runs one worker at a time. There is no parallel execution.
- **One reusable worker.** A single `story-analyser` definition is started anew for each story (one `Agent` call per story, never continued with `SendMessage`, never forked). There is no agent definition per story.
- **Minimal input.** A worker receives only: `run_id`, `story_id`, `story_content` (that story alone), `relevant_shared_rules` (only rules the story needs), `dependency_context` (a small read-only excerpt of a story it explicitly names, only where needed), `analysis_instructions` and `output_schema_version`. It never gets the workflow state, the source document, other stories, earlier analyses, generated cases or any transcript. `story-analysis-state.py begin` builds this input and refuses one that holds more than one story, unexpected fields or a secret.
- **Structured result.** The worker returns one compact JSON object (`schemas/story-analysis.schema.json`, version 2) and finishes: `story_id`, `story_summary`, `behaviour_to_validate`, `acceptance_criteria_interpretation`, `business_rules`, `preconditions`, `dependencies`, `relevant_non_functional_expectations`, `test_design_considerations`, `ambiguities`, `analysis_complete`. It is an internal handoff to coverage design, not a report, and is never written into your story file.
- **Validated before use.** `story-analysis-state.py complete` checks the result (schema, matching story ID, complete, unique labels, no secrets). An invalid or partial result is never passed to coverage design: the story is marked `failed`, the orchestrator retries it once in another fresh worker, and a second failure leaves it for `/test-design-pipeline:resume` to retry on its own. The orchestrator never falls back to analysing stories in its own context.
- **Checkpoints and resume.** Per story, `workflow.json` records the analysis status (`not_started`, `in_progress`, `completed`, `failed`), the story fingerprint, the fingerprints of the shared rules and dependency excerpts used, and the last completed stage; the result is saved in `state/analysis/<story-id>.json`. Resume reuses a completed analysis only while those fingerprints are unchanged. A changed story, a changed shared rule or a changed dependency invalidates only the analyses that used it. Existing test cases and files are never regenerated without your explicit yes.
- **Shared rules (optional).** If your stories rely on a project-level rules file (Markdown, one rule per heading), name it when you confirm the sources; it is stored as `sharedRulesFile`. Each worker gets only the rules that apply to its story, and editing a rule invalidates only the stories that used it.
- **Audit evidence.** `audit.jsonl` records `analysis_started`, `analysis_completed`, `analysis_failed` and `analysis_invalidated` (IDs and counts only). `story-analysis-state.py check-audit` verifies from it that workers ran one at a time and that no worker session served two stories. Worker transcripts are not stored.

**Runtime requirement.** Isolation depends on the host starting a separate agent session for each `Agent` call, which Claude Code does. If a surface cannot do that, the orchestrator stops and says so instead of analysing stories in one shared context.

## What it writes

Everything goes under the project root you confirm. Your story files are never modified.

```text
<project-root>/test-design/
├── test-cases/
│   ├── US-001-testcase.md         # one file per user story: only that story's cases
│   ├── US-002-testcase.md         # <USER_STORY_ID>-testcase.md, all directly in this folder
│   └── ...                        # any one file can be handed to the Automation Builder on its own
└── state/
    ├── workflow.json              # checkpoint: phase, per-story status, analysis checkpoint, each story's file + hash
    ├── analysis/<story-id>.json   # validated structured story analysis (internal handoff, no transcripts)
    ├── traceability.json          # which stories each case verifies, and each story's file (kept out of the Markdown)
    ├── source-fingerprints.json   # story hashes for change detection
    ├── audit.jsonl                # event history
    └── backups/                   # copies of anything the plugin replaced
```

There is no approval queue: cases that pass validation are saved directly. Cases that cannot be validated are not saved, and the summary tells you why.

## One file per story

Each story gets `test-design/test-cases/<USER_STORY_ID>-testcase.md` (`US-001-testcase.md`, `PROJ-123-testcase.md`). The Markdown format, IDs and validation rules are exactly the ones below; the only change is where the cases live.

- **Only its own story.** Every module in a file carries that story's `User Story ID:`. The validator (`--story-id`) rejects a file that holds anything else, and `merge-cases --story-id` only writes to the story's own file name.
- **Self-contained.** A case may depend only on cases in the same file (`DEPENDENCY_CROSS_FILE` otherwise; put cross-story setup in Preconditions), so the Automation Builder can consume any one file without the others. Test IDs are unique across all files; this is checked from `traceability.json`, so saving one story never opens another story's file.
- **Handing a file to the Automation Builder.** Point it at the file for the story you want, for example `test-design/test-cases/US-001-testcase.md`. Nothing else from `test-design/` is needed.
- **A changed story regenerates only its own file.** `status` and `resume` compare each story with the fingerprint recorded when its file was generated (`stories.<id>.testCaseFile.sourceSha256`) and list the stale files. For each one you choose keep, regenerate or skip. Regenerating shows a dry run (case IDs kept / changed / added / removed) first, replaces the file only after your yes, asks again if you had hand-edited it, and keeps a backup. Unchanged scenarios keep their IDs. Other stories' files are not read or written.
- **Existing files are never silently overwritten.** Saving appends to the story's file and leaves existing bytes alone. If `<story>-testcase.md` already exists but was not recorded by the run, you are asked before anything is appended.
- **Older output.** A run made before 0.5.0 has one consolidated `test-cases.md`. It keeps working and is never modified on its own; `validate` flags it, and `safe-file-operations.py split-legacy` (dry run first, then `--yes`) splits it into per-story files using each module's `User Story ID:` and moves the old file to `state/backups/`.

## Publishing to Zephyr Scale

Optional and fully separate from generation. Nothing is published unless you run it, and only the one file you name.

```text
/test-design-pipeline:publish-zephyr test-design/test-cases/US-001-testcase.md
```

Configure Zephyr Scale Cloud in the project's git-ignored `.env` (or the environment). Create the token in Jira under your profile > Zephyr Scale API Access Tokens:

```env
ZEPHYR_BASE_URL=https://api.zephyrscale.smartbear.com/v2
ZEPHYR_API_TOKEN=<your token>
```

Jira is reached through the Atlassian connector you already have connected; no Jira credentials are added. Only Zephyr Scale **Cloud** (REST API v2) is supported; a Data Center/Server URL is refused.

1. **Preflight (stops at the first failure with a fix):** Jira connector authenticated, accessible projects listed, **you confirm the Jira project**, Zephyr settings present, Zephyr reachable with a valid token and the project open, file exists/readable/valid.
2. **Story mapping:** you give the Jira story key (`PROJ-101`); it must exist, belong to the confirmed project and be a Story (other types need your confirmation); its numeric issue ID is read from Jira. Nothing is created before this passes.
3. **Convert and publish:** each case becomes a Zephyr test case (title, preconditions, ordered steps, per-step test data and expected results, tags as labels), is created once, and is linked to the story. Fields with no Zephyr equivalent are reported; `Depends on` needs your decision before the case is published without it.

Safe retries: progress is saved after every stage in `test-design/state/zephyr-publishing.json` (+ `zephyr-publishing-audit.jsonl`, no secrets). Re-running the same command never creates a case twice, retries only a missing link/steps step, and never overwrites, edits or deletes anything in Zephyr. If a create request's outcome is unknown (timeout), that case waits for you to check Zephyr and run `zephyr-publish.py resolve` instead of risking a duplicate. The Markdown file is never modified. Details: `skills/zephyr-publishing/SKILL.md`.

## Test-case format

The contract with the Automation Builder (see `templates/test-cases.template.md`):

```markdown
# Login
User Story ID: US-001

## AUTO-ea4e94fb: Valid user can sign in
Priority: High
Tags: smoke, auth

### Preconditions
- An active test account exists

### Test Data
- email: env:TEST_USER_EMAIL
- password: env:TEST_USER_PASSWORD

### Steps
1. Open the login page
2. Enter {email} in the Email field
3. Enter {password} in the Password field
4. Click the "Sign in" button -> Expected: The dashboard is displayed

### Expected Results
- The heading "Dashboard" is visible
- The URL contains "/dashboard"
```

- **User Story ID** sits directly under the `# Module` heading and applies to every case in that section; it is never repeated inside a case. A module that covers several stories repeats its heading once per story, each with its own `User Story ID:`. The line is optional when reading, so files written before it existed stay valid and are read as before; newly generated cases always carry it.
- **IDs** are always written. Use your own test IDs if your stories supply them; otherwise the plugin derives a stable `AUTO-xxxxxxxx` from the source story ID and the case title. An ID is never changed afterwards, even if you rename the case.
- **Test data:** `env:NAME` for secrets and environment-specific values (the value lives in `automation/.env`, which this plugin never touches), `literal:value` for deliberately fake fixed values, and plain text for ordinary values. Secret values are never written to any file or message.
- **Steps** are actions and **expected results** are observable outcomes. No selectors or automation code.

## Safety

- Source stories are read-only; all writes are confined to `<root>/test-design/` and checked by the scripts.
- Saving *appends* validated cases to the end of their module in the story's own file and leaves the rest of the file byte-for-byte unchanged, so hand edits survive. Replacing an existing case, or regenerating a whole story file, needs your explicit yes and keeps a backup.
- Writes use a temp file, atomic replace and a read-back hash check.
- If a story changes after generation, `status` and `resume` show which story file and cases are linked to it and ask what to do. Nothing is regenerated automatically, and only that story's file is ever regenerated.
- Missing or corrupt state is reported, never assumed complete.
- If Python is missing the plugin explains why it is needed and asks before installing anything.

## Claude Code CLI and Cowork

Both surfaces run the same commands, agents, rules and output contract. The plugin verifies at runtime that it can read your stories and write to the project root, and tells you plainly if a surface cannot (for example no filesystem or no script execution) instead of changing the workflow. Where the interactive question dialog is unavailable it asks numbered questions in chat.

## Repository layout

```text
.claude-plugin/plugin.json   manifest
commands/                    start, status, resume, validate, publish-zephyr (thin entry points)
agents/                      orchestrator, story-analyser (single-story worker), test-coverage-designer,
                             test-case-generator, test-case-quality-checker
skills/                      reusable procedures (discovery, analysis, coverage,
                             authoring, validation, resume)
rules/                       principles, format, data & secrets, traceability, safe file ops
schemas/                     workflow state, traceability, test-case metadata, story analysis input/result/record (JSON Schema)
templates/                   canonical sample and state template
scripts/                     deterministic Python tools (+ td_common.py shared library)
tests/                       unittest suite and fixtures
```

## Develop and test

```bash
python -m unittest discover -s tests -t tests      # all tests, standard library only
claude plugin validate ./test-design-pipeline               # manifest and component check
```

Scripts can be run by hand; each prints JSON:

```bash
python scripts/discover-story-files.py docs/stories
python scripts/validate-test-cases.py test-design/test-cases/US-001-testcase.md --story-id US-001 --check-file-name
python scripts/validate-test-cases.py --dir test-design/test-cases       # every story file + cross-file rules
python scripts/generate-stable-id.py --story US-001 --title "Valid user can sign in"
python scripts/story-analysis-state.py plan --root .    # which story analyses would be reused or rerun
```

## Marketplace registration (maintainers)

This plugin is listed in the `tda` marketplace, defined by `.claude-plugin/marketplace.json` at the root of the `akhilvn-crypto/TDA-` repository (the plugin lives in `./test-design-pipeline`). To release an update, bump `version` in both that file and `.claude-plugin/plugin.json` (keep them equal), run `claude plugin validate .` from the repository root, and push to `main`. See the top-level README for the user-facing update steps.

## License

MIT. See `LICENSE`.
