#!/bin/bash

# JavSP 跨平台构建脚本
# 支持 macOS、Linux 和 Windows (通过 WSL 或 Git Bash)

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目信息
PROJECT_NAME="JavSP"
VERSION="2.8.0"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  JavSP 跨平台构建脚本 v${VERSION}${NC}"
echo -e "${BLUE}========================================${NC}"

# 检测操作系统
OS=$(uname -s)
case "$OS" in
    Darwin*)
        PLATFORM="macos"
        ARCH=$(uname -m)
        ;;
    Linux*)
        PLATFORM="linux"
        ARCH=$(uname -m)
        ;;
    CYGWIN*|MINGW*|MSYS*)
        PLATFORM="windows"
        ARCH=$(uname -m)
        ;;
    *)
        echo -e "${RED}不支持的操作系统: $OS${NC}"
        exit 1
        ;;
esac

echo -e "${GREEN}检测到平台: $PLATFORM ($ARCH)${NC}"

# 检查 Python 版本
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
echo -e "${GREEN}Python 版本: $PYTHON_VERSION${NC}"

# 检查依赖
check_dependency() {
    if ! command -v "$1" &> /dev/null; then
        echo -e "${RED}错误: 未找到 $1${NC}"
        return 1
    fi
    return 0
}

echo -e "${YELLOW}检查构建依赖...${NC}"

# 检查 Python
if ! check_dependency python3; then
    echo -e "${RED}请先安装 Python 3.8+${NC}"
    exit 1
fi

# 检查 pip
if ! check_dependency pip3; then
    echo -e "${RED}请先安装 pip3${NC}"
    exit 1
fi

# 安装构建依赖
echo -e "${YELLOW}安装构建依赖...${NC}"
pip3 install --upgrade pip
pip3 install \
    pydantic>=2.0.0 \
    confz>=2.0.0 \
    requests>=2.28.0 \
    colorama>=0.4.0 \
    tqdm>=4.64.0 \
    Pillow>=9.0.0 \
    pydantic-extra-types>=2.0.0 \
    pendulum>=2.1.0 \
    cloudscraper>=1.2.0 \
    cx-Logging>=3.0.0 \
    lxml>=4.9.0 \
    beautifulsoup4>=4.11.0 \
    pretty_errors>=1.2.0 \
    cx-Freeze>=6.15.0

# 创建构建目录
BUILD_DIR="build/$PLATFORM-$ARCH"
DIST_DIR="dist/$PLATFORM-$ARCH"
echo -e "${YELLOW}构建目录: $BUILD_DIR${NC}"
echo -e "${YELLOW}输出目录: $DIST_DIR${NC}"

# 清理之前的构建
echo -e "${YELLOW}清理之前的构建...${NC}"
rm -rf build/ dist/ *.egg-info/

# 构建可执行文件
echo -e "${YELLOW}开始构建可执行文件...${NC}"
python3 setup.py build

# 复制可执行文件到输出目录
mkdir -p "$DIST_DIR"
if [ "$PLATFORM" = "macos" ]; then
    EXECUTABLE_PATH="build/exe.macosx-$ARCH-3.*/javsp"
elif [ "$PLATFORM" = "linux" ]; then
    EXECUTABLE_PATH="build/exe.linux-$ARCH-3.*/javsp"
elif [ "$PLATFORM" = "windows" ]; then
    EXECUTABLE_PATH="build/exe.win-*/javsp.exe"
fi

# 查找并复制可执行文件
FOUND_EXECUTABLE=$(find build -name "javsp*" -type f -executable 2>/dev/null | head -1)
if [ -n "$FOUND_EXECUTABLE" ]; then
    cp -r "$(dirname "$FOUND_EXECUTABLE")"/* "$DIST_DIR/"
    echo -e "${GREEN}可执行文件已复制到: $DIST_DIR${NC}"
else
    echo -e "${RED}未找到可执行文件${NC}"
    exit 1
fi

# 创建发布包
echo -e "${YELLOW}创建发布包...${NC}"
PACKAGE_NAME="${PROJECT_NAME}-${VERSION}-${PLATFORM}-${ARCH}"
RELEASE_DIR="release"

mkdir -p "$RELEASE_DIR"

# 创建 zip 包
if command -v zip &> /dev/null; then
    cd "$DIST_DIR"
    zip -r "../${RELEASE_DIR}/${PACKAGE_NAME}.zip" .
    cd ../..
    echo -e "${GREEN}发布包已创建: ${RELEASE_DIR}/${PACKAGE_NAME}.zip${NC}"
fi

# 创建 tar.gz 包
if command -v tar &> /dev/null; then
    tar -czf "${RELEASE_DIR}/${PACKAGE_NAME}.tar.gz" -C "$DIST_DIR" .
    echo -e "${GREEN}发布包已创建: ${RELEASE_DIR}/${PACKAGE_NAME}.tar.gz${NC}"
fi

# 显示构建信息
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}构建完成!${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "项目名称: $PROJECT_NAME"
echo -e "版本: $VERSION"
echo -e "平台: $PLATFORM ($ARCH)"
echo -e "Python 版本: $PYTHON_VERSION"
echo -e "可执行文件: $DIST_DIR/javsp"
echo -e "发布包: $RELEASE_DIR/"
echo -e ""

# 显示使用说明
echo -e "${YELLOW}使用说明:${NC}"
echo -e "1. 将可执行文件复制到目标机器"
echo -e "2. 确保 config.yml 文件在可执行文件同目录"
echo -e "3. 确保 data/ 和 image/ 目录在可执行文件同目录"
echo -e "4. 运行 ./javsp 开始使用"
echo -e ""

if [ "$PLATFORM" = "macos" ]; then
    echo -e "${YELLOW}macOS 特殊说明:${NC}"
    echo -e "- 首次运行可能需要在系统偏好设置中允许运行"
    echo -e "- 如果遇到安全限制，请运行: xattr -d com.apple.quarantine javsp"
    echo -e ""
fi

echo -e "${GREEN}构建脚本执行完成!${NC}"