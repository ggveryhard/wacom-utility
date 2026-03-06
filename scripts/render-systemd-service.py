#!/usr/bin/env python3
"""Render a systemd unit from the shared template."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--exec-start", required=True)
    parser.add_argument("--path")
    args = parser.parse_args()

    template = Path(args.template).read_text(encoding="utf-8")
    path_directive = f"Environment=PATH={args.path}" if args.path else ""
    if path_directive:
        rendered = template.replace("@PATH_DIRECTIVE@", path_directive)
    else:
        rendered = template.replace("@PATH_DIRECTIVE@\n", "")
    rendered = rendered.replace("@EXECSTART@", args.exec_start)
    Path(args.output).write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
