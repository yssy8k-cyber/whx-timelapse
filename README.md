# RTSP 延时摄影工具

这是一套基于 Python 标准库和 FFmpeg 的命令行工具，适合从海康威视等支持 RTSP 的摄像头定时保存图片，再把图片序列合成为 MP4 延时视频。

## 环境准备

需要 Python 3.9 及以上版本，以及 FFmpeg。确认 FFmpeg 已经在 PATH 中：

```bash
ffmpeg -version
```

macOS 可用 `brew install ffmpeg`，Debian/Ubuntu 可用 `sudo apt install ffmpeg`。Windows 请安装 FFmpeg 并把其 `bin` 目录加入 PATH，也可以通过 `--ffmpeg /path/to/ffmpeg` 指定可执行文件。

在项目目录创建虚拟环境并安装本项目：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Windows PowerShell 的激活命令是 `.venv\Scripts\Activate.ps1`。

## RTSP 地址

海康威视常见地址格式：

```text
rtsp://用户名:密码@摄像头IP:554/Streaming/Channels/101
```

主码流通常是 `101`，子码流通常是 `102`，实际通道号以设备配置为准。用户名或密码包含 `@`、`#`、`:` 等字符时，先进行 URL 编码。不要把真实密码写入 Git；可以复制 `.env.example` 的变量到当前终端环境：

```bash
export RTSP_URL='rtsp://user:password@192.168.1.100:554/Streaming/Channels/101'
```

## 定时抽帧

立即抓第一帧，之后每 10 秒抓一帧，抓够 360 张后停止：

```bash
timelapse capture \
  --rtsp "$RTSP_URL" \
  --interval 10 \
  --count 360 \
  --output-dir captures
```

也可以运行指定时长，例如运行 1 小时：

```bash
timelapse capture --rtsp "$RTSP_URL" --interval 10 --duration 3600
```

默认通过 TCP 拉流，网络不稳定时通常比 UDP 更容易排查。可用 `--transport udp` 切换。单次连接默认超时 30 秒，失败会记录日志并在下一个间隔重试。

## 合成 MP4

图片文件名按 `frame_YYYYMMDD_HHMMSS_microseconds.jpg` 生成，工具会按文件名排序：

```bash
timelapse render \
  --input-dir captures \
  --output output/timelapse.mp4 \
  --fps 24
```

`--fps` 是最终视频播放帧率，不是摄像头采集帧率。每 10 秒一张、24fps 时，360 张图片约生成 15 秒视频。已有输出文件默认不会覆盖，确认后可加 `--overwrite`。

## 一键流水线

```bash
timelapse run \
  --rtsp "$RTSP_URL" \
  --interval 10 \
  --duration 3600 \
  --output output/timelapse.mp4 \
  --fps 24
```

## 可选 AI/外部后处理

由于不同 AI 视频工具的命令行或 API 不同，主控脚本提供了一个不绑定厂商的外部命令钩子。命令必须包含 `{input}` 和 `{output}`，工具会以参数列表方式执行，不经过 shell：

```bash
timelapse run \
  --rtsp "$RTSP_URL" \
  --interval 10 \
  --count 360 \
  --output output/timelapse.mp4 \
  --postprocess-command 'ai-tool render {input} --output {output}'
```

后处理结果会写到 `output/timelapse_processed.mp4`。如果目标工具只有 HTTP API，可以把 `ai-tool` 替换成一个本地适配器脚本，由适配器负责上传、等待任务完成和下载结果。

## 常用选项

```text
capture: --interval --count/--duration --transport --timeout --jpeg-quality --ffmpeg
render:  --fps --crf --preset --overwrite --ffmpeg
run:     同时支持以上两组参数，以及 --postprocess-command
```

运行帮助：

```bash
timelapse --help
timelapse capture --help
```

## 原生桌面客户端

启动 PyQt6 原生窗口：

```bash
timelapse gui
```

客户端直接打开操作系统窗口，不启动本地 HTTP 服务，也不会调用默认浏览器。窗口支持填写 RTSP 地址、开始/停止抽帧、实时查看最近图片；采集自然结束后会按输出设置自动合成 MP4。背景图片由 Qt `QPainter` 单独以 20% 透明度绘制，前景控件保持清晰。

运行测试（需要安装测试可选依赖）：

```bash
python -m pip install -e '.[test]'
python -m pytest
```

## 打包桌面应用

项目使用 PyInstaller 打包。桌面入口是 PyQt6 原生 `QMainWindow`；PyQt6 运行时、背景图片和 FFmpeg 会被一并打包，Windows 使用单文件和隐藏控制台模式，macOS 使用标准 `.app` bundle 和隐藏控制台模式。

先安装构建依赖：

```bash
python -m pip install -r requirements-build.txt
```

把图标放入 `assets/app.ico`（Windows）和 `assets/app.icns`（macOS），然后必须在目标系统原生构建：

```bash
python scripts/build.py --clean
```

产物名称为 `QQQ.exe` 和 `QQQ-Windows-Setup.exe`。PyInstaller 不能在 macOS 上交叉生成 Windows 程序，因此仓库提供了 `.github/workflows/build-desktop.yml`，推送 `main` 或 `v*` 标签后，会在 Windows runner 上构建、启动冒烟测试并上传安装包。

如果 macOS 首次提示无法验证开发者，优先右键应用选择“打开”。仍被隔离时，只解除这个应用的隔离属性，不要关闭系统安全机制：

```bash
xattr -dr com.apple.quarantine "/Users/你的用户名/Documents/New project/dist/WHX延时摄影自动化工具.app"
open -n "/Users/你的用户名/Documents/New project/dist/WHX延时摄影自动化工具.app"
```

启动异常日志位于 `~/Library/Logs/WHXTimelapse/startup.log`。

## 安全与运行建议

- RTSP 地址中的密码属于敏感信息，避免写入脚本、日志和 Git。
- 建议给摄像头单独创建只读用户，并限制摄像头网络访问范围。
- 长时间运行时使用 `systemd`、`launchd` 或 Windows 任务计划程序托管进程。
- 先用 `--count 3` 做连通性和画面验证，再开始长时间采集。
