# Test Design

A Claude plugin that turns Markdown user stories into **automation-ready test cases**. It reads your stories one at a time, designs coverage with the right techniques, writes concise test cases in a fixed Markdown format, keeps story-to-test traceability, and saves everything locally so an interrupted run can be resumed safely.

Test Design decides **what to validate**. The downstream Automation Builder decides how to automate and run it. This plugin does not repeat BA gap analysis, edit your stories, or write Playwright code.

## Install

The plugin is distributed through a Claude plugin marketplace. Replace the placeholders with your marketplace's repository and name.

```bash
# add the marketplace (GitHub repo, git URL, or local path)
claude plugin marketplace add <owner>/<marketplace-repo>

# install the plugin from it
claude plugin install test-design@<marketplace-name>
```

Inside Claude Code the same two steps are `/plugin marketplace add <owner>/<marketplace-repo>` and `/plugin install test-design@<marketplace-name>`; on recent versions one step also works: `/plugin install test-design --marketplace <owner>/<marketplace-repo>`. Then check that `/test-design:start`, `/test-design:status`, `/test-design:resume` and `/test-design:validate` are listed.

To try it from a local checkout without installing: `claude --plugin-dir ./test-design`.

**Requirements:** Python 3.9 or newer on the machine that runs Claude (standard library only; nothing is installed for you). Developed and tested on Python 3.14.

## Use

```text
/test-design:start                         # asks: Where are your user stories located?
/test-design:start docs/stories            # a directory (searched recursively for .md)
/test-design:start docs/stories/login.md   # one file
/test-design:start login                   # a bare file name
```

1. **Pick the stories.** A file, a directory, or a name. If several files match you choose which to process. Only `.md` is supported. The story folder is the default project root and you confirm the output location before anything is written.
2. **Per story:** analyse, design coverage, generate cases, validate, save. You see one progress line per story, and a question only when something blocks reliable test design (for example a limit the story mentions but never states).
3. **Summary:** stories processed, cases generated, validation issues, output location, and the `env:` variables you need to provide.

| Command | What it does |
|---|---|
| `/test-design:start [path]` | Run the workflow. Offers to resume if a run exists in that project |
| `/test-design:status` | Phase, per-story progress, case counts, and whether your stories changed since generation (read-only) |
| `/test-design:resume` | Continue the last incomplete run. Asks before touching anything affected by changed stories |
| `/test-design:validate` | Check saved cases (format, IDs, data, dependencies, expected results) and traceability. Changes nothing without your approval |

## What it writes

Everything goes under the project root you confirm. Your story files are never modified.

```text
<project-root>/test-design/
├── test-cases/test-cases.md       # the single consolidated file the Automation Builder reads
└── state/
    ├── workflow.json              # checkpoint: phase, per-story status, hashes
    ├── traceability.json          # which stories each case verifies (kept out of the Markdown)
    ├── source-fingerprints.json   # story hashes for change detection
    ├── audit.jsonl                # event history
    └── backups/                   # copies of anything the plugin replaced
```

There is no approval queue: cases that pass validation are saved directly. Cases that cannot be validated are not saved, and the summary tells you why.

## Test-case format

The contract with the Automation Builder (see `templates/test-cases.template.md`):

```markdown
# Login

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

- **IDs** are always written. Use your own test IDs if your stories supply them; otherwise the plugin derives a stable `AUTO-xxxxxxxx` from the source story ID and the case title. An ID is never changed afterwards, even if you rename the case.
- **Test data:** `env:NAME` for secrets and environment-specific values (the value lives in `automation/.env`, which this plugin never touches), `literal:value` for deliberately fake fixed values, and plain text for ordinary values. Secret values are never written to any file or message.
- **Steps** are actions and **expected results** are observable outcomes. No selectors or automation code.

## Safety

- Source stories are read-only; all writes are confined to `<root>/test-design/` and checked by the scripts.
- Saving *appends* validated cases to the end of their module and leaves the rest of the file byte-for-byte unchanged, so hand edits survive. Replacing an existing case needs your explicit yes and keeps a backup.
- Writes use a temp file, atomic replace and a read-back hash check.
- If a story changes after generation, `status` and `resume` show which cases are linked to it and ask what to do. Nothing is regenerated automatically.
- Missing or corrupt state is reported, never assumed complete.
- If Python is missing the plugin explains why it is needed and asks before installing anything.

## Claude Code CLI and Cowork

Both surfaces run the same commands, agents, rules and output contract. The plugin verifies at runtime that it can read your stories and write to the project root, and tells you plainly if a surface cannot (for example no filesystem or no script execution) instead of changing the workflow. Where the interactive question dialog is unavailable it asks numbered questions in chat.

## Repository layout

```text
.claude-plugin/plugin.json   manifest
commands/                    start, status, resume, validate (thin entry points)
agents/                      orchestrator, story-analyser, test-coverage-designer,
                             test-case-generator, test-case-quality-checker
skills/                      reusable procedures (discovery, analysis, coverage,
                             authoring, validation, resume)
rules/                       principles, format, data & secrets, traceability, safe file ops
schemas/                     workflow state, traceability, test-case metadata (JSON Schema)
templates/                   canonical sample and state template
scripts/                     deterministic Python tools (+ td_common.py shared library)
tests/                       unittest suite and fixtures
```

## Develop and test

```bash
python -m unittest discover -s tests -t tests      # 130 tests, standard library only
claude plugin validate ./test-design               # manifest and component check
```

Scripts can be run by hand; each prints JSON:

```bash
python scripts/discover-story-files.py docs/stories
python scripts/validate-test-cases.py test-design/test-cases/test-cases.md
python scripts/generate-stable-id.py --story US-001 --title "Valid user can sign in"
```

## Marketplace registration (maintainers)

Keep `.claude-plugin/marketplace.json` in the **marketplace** repository, not here. Add an entry whose `name` matches `plugin.json` (`test-design`) and keep the versions equal:

```json
{
  "name": "test-design",
  "source": "./plugins/test-design",
  "description": "Design automation-ready test cases from Markdown user stories.",
  "version": "0.1.0",
  "category": "testing",
  "tags": ["testing", "test-design", "qa", "traceability"]
}
```

Use `"source": "./plugins/test-design"` when the plugin folder lives inside the marketplace repository, or a GitHub source object when it stays in its own repository. Then run `claude plugin validate ./path/to/marketplace`, add the marketplace in a clean environment, install, and confirm the four commands appear.

## License

MIT. See `LICENSE`.
