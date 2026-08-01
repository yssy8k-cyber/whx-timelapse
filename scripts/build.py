"""Build the native desktop artifact for the current operating system."""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "WHXTimelapse.spec"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build WHX Timelapse with PyInstaller")
    parser.add_argument("--clean", action="store_true", help="清理 PyInstaller 的临时构建缓存")
    args = parser.parse_args()

    if platform.system() not in {"Darwin", "Windows"}:
        raise SystemExit("此脚本只支持在 macOS 或 Windows 原生环境构建。")
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", str(SPEC)]
    if args.clean:
        command.insert(-1, "--clean")
    print("Building for", platform.system())
    env = os.environ.copy()
    env["PYINSTALLER_CONFIG_DIR"] = str(ROOT / ".pyinstaller")
    subprocess.run(command, cwd=ROOT, check=True, env=env)
    print("Artifacts are in", ROOT / "dist")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
