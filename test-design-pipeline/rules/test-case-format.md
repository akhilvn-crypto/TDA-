# Test-case format (canonical contract)

This is the interface to the Automation Builder. Do not replace it, add fields, or rename headings.

```markdown
# Module                                  <- optional grouping; may repeat in one file

## TC-001: Valid user can sign in         <- ID: Title
Priority: High                            <- optional
Tags: smoke, auth                         <- optional, comma-separated
Depends on: TC-000                        <- optional, only if it must run first

### Preconditions                         <- only conditions required before execution
- An active test account exists

### Test Data                             <- every {variable} used in Steps
- email: env:TEST_USER_EMAIL
- plan: Premium
- wrong_password: literal:wrong-pass-1

### Steps                                 <- numbered; optional inline "-> Expected:"
1. Open the login page
2. Enter {email} in the Email field
3. Click the "Sign in" button -> Expected: The dashboard is displayed

### Expected Results                      <- final observable outcomes
- The heading "Dashboard" is visible
```

The `<-` notes are explanations for you; never write them into a test-case file.

## Rules

- Headings: `#` module, `##` case, `###` only `Preconditions`, `Test Data`, `Steps`, `Expected Results`, in that order. No other headings, no prose between them, no front matter.
- Fields directly under the `##` line, in any order, only `Priority:`, `Tags:`, `Depends on:`. Omit a field instead of leaving it empty. Priority is one of Critical, High, Medium, Low.
- **This plugin always writes the ID**: `## <ID>: <Title>`. A supplied ID is used verbatim. Otherwise derive `AUTO-xxxxxxxx` with `scripts/generate-stable-id.py` (never invent or hand-type one). An existing ID is never changed on regeneration or edit.
- Steps: one action each, numbered 1..n, imperative, in domain language. Inline `-> Expected:` only for an immediate assertion; do not repeat it under Expected Results.
- Expected results: specific, observable, assertable ("The message "Invalid email or password" is displayed", not "login fails properly"). At least one per case, inline or in the section.
- `Depends on:` lists IDs that exist, never itself, never forming a cycle. Use it only when the case genuinely cannot run without the other having run first.
- Test Data: plain literal for ordinary values; `env:NAME` for secrets and environment-specific values; `literal:value` for a deliberately fake or explicitly fixed value. Details in `test-data-and-secrets.md`.
- Story traceability is **not** part of this file. It lives in `state/traceability.json`.

`scripts/validate-test-cases.py` enforces this. Findings and what they mean: `skills/test-case-validation/SKILL.md`.
