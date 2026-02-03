#!/bin/bash

echo "=========================================="
echo "视频字幕生成服务"
echo "=========================================="
echo ""

# 检查 Python 环境
echo "[1/3] 检查 Python 环境..."
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 Python3，请安装 Python 3.8+"
    exit 1
fi

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "[2/3] 创建虚拟环境..."
    python3 -m venv .venv
fi

echo "[2/3] 激活虚拟环境..."
source .venv/bin/activate

# 安装依赖
echo "[3/3] 检查依赖..."
if ! pip show flask &> /dev/null; then
    echo "安装依赖包..."
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
fi

echo ""
echo "=========================================="
echo "启动服务..."
echo "API 地址: http://localhost:5000"
echo "WebSocket: ws://localhost:5000"
echo "=========================================="
echo ""

python app.py
