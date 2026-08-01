from pathlib import Path

import pytest

from threading import Event

from timelapse.capture import CaptureConfig
from timelapse.pipeline import capture_and_render, run_postprocess


def test_capture_and_render_uses_only_frames_from_this_job(monkeypatch, tmp_path):
    frames = [tmp_path / "frame_1.jpg", tmp_path / "frame_2.jpg"]
    rendered = tmp_path / "timelapse.mp4"
    calls = []

    monkeypatch.setattr("timelapse.pipeline.capture", lambda config, stop_event: frames)

    def fake_render(input_dir, output, **kwargs):
        calls.append((input_dir, output, kwargs["images"]))
        return rendered

    monkeypatch.setattr("timelapse.pipeline.render", fake_render)
    result = capture_and_render(
        CaptureConfig("rtsp://camera/stream", tmp_path),
        Event(),
        rendered,
    )

    assert result == (frames, rendered)
    assert calls == [(tmp_path, rendered, frames)]


def test_manual_stop_does_not_start_auto_render(monkeypatch, tmp_path):
    frames = [tmp_path / "frame_1.jpg"]
    stop_event = Event()
    stop_event.set()
    monkeypatch.setattr("timelapse.pipeline.capture", lambda config, event: frames)
    monkeypatch.setattr(
        "timelapse.pipeline.render",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not render")),
    )

    result = capture_and_render(
        CaptureConfig("rtsp://camera/stream", tmp_path),
        stop_event,
        tmp_path / "timelapse.mp4",
    )

    assert result == (frames, None)


def test_postprocess_expands_placeholders(monkeypatch, tmp_path):
    calls = []
    output = tmp_path / "processed.mp4"

    def fake_run(args, check):
        calls.append((args, check))
        output.write_bytes(b"processed")

    monkeypatch.setattr("timelapse.pipeline.subprocess.run", fake_run)
    result = run_postprocess("ai-tool render {input} --output {output}", tmp_path / "input.mp4", output)

    assert result == output
    assert calls == [(["ai-tool", "render", str(tmp_path / "input.mp4"), "--output", str(output)], True)]


def test_postprocess_requires_both_placeholders(tmp_path):
    with pytest.raises(ValueError, match="同时包含"):
        run_postprocess("ai-tool render {input}", tmp_path / "input.mp4", tmp_path / "output.mp4")
