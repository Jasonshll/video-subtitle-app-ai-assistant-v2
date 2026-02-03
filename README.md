# 阿泽字幕助手 (Subtitle Pro)

基于 **Silero-VAD** + **SenseVoice** 的智能视频语音识别与字幕生成工具。

## 技术架构

- **前端**: Electron + React + TypeScript + Tailwind CSS
- **后端**: Python + Flask + Flask-SocketIO
- **语音识别**: Silero-VAD (语音检测) + SenseVoice API (文字识别)
- **通信**: WebSocket 实时进度推送

## 功能特性

- **批量处理**: 支持最多 10 个视频同时处理
- **实时预览**: WebSocket 实时显示处理进度
- **字幕编辑**: 内置字幕编辑器，支持修改文本 and 时间戳
- **多格式导出**: 支持 SRT 字幕格式 and 纯文本导出
- **暗黑模式**: 支持深色/亮色主题切换
- **长视频支持**: 优化内存管理，支持 1 分钟 - 2 小时视频
