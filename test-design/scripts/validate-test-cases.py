#!/usr/bin/env python3
"""Validate a test-case Markdown file against the canonical contract.

    validate-test-cases.py FILE [--existing FILE] [--external-id ID ...] [--strict]
    validate-test-cases.py FILE --fix-safe --fix-output PATH

Checks structure, unique IDs, expected results, ``{variable}`` declarations, ``env:`` references,
secret-looking values, dependencies (existing + acyclic), implementation detail in steps and
duplicate scenarios. ``--existing`` supplies already-saved cases: their IDs are valid dependency
targets and are checked for duplicates. Prints a JSON report; exit 1 when there are errors
(or any finding with ``--strict``). ``--fix-safe`` writes a formatting-only normalised copy to
``--fix-output`` and never edits FILE.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import td_common as td  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--existing", help="saved test-cases.md to check IDs, dependencies and duplicates against")
    ap.add_argument("--external-id", action="append", default=[], help="extra valid dependency ID (repeatable)")
    ap.add_argument("--strict", action="store_true", help="treat warnings as failures")
    ap.add_argument("--fix-safe", action="store_true", help="write a formatting-only fixed copy to --fix-output")
    ap.add_argument("--fix-output")
    args = ap.parse_args()

    path = Path(args.file)
    if not path.is_file():
        raise td.fail("FILE_MISSING", f"{path} does not exist", td.EXIT_MISSING)
    text = td.read_text(path)

    if args.fix_safe:
        if not args.fix_output:
            raise td.fail("USAGE", "--fix-safe needs --fix-output PATH (the input file is never edited)", td.EXIT_USAGE)
        out = Path(args.fix_output).resolve()
        if out == path.resolve():
            raise td.fail("USAGE", "--fix-output must differ from the input file", td.EXIT_USAGE)
        fixed, fixes = td.fix_safe(text)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(fixed.encode("utf-8"))
        text = fixed
        fix_info = {"fixesApplied": fixes, "fixedFile": str(out)}
    else:
        fix_info = {}

    existing = None
    if args.existing:
        ep = Path(args.existing)
        if ep.is_file():
            existing = td.parse_test_cases(td.read_text(ep))
    doc = td.parse_test_cases(text)
    findings = td.validate_doc(doc, existing, set(args.external_id))
    report = td.validation_report(doc, findings, str(path))
    report.update(fix_info)
    td.emit(report)
    failing = report["summary"]["errors"] + (report["summary"]["warnings"] if args.strict else 0)
    return td.EXIT_FINDINGS if failing else td.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
