#!/usr/bin/env python3
"""Create a SHA-256 manifest for a specified workflow release directory."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

EXCLUDED_PARTS = {".git", "__pycache__"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if not args.root.is_dir():
        raise SystemExit(f"Root does not exist: {args.root}")
    output_resolved = args.output.resolve()
    files: List[Dict[str, object]] = []
    for path in sorted(args.root.rglob("*")):
        if not path.is_file() or any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        if path.resolve() == output_resolved:
            continue
        files.append(
            {
                "relative_path": str(path.relative_to(args.root)),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    manifest = {
        "workflow_release": "HMF_RCT_PublicationWorkflow_v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "root": str(args.root),
        "file_count": len(files),
        "files": files,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote manifest with {len(files)} files: {args.output}")


if __name__ == "__main__":
    main()
