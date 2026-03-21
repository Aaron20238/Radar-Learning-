#!/usr/bin/env python3
"""
便捷启动脚本 — 在项目根目录运行，可选择德州扑克游戏或智能合同审阅助手。

用法：
    python run.py
"""
import sys
import os

# 确保无论从哪个目录运行，都能正确找到各子包
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    print("\n════════════════════════════════════════════")
    print("  请选择要启动的程序：")
    print("  [1] 🃏  德州扑克游戏")
    print("  [2] ⚖️  智能合同审阅助手")
    print("  [0] 退出")
    print("════════════════════════════════════════════")

    while True:
        choice = input("  请选择 (0-2): ").strip()
        if choice == "1":
            from texas_holdem.main import main_menu
            main_menu()
            break
        elif choice == "2":
            from contract_review.main import main as contract_main
            contract_main()
            break
        elif choice == "0":
            print("  再见！👋")
            break
        else:
            print("  ❌ 请输入 0、1 或 2")


if __name__ == "__main__":
    main()
