"""Command-line interface for the timelapse toolkit."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from .capture import CaptureConfig, capture
from .pipeline import run_pipeline
from .render import render


def _common_ffmpeg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--ffmpeg", default=os.getenv("FFMPEG_BIN", "ffmpeg"), help="FFmpeg 可执行文件路径")


def _add_capture_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--rtsp", default=os.getenv("RTSP_URL"), help="RTSP 地址，也可通过 RTSP_URL 设置")
    parser.add_argument("--output-dir", type=Path, default=Path("captures"), help="图片输出目录")
    parser.add_argument("--interval", type=float, default=10.0, help="抽帧间隔（秒），默认 10")
    stop = parser.add_mutually_exclusive_group()
    stop.add_argument("--count", type=int, help="成功图片数量；不指定则持续运行")
    stop.add_argument("--duration", type=float, help="运行时长（秒）；不指定则持续运行")
    parser.add_argument("--transport", choices=["tcp", "udp", "http", "https"], default="tcp", help="RTSP 传输方式")
    parser.add_argument("--timeout", type=float, default=30.0, help="单次连接超时（秒）")
    parser.add_argument("--jpeg-quality", type=int, default=2, help="JPEG 质量 1-31，数字越小质量越高")
    _common_ffmpeg(parser)


def _capture_config(args: argparse.Namespace) -> CaptureConfig:
    if not args.rtsp:
        raise ValueError("请通过 --rtsp 或 RTSP_URL 提供 RTSP 地址。")
    return CaptureConfig(
        rtsp_url=args.rtsp,
        output_dir=args.output_dir,
        interval=args.interval,
        count=args.count,
        duration=args.duration,
        ffmpeg_bin=args.ffmpeg,
        transport=args.transport,
        timeout=args.timeout,
        jpeg_quality=args.jpeg_quality,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="海康威视 RTSP 延时摄影工具")
    parser.add_argument("--verbose", action="store_true", help="显示更详细的日志")
    subparsers = parser.add_subparsers(dest="command", required=True)

    capture_parser = subparsers.add_parser("capture", help="定时从 RTSP 流抓取 JPG")
    _add_capture_args(capture_parser)

    render_parser = subparsers.add_parser("render", help="把图片序列合成为 MP4")
    render_parser.add_argument("--input-dir", type=Path, default=Path("captures"), help="图片目录")
    render_parser.add_argument("--output", type=Path, default=Path("output/timelapse.mp4"), help="MP4 输出路径")
    render_parser.add_argument("--fps", type=float, default=24.0, help="视频帧率，默认 24")
    render_parser.add_argument("--crf", type=int, default=18, help="H.264 质量参数，默认 18")
    render_parser.add_argument("--preset", default="medium", help="H.264 编码速度预设")
    render_parser.add_argument("--overwrite", action="store_true", help="覆盖已有输出文件")
    _common_ffmpeg(render_parser)

    pipeline_parser = subparsers.add_parser("run", help="连续抽帧并合成视频")
    _add_capture_args(pipeline_parser)
    pipeline_parser.add_argument("--output", type=Path, default=Path("output/timelapse.mp4"), help="MP4 输出路径")
    pipeline_parser.add_argument("--fps", type=float, default=24.0, help="视频帧率，默认 24")
    pipeline_parser.add_argument("--crf", type=int, default=18, help="H.264 质量参数，默认 18")
    pipeline_parser.add_argument("--preset", default="medium", help="H.264 编码速度预设")
    pipeline_parser.add_argument("--overwrite", action="store_true", help="覆盖已有输出文件")
    pipeline_parser.add_argument(
        "--postprocess-command",
        help="可选外部后处理命令，使用 {input} 和 {output} 占位符，例如 ai-tool render {input} --out {output}",
    )

    subparsers.add_parser("gui", help="启动 PyQt6 原生桌面客户端")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        if args.command == "capture":
            capture(_capture_config(args))
        elif args.command == "render":
            output = render(
                args.input_dir,
                args.output,
                fps=args.fps,
                ffmpeg_bin=args.ffmpeg,
                crf=args.crf,
                preset=args.preset,
                overwrite=args.overwrite,
            )
            logging.info("视频已生成: %s", output)
        elif args.command == "run":
            output = run_pipeline(
                _capture_config(args),
                args.output,
                fps=args.fps,
                crf=args.crf,
                preset=args.preset,
                overwrite=args.overwrite,
                postprocess_command=args.postprocess_command,
            )
            logging.info("流水线已完成: %s", output)
        elif args.command == "gui":
            from .main import main as gui_main

            return gui_main()
    except (ValueError, FileExistsError, RuntimeError) as exc:
        parser.error(str(exc))
    except KeyboardInterrupt:
        logging.info("已停止。")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
