"""Command-line interface.

clausekit analyze contract.txt --pretty
cat contract.txt | clausekit analyze -
clausekit analyze contract.txt --risks-only
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__
from .extractor import analyze


def _read_input(source: str) -> str:
    if source == "-":
        return sys.stdin.read()
    return Path(source).read_text(encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="clausekit",
        description="Extract and classify clauses from Arabic/English contracts.",
    )
    parser.add_argument("--version", action="version", version=f"clausekit {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("analyze", help="analyse a contract text file")
    run.add_argument("file", help="path to a UTF-8 text file, or - for stdin")
    run.add_argument("--pretty", action="store_true", help="indent the JSON output")
    run.add_argument("--output", "-o", help="write JSON to this file instead of stdout")
    run.add_argument(
        "--risks-only", action="store_true", help="output only parties, risk flags and the summary"
    )
    run.add_argument(
        "--split-level",
        type=int,
        default=1,
        help="deepest plain numbering level that starts a clause (default 1)",
    )
    run.add_argument(
        "--min-score",
        type=float,
        default=3.0,
        help="minimum keyword score for a clause type (default 3.0)",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        text = _read_input(args.file)
    except (OSError, UnicodeDecodeError) as exc:
        print(f"clausekit: cannot read {args.file}: {exc}", file=sys.stderr)
        return 2

    result = analyze(text, split_level=args.split_level, min_score=args.min_score).to_dict()
    if args.risks_only:
        result = {k: result[k] for k in ("language", "parties", "risks", "summary")}

    payload = json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    else:
        sys.stdout.write(payload + "\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
