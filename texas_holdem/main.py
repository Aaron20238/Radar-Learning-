"""
Main entry point for the Texas Hold'em Poker game.
Provides a menu-driven interface with difficulty selection and tutorial mode.
"""
import sys
import os

# Allow running as `python main.py` from the texas_holdem directory or from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from texas_holdem.player import (
    HumanPlayer, AIPlayer,
    DIFFICULTY_EASY, DIFFICULTY_MEDIUM, DIFFICULTY_HARD, DIFFICULTY_NAMES,
)
from texas_holdem.game import Game
from texas_holdem.tutorial import show_tutorial_menu, quick_quiz

BANNER = r"""
  ████████╗███████╗██╗  ██╗ █████╗ ███████╗
     ██╔══╝██╔════╝╚██╗██╔╝██╔══██╗██╔════╝
     ██║   █████╗   ╚███╔╝ ███████║███████╗
     ██║   ██╔══╝   ██╔██╗ ██╔══██║╚════██║
     ██║   ███████╗██╔╝ ██╗██║  ██║███████║
     ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝

  ██╗  ██╗ ██████╗ ██╗     ██████╗ ███████╗███╗   ███╗
  ██║  ██║██╔═══██╗██║     ██╔══██╗██╔════╝████╗ ████║
  ███████║██║   ██║██║     ██║  ██║█████╗  ██╔████╔██║
  ██╔══██║██║   ██║██║     ██║  ██║██╔══╝  ██║╚██╔╝██║
  ██║  ██║╚██████╔╝███████╗██████╔╝███████╗██║ ╚═╝ ██║
  ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═════╝ ╚══════╝╚═╝     ╚═╝

          🃏  德州扑克  — 从新手到高手  🃏
"""

DIFFICULTY_DESCRIPTIONS = {
    DIFFICULTY_EASY: "随机出牌，偶尔犯错，适合完全新手",
    DIFFICULTY_MEDIUM: "基于牌力和底池赔率决策，有一定策略",
    DIFFICULTY_HARD: "综合胜率、赔率、诈唬，模拟真实高手",
}


def print_banner():
    print(BANNER)


def select_difficulty() -> str:
    """Prompt the user to select AI difficulty."""
    print("\n  选择 AI 难度：")
    levels = [DIFFICULTY_EASY, DIFFICULTY_MEDIUM, DIFFICULTY_HARD]
    for i, d in enumerate(levels, 1):
        print(f"  [{i}] {DIFFICULTY_NAMES[d]} — {DIFFICULTY_DESCRIPTIONS[d]}")

    while True:
        choice = input("\n  请选择难度（1-3，默认为1）: ").strip()
        if choice == "" or choice == "1":
            return DIFFICULTY_EASY
        elif choice == "2":
            return DIFFICULTY_MEDIUM
        elif choice == "3":
            return DIFFICULTY_HARD
        else:
            print("  ❌ 请输入 1、2 或 3")


def select_num_opponents() -> int:
    """Prompt the user for number of AI opponents."""
    print("\n  选择 AI 对手数量（1-4）：")
    while True:
        choice = input("  请输入对手数量（默认为 2）: ").strip()
        if choice == "":
            return 2
        if choice.isdigit() and 1 <= int(choice) <= 4:
            return int(choice)
        print("  ❌ 请输入 1 到 4 之间的数字")


def select_starting_chips() -> int:
    """Prompt the user for starting chip amount."""
    print("\n  设置起始筹码（建议 500-5000）：")
    while True:
        choice = input("  请输入起始筹码数量（默认为 1000）: ").strip()
        if choice == "":
            return 1000
        if choice.isdigit() and 100 <= int(choice) <= 100000:
            return int(choice)
        print("  ❌ 请输入 100 到 100000 之间的数字")


def select_blinds() -> tuple[int, int]:
    """Prompt for blind levels."""
    print("\n  设置盲注级别：")
    options = [
        (5, 10, "微额：小盲5 / 大盲10"),
        (10, 20, "低额：小盲10 / 大盲20（推荐）"),
        (25, 50, "中额：小盲25 / 大盲50"),
        (50, 100, "高额：小盲50 / 大盲100"),
    ]
    for i, (sb, bb, desc) in enumerate(options, 1):
        print(f"  [{i}] {desc}")

    while True:
        choice = input("  请选择盲注级别（默认为2）: ").strip()
        if choice == "" or choice == "2":
            return 10, 20
        if choice.isdigit() and 1 <= int(choice) <= 4:
            idx = int(choice) - 1
            return options[idx][0], options[idx][1]
        print("  ❌ 请输入 1 到 4 之间的数字")


def setup_game() -> Game:
    """Interactively set up a new game and return a configured Game instance."""
    print("\n" + "═" * 50)
    print("  ⚙️  游戏设置")
    print("═" * 50)

    # Player name
    name = input("\n  请输入你的名字（默认：玩家）: ").strip() or "玩家"

    # Tutorial mode
    tutorial_input = input("  开启教学模式？(y/n，默认 y): ").strip().lower()
    tutorial_mode = tutorial_input != "n"

    # Game settings
    difficulty = select_difficulty()
    num_opponents = select_num_opponents()
    starting_chips = select_starting_chips()
    small_blind, big_blind = select_blinds()

    # Create players
    human = HumanPlayer(name=name, chips=starting_chips)

    ai_names = ["Alice", "Bob", "Charlie", "Diana"]
    ai_players = [
        AIPlayer(name=ai_names[i], chips=starting_chips, difficulty=difficulty)
        for i in range(num_opponents)
    ]

    game = Game(
        human_player=human,
        ai_players=ai_players,
        small_blind=small_blind,
        big_blind=big_blind,
        tutorial_mode=tutorial_mode,
    )

    print(f"\n  ✅ 游戏设置完成！")
    print(f"     玩家: {name}  筹码: {starting_chips}")
    print(f"     AI对手: {num_opponents} 位 ({DIFFICULTY_NAMES[difficulty]})")
    print(f"     盲注: {small_blind}/{big_blind}")
    print(f"     教学模式: {'开启' if tutorial_mode else '关闭'}")

    return game


def main_menu():
    """Display the main menu and handle user choices."""
    print_banner()

    while True:
        print("\n" + "═" * 50)
        print("  🎮 主菜单")
        print("═" * 50)
        print("  [1] 开始游戏")
        print("  [2] 学习教程")
        print("  [3] 快速测验")
        print("  [4] 查看牌型速查表")
        print("  [0] 退出")
        print("═" * 50)

        choice = input("  请选择 (0-4): ").strip()

        if choice == "1":
            game = setup_game()
            input("\n  按回车键开始游戏...")
            game.play_session()

        elif choice == "2":
            show_tutorial_menu()

        elif choice == "3":
            quick_quiz()

        elif choice == "4":
            from texas_holdem.tutorial import HAND_RANKINGS_TEXT
            print(HAND_RANKINGS_TEXT)
            input("  按回车键继续...")

        elif choice == "0":
            print("\n  感谢游玩德州扑克！再见！👋\n")
            break

        else:
            print("  ❌ 无效选项，请输入 0-4")


if __name__ == "__main__":
    main_menu()
