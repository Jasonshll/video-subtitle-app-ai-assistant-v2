@echo off
chcp 65001 >nul
echo ==========================================
echo 视频字幕生成服务
echo ==========================================
echo.

REM 检查 Python 环境
echo [1/3] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Python，请安装 Python 3.8+
    pause
    exit /b 1
)

REM 检查虚拟环境
if not exist .venv (
    echo [2/3] 创建虚拟环境...
    python -m venv .venv
)

echo [2/3] 激活虚拟环境...
call .venv\Scripts\activate.bat

REM 安装依赖
echo [3/3] 检查依赖...
if not exist .venv\Lib\site-packages\flask (
    echo 安装依赖包...
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
)

echo.
echo ==========================================
echo 启动服务...
echo API 地址: http://localhost:5000
echo WebSocket: ws://localhost:5000
echo ==========================================
echo.

python app.py

pause
