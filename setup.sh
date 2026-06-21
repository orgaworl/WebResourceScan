#!/bin/bash
# 安装依赖并初始化环境
set -e

echo "==> 安装 Python 依赖..."
uv sync

echo "==> 安装 Playwright Chromium 浏览器..."
uv run playwright install chromium

echo "==> 创建数据目录..."
mkdir -p data

echo "✓ 初始化完成。运行前请设置 ANTHROPIC_API_KEY 环境变量。"
