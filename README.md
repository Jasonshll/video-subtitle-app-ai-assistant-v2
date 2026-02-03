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
- **字幕编辑**: 内置字幕编辑器，支持修改文本和时间戳
- **多格式导出**: 支持 SRT 字幕格式和纯文本导出
- **暗黑模式**: 支持深色/亮色主题切换
- **长视频支持**: 优化内存管理，支持 1 分钟 - 2 小时视频

## 安装步骤

### 1. 克隆项目

```bash
git clone https://github.com/Jasonshll/video-subtitle-app-ai-assistant-v2.git
cd video-subtitle-app-ai-assistant-v2
```

### 2. 安装前端依赖

```bash
cd frontend
npm install
cd ..
```

### 3. 安装 Electron 依赖

```bash
cd electron
npm install
cd ..
```

### 4. 安装 Python 依赖

```bash
cd backend

# 创建虚拟环境（推荐）
python -m venv venv

# Windows 激活虚拟环境
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

cd ..
```

### 5. 配置 API Key

首次运行时，在应用设置中输入你的 SiliconFlow API Key。

或者手动创建配置文件：

```bash
# Windows
copy backend\.env.example backend\.env

# 编辑 backend\.env，填入你的 API Key
SILICONFLOW_API_KEY=your_api_key_here
```

## 开发运行

```bash
# 启动开发环境（同时启动前端、后端、Electron）
npm run dev
```

这将同时启动：
- React 开发服务器 (http://localhost:5173)
- Python Flask 后端 (http://localhost:5000)
- Electron 桌面应用

## 打包构建

```bash
# 构建生产版本
npm run build

# 打包为可执行文件
npm run dist
```

打包后的文件位于 `dist` 目录：
- Windows: `视频字幕生成器 Setup 1.0.0.exe`
