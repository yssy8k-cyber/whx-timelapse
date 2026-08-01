# PyInstaller native Qt desktop build for Windows and macOS.
# Build natively on each target OS; PyInstaller is not a cross-compiler.

from pathlib import Path
import os
import sys
from typing import Optional



ROOT = Path(SPECPATH).resolve()
ASSETS = ROOT / "assets"
PACKAGE_ASSETS = ROOT / "src" / "timelapse" / "assets"
QT_RUNTIME_HOOK = ROOT / "src" / "timelapse" / "qt_runtime_hook.py"
ICON = None
if sys.platform == "win32":
    candidate = ROOT / "assets" / "app.ico"
    ICON = str(candidate) if candidate.is_file() else None
elif sys.platform == "darwin":
    candidate = ROOT / "assets" / "app.icns"
    ICON = str(candidate) if candidate.is_file() else None


def find_ffmpeg() -> Optional[str]:
    configured = os.getenv("FFMPEG_BINARY")
    if configured and Path(configured).is_file():
        return configured
    try:
        import imageio_ffmpeg

        bundled = imageio_ffmpeg.get_ffmpeg_exe()
    except (ImportError, RuntimeError):
        return None
    return bundled if Path(bundled).is_file() else None


ffmpeg = find_ffmpeg()
if not ffmpeg:
    raise RuntimeError(
        "找不到 FFmpeg。请先安装 imageio-ffmpeg，或设置 FFMPEG_BINARY 指向对应平台的 FFmpeg 可执行文件。"
    )


datas = [(str(PACKAGE_ASSETS / "background.jpg"), "timelapse/assets")]
binaries = [(ffmpeg, "bin")]

a = Analysis(
    [str(ROOT / "src" / "timelapse" / "main.py")],
    pathex=[str(ROOT / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(QT_RUNTIME_HOOK)],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
if sys.platform == "darwin":
    # A native .app needs a bundle directory; use onedir inside it.
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="QQQ",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        icon=ICON,
    )
    coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="QQQ")
    app = BUNDLE(
        coll,
        name="QQQ.app",
        icon=ICON,
        bundle_identifier="com.whx.qqq",
        info_plist={
            "CFBundleDisplayName": "QQQ",
            "NSHighResolutionCapable": True,
        },
    )
else:
    # Windows remains a single-file executable for convenient distribution.
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name="QQQ",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        icon=ICON,
    )
