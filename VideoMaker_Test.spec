"""VideoMaker_Test 独立验证工具的 PyInstaller 配置。"""

from pathlib import Path

import imageio_ffmpeg
from PyInstaller.utils.hooks import collect_data_files


project_root = Path.cwd()
ffmpeg_binary = Path(imageio_ffmpeg.get_ffmpeg_exe())
datas = collect_data_files("imageio_ffmpeg")
datas.append((str(ffmpeg_binary), "imageio_ffmpeg/binaries"))

a = Analysis(
    [str(project_root / "video_maker_test.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=["imageio_ffmpeg"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VideoMaker_Test",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, upx_exclude=[], name="VideoMaker_Test")
