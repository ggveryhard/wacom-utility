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
    parser.add_argument("--unit-extra", action="append", default=[])
    parser.add_argument("--service-extra", action="append", default=[])
    args = parser.parse_args()

    template = Path(args.template).read_text(encoding="utf-8")
    service_extra = list(args.service_extra)
    if args.path:
        service_extra.insert(0, f"Environment=PATH={args.path}")

    unit_extra = "\n".join(args.unit_extra)
    service_extra_text = "\n".join(service_extra)

    rendered = template.replace("@UNIT_EXTRA@", unit_extra)
    rendered = rendered.replace("@SERVICE_EXTRA@", service_extra_text)
    rendered = rendered.replace("@EXECSTART@", args.exec_start)
    rendered = rendered.replace("\n\n[Service]", "\n[Service]")
    rendered = rendered.replace("\n\nExecStart=", "\nExecStart=")
    Path(args.output).write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
