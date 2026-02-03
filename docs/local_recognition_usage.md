# 识别配置

## 本地识别方案

本项目支持通过 **Whisper ONNX** 进行本地识别，无需联网即可处理视频。

### 使用方法

1. 下载 Whisper ONNX 模型（推荐使用 `base` 或 `small` 版本）。
2. 将模型文件放置在 `backend/models` 目录下。
3. 在应用设置中选择 "本地 Whisper 识别"。

## 云端识别方案 (SenseVoice)

默认使用 **SenseVoice API** 进行高精度识别，需要配置 **SiliconFlow API Key**。

### 优势
- 极高的识别准确率
- 极速处理（GPU 加速）
- 支持多种语言和标点符号自动纠正
