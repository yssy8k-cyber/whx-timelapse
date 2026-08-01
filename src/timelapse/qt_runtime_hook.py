"""Set Qt plugin paths before PyQt6 imports in a frozen application."""

from __future__ import annotations

import os
import sys
from pathlib import Path


bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
plugin_candidates = [
    bundle_root / "PyQt6" / "Qt6" / "plugins",
    bundle_root.parent / "Resources" / "PyQt6" / "Qt6" / "plugins",
    bundle_root.parent / "Frameworks" / "PyQt6" / "Qt6" / "plugins",
]
for plugin_dir in plugin_candidates:
    if (plugin_dir / "platforms").is_dir():
        os.environ.setdefault("QT_PLUGIN_PATH", str(plugin_dir))
        os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", str(plugin_dir / "platforms"))
        break
