# Timelapse Studio

基于 Python 3.12、PySide6、OpenCV 和 FFmpeg 的海康威视 RTSP 长期延时摄影工具。

## 当前阶段

第一阶段至第三阶段基础功能已完成：

- PySide6 模块化主界面
- RTSP 地址、用户名和密码输入
- OpenCV 后台线程连接测试
- JSON 配置保存与启动恢复
- 文件日志和界面日志窗口
- 图片目录选择
- 独立定时截图线程
- 按日期目录保存 JPEG 图片
- 预设及自定义截图间隔
- 摄像头取帧与截图线程的线程安全连接
- FFmpeg H.264 MP4 视频生成
- 15、24、30、60 FPS 视频设置
- 视频生成成功后的可选图片清理
- 独立视频生成线程与 GUI 按钮接入
- 固定间隔或每天固定时间触发的视频生成调度服务
- 视频生成计划、日期范围和完成动作配置保存与启动恢复
- RTSP 断流检测和 10 秒自动重连
- 浅色/深色主题切换与配置恢复
- QueueListener 异步日志线程与滚动日志文件
- 多设备配置档案、设备切换和旧版配置迁移
- 独立 RTSP 实时画面预览，限制 12 FPS 并显示分辨率、FPS 和码流类型
- 预览与截图使用独立视频流和线程，支持刷新预览及截图中的 REC 计时标识
- 独立图片保存目录和视频输出目录
- 图片保留全部、生成后删除、保留最近 N 天三种策略
- 手动、固定间隔、每天固定时间三种视频生成计划
- 今天、昨天、最近 24 小时、最近 7 天和自定义日期范围
- 视频命名模板、同名覆盖/重命名/提示策略及完成后的目录打开和提示

Windows EXE 和安装程序已配置 GitHub Actions 自动打包。

## GitHub Actions 打包

推送到 `main` 后，GitHub Actions 会在 Windows runner 上自动安装 Python 3.12、运行测试、构建 EXE，并上传 `TimelapseStudio-Windows-*` Artifact。
同时会使用 Inno Setup 生成 `TimelapseStudio-Setup.exe`，上传为独立 Artifact。安装默认位于当前用户的 `%LOCALAPPDATA%\Timelapse Studio`，不会要求管理员权限。

本地可使用以下命令验证 PyInstaller 配置：

```bash
./.venv/bin/python -m PyInstaller --noconfirm --clean TimelapseStudio.spec
```

## Windows 开发环境

```powershell
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py
```

当前项目依赖中包含 `imageio-ffmpeg`，用于提供 FFmpeg 可执行文件；`TimelapseStudio.spec` 会在打包时将其一并放入应用目录。

macOS 本地开发环境可以使用项目内的 `.tools/uv` 和 `.venv/bin/python`，不需要改动系统 Python：

```bash
./.tools/uv venv --python 3.12 .venv
./.tools/uv pip install --python .venv/bin/python -r requirements.txt
./.venv/bin/python main.py
```

配置文件保存到 `config/settings.json`，日志保存到 `logs/`。

视频计划默认使用 MP4(H.264)，视频文件保存到独立的视频输出目录。文件名模板支持
`{date}`、`{time}` 和 `{camera}`，例如 `Timelapse_{date}.mp4`。

海康威视常见 RTSP 地址格式：

```text
rtsp://摄像头地址:554/Streaming/Channels/101
```
