from pathlib import Path

import pytest

from timelapse.render import build_concat_manifest, find_images, render


def test_find_images_is_timestamp_sorted(tmp_path):
    (tmp_path / "frame_20260731_120002.jpg").write_bytes(b"2")
    (tmp_path / "frame_20260731_120001.JPG").write_bytes(b"1")
    (tmp_path / "notes.txt").write_text("ignore", encoding="utf-8")

    assert [path.name for path in find_images(tmp_path)] == [
        "frame_20260731_120001.JPG",
        "frame_20260731_120002.jpg",
    ]


def test_concat_manifest_escapes_paths(tmp_path):
    image = tmp_path / "camera's frame.jpg"
    image.write_bytes(b"jpeg")

    manifest = build_concat_manifest([image], 25)

    assert "camera'\\''s frame.jpg" in manifest
    assert "duration 0.040000000" in manifest
    assert manifest.count("file '") == 2


def test_render_uses_atomic_output(monkeypatch, tmp_path):
    image = tmp_path / "frame_20260731_120000.jpg"
    image.write_bytes(b"jpeg")
    output = tmp_path / "out" / "timelapse.mp4"
    captured_args = []

    def fake_run_ffmpeg(args, *, ffmpeg_bin):
        captured_args.append((args, ffmpeg_bin))
        Path(args[-1]).write_bytes(b"mp4")

    monkeypatch.setattr("timelapse.render.run_ffmpeg", fake_run_ffmpeg)

    assert render(tmp_path, output, fps=30, ffmpeg_bin="ffmpeg-test") == output.resolve()
    assert output.read_bytes() == b"mp4"
    assert captured_args[0][1] == "ffmpeg-test"
    assert "-f" in captured_args[0][0]
    assert "30" in captured_args[0][0]
    assert not list(output.parent.glob("*.part.mp4"))


def test_render_requires_images(tmp_path):
    with pytest.raises(ValueError, match="没有"):
        render(tmp_path, tmp_path / "out.mp4")
