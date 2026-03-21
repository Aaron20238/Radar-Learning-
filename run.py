#!/usr/bin/env python3
"""
便捷启动脚本 — 在项目根目录直接运行德州扑克游戏。

用法：
    python run.py
"""
import sys
import os

# 确保无论从哪个目录运行，都能正确找到 texas_holdem 包
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from texas_holdem.main import main_menu

if __name__ == "__main__":
    main_menu()
