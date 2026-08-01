from pathlib import Path

import pytest

from timelapse.capture import CaptureConfig, build_snapshot_args, capture_one


def test_build_snapshot_args_does_not_transform_rtsp_url():
    config = CaptureConfig(
        rtsp_url="rtsp://user:pass@camera/Streaming/Channels/101",
        output_dir=Path("captures"),
        timeout=12.5,
    )

    args = build_snapshot_args(config, Path("captures/frame.part.jpg"))

    assert "-rtsp_transport" in args
    assert args[args.index("-i") + 1] == config.rtsp_url
    assert args[args.index("-rw_timeout") + 1] == "12500000"
    assert args[-1].endswith("frame.part.jpg")


def test_capture_one_replaces_temporary_file(monkeypatch, tmp_path):
    calls = []

    def fake_run_ffmpeg(args, *, timeout, ffmpeg_bin):
        calls.append((args, timeout, ffmpeg_bin))
        Path(args[-1]).write_bytes(b"jpeg")

    monkeypatch.setattr("timelapse.capture.run_ffmpeg", fake_run_ffmpeg)
    config = CaptureConfig("rtsp://camera/stream", tmp_path, timeout=4)
    destination = tmp_path / "frame_20260731_120000_000000.jpg"

    assert capture_one(config, destination) == destination
    assert destination.read_bytes() == b"jpeg"
    assert not list(tmp_path.glob("*.part.jpg"))
    assert calls[0][1] == 9


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"interval": 0}, "间隔"),
        ({"count": 0}, "数量"),
        ({"count": 1, "duration": 1}, "只能二选一"),
    ],
)
def test_capture_config_validation(kwargs, message):
    config = CaptureConfig("rtsp://camera/stream", Path("captures"), **kwargs)
    with pytest.raises(ValueError, match=message):
        config.validate()
