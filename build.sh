#!/bin/bash
# TrollRestore macOS 一键打包脚本
# 在 Mac 终端执行: chmod +x build.sh && ./build.sh

set -e

echo "========================================"
echo " TrollRestore macOS 构建脚本"
echo "========================================"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 需要 Python 3.9+，请先安装: brew install python@3.11"
    exit 1
fi

echo "✅ Python: $(python3 --version)"

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi
source venv/bin/activate

# 安装依赖
echo "📦 安装依赖..."
pip install --upgrade pip
pip install PyQt5 qasync pymobiledevice3 packaging requests pyinstaller

# 检查必要文件
if [ ! -f "PersistenceHelper_Embedded" ]; then
    echo "❌ 缺少 PersistenceHelper_Embedded，请从 Windows 版目录复制"
    exit 1
fi
if [ ! -d "sparserestore" ]; then
    echo "❌ 缺少 sparserestore/ 目录，请从 Windows 版目录复制"
    exit 1
fi

echo "✅ 所有文件就绪"

# 打包
echo "🔨 开始打包..."
pyinstaller --onedir --windowed \
    --name "TrollRestore" \
    --add-data "sparserestore:sparserestore" \
    --add-data "PersistenceHelper_Embedded:." \
    --osx-bundle-identifier "com.trollrestore.app" \
    trollrestore_mac.py 2>&1 | tail -20

# 检查产物
if [ -d "dist/TrollRestore.app" ]; then
    echo ""
    echo "========================================"
    echo " ✅ 打包成功！"
    echo " App 位置: $(pwd)/dist/TrollRestore.app"
    echo "========================================"
    open dist/
else
    echo "❌ 打包失败，检查上方错误信息"
    exit 1
fi
