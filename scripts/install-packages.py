#!/usr/bin/env python3
"""Copy nuttx_periphery from a .whl into a target directory (no pip).

Usage:
    python3 install-packages.py [DESTDIR] [WHEEL]

Defaults:
    DESTDIR  /data
    WHEEL    newest *.whl in this script's directory
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

PACKAGE = "nuttx_periphery"


def find_wheel(directory: Path) -> Path:
    """Find the newest .whl in directory*."""
    wheels = sorted(
        directory.glob("*.whl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not wheels:
        raise FileNotFoundError(f"no .whl in {directory}")
    return wheels[0]


def install(wheel: Path, destdir: Path) -> None:
    """Install the wheel into the destination directory."""
    prefix = f"{PACKAGE}/"
    destdir.mkdir(parents=True, exist_ok=True)
    target = destdir / PACKAGE
    if target.exists():
        shutil.rmtree(target)

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        print(f"extracting {wheel} to {tmpdir}")
        with zipfile.ZipFile(wheel) as zf:
            members = [
                name
                for name in zf.namelist()
                if name.startswith(prefix) and not name.endswith("/")
            ]
            if not members:
                raise RuntimeError(f"wheel has no {PACKAGE} package")
            zf.extractall(tmpdir, members=members)

        shutil.copytree(tmpdir / PACKAGE, target)

    print(f"copied {PACKAGE} -> {target}")
    print(f"export PYTHONPATH={destdir}:$PYTHONPATH")


def main(argv: list[str] | None = None) -> int:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "destdir",
        nargs="?",
        default="/data",
        type=Path,
        help="install directory (default: /data)",
    )
    parser.add_argument(
        "wheel",
        nargs="?",
        type=Path,
        help="path to .whl (default: newest *.whl next to this script)",
    )
    args = parser.parse_args(argv)

    try:
        wheel = (args.wheel or find_wheel(script_dir)).resolve()
        if not wheel.is_file():
            print(f"error: wheel not found: {wheel}", file=sys.stderr)
            return 1
        install(wheel, args.destdir.resolve())
    except (FileNotFoundError, RuntimeError, zipfile.BadZipFile) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
