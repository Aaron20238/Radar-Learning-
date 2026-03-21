"""
Player classes for Texas Hold'em Poker.
Includes human player and AI bots of different difficulty levels.
"""
import random
from .card import Card
from .hand_evaluator import (
    best_hand, hand_strength_percent,
    HIGH_CARD, ONE_PAIR, TWO_PAIR, THREE_OF_A_KIND,
)

# Player actions
ACTION_FOLD = "fold"
ACTION_CHECK = "check"
ACTION_CALL = "call"
ACTION_RAISE = "raise"
ACTION_ALL_IN = "all_in"

ACTION_NAMES = {
    ACTION_FOLD: "弃牌（Fold）",
    ACTION_CHECK: "过牌（Check）",
    ACTION_CALL: "跟注（Call）",
    ACTION_RAISE: "加注（Raise）",
    ACTION_ALL_IN: "全押（All-In）",
}

# AI difficulty levels
DIFFICULTY_EASY = "easy"
DIFFICULTY_MEDIUM = "medium"
DIFFICULTY_HARD = "hard"

DIFFICULTY_NAMES = {
    DIFFICULTY_EASY: "新手 AI",
    DIFFICULTY_MEDIUM: "中级 AI",
    DIFFICULTY_HARD: "高手 AI",
}


class Player:
    """Base class for all players."""

    def __init__(self, name: str, chips: int = 1000):
        self.name = name
        self.chips = chips
        self.hole_cards: list[Card] = []
        self.current_bet = 0       # Amount bet in current betting round
        self.total_bet_in_hand = 0  # Total amount bet in this hand (for side-pot logic)
        self.is_folded = False
        self.is_all_in = False

    def reset_for_hand(self):
        """Reset per-hand state."""
        self.hole_cards = []
        self.current_bet = 0
        self.total_bet_in_hand = 0
        self.is_folded = False
        self.is_all_in = False

    def reset_for_round(self):
        """Reset per-betting-round state."""
        self.current_bet = 0

    def receive_cards(self, cards: list[Card]):
        self.hole_cards.extend(cards)

    def place_bet(self, amount: int) -> int:
        """Place a bet of `amount`. Returns actual amount placed (capped by chips)."""
        actual = min(amount, self.chips)
        self.chips -= actual
        self.current_bet += actual
        self.total_bet_in_hand += actual
        if self.chips == 0:
            self.is_all_in = True
        return actual

    def is_active(self) -> bool:
        """True if the player can still act (not folded and not all-in)."""
        return not self.is_folded and not self.is_all_in

    def __str__(self) -> str:
        return self.name


class HumanPlayer(Player):
    """Human-controlled player that prompts for input."""

    def __init__(self, name: str = "玩家", chips: int = 1000):
        super().__init__(name, chips)

    def decide_action(self, game_state: dict) -> tuple[str, int]:
        """
        Prompt the human player for their action.
        Returns (action, amount).
        `game_state` contains: call_amount, min_raise, pot, community_cards, tutorial_mode
        """
        call_amount = game_state["call_amount"]
        min_raise = game_state["min_raise"]
        pot = game_state["pot"]
        tutorial_mode = game_state.get("tutorial_mode", False)

        print(f"\n  🃏 你的手牌: {' '.join(str(c) for c in self.hole_cards)}")
        print(f"  💰 你的筹码: {self.chips}  | 底池: {pot}")

        if tutorial_mode:
            self._show_tutorial_hints(game_state)

        # Build available actions
        options = []
        if call_amount == 0:
            options.append(ACTION_CHECK)
        else:
            options.append(ACTION_FOLD)
            if self.chips >= call_amount:
                options.append(ACTION_CALL)

        if self.chips > call_amount and self.chips >= min_raise + call_amount:
            options.append(ACTION_RAISE)

        if self.chips > 0:
            options.append(ACTION_ALL_IN)

        print("\n  可选操作:")
        for i, action in enumerate(options, 1):
            extra = ""
            if action == ACTION_CALL:
                extra = f"（跟注 {call_amount} 筹码）"
            elif action == ACTION_RAISE:
                extra = f"（最小加注到 {call_amount + min_raise} 筹码）"
            elif action == ACTION_ALL_IN:
                extra = f"（押上全部 {self.chips} 筹码）"
            print(f"  [{i}] {ACTION_NAMES[action]} {extra}")

        while True:
            try:
                choice_str = input("  请选择操作 (输入数字): ").strip()
                if not choice_str.isdigit():
                    print("  ❌ 请输入有效数字")
                    continue
                choice = int(choice_str) - 1
                if choice < 0 or choice >= len(options):
                    print("  ❌ 无效选项，请重新选择")
                    continue
                action = options[choice]

                if action == ACTION_RAISE:
                    amount = self._prompt_raise(call_amount, min_raise)
                    return action, amount
                elif action == ACTION_ALL_IN:
                    return action, self.chips
                elif action == ACTION_CALL:
                    return action, call_amount
                else:
                    return action, 0
            except (ValueError, KeyboardInterrupt):
                print("\n  ❌ 请输入有效数字")

    def _prompt_raise(self, call_amount: int, min_raise: int) -> int:
        """Prompt the user for a raise amount."""
        minimum = call_amount + min_raise
        maximum = self.chips
        while True:
            try:
                raw = input(f"  请输入加注总额 (最少 {minimum}，最多 {maximum}): ").strip()
                amount = int(raw)
                if amount < minimum:
                    print(f"  ❌ 加注至少需要 {minimum} 筹码")
                elif amount > maximum:
                    print(f"  ❌ 你只有 {maximum} 筹码")
                else:
                    return amount
            except ValueError:
                print("  ❌ 请输入有效数字")

    def _show_tutorial_hints(self, game_state: dict):
        """Show beginner hints during tutorial mode."""
        community_cards = game_state.get("community_cards", [])
        call_amount = game_state["call_amount"]
        pot = game_state["pot"]
        num_opponents = game_state.get("num_active_opponents", 1)

        print("\n  ━━━━━━━━━━━━━ 📚 教学提示 ━━━━━━━━━━━━━")
        if community_cards:
            try:
                result = best_hand(self.hole_cards, community_cards)
                print(f"  当前最佳牌型: {result.name} — {result.description}")
                print(f"  最佳5张牌: {' '.join(str(c) for c in result.cards)}")

                if len(community_cards) < 5:
                    # Show outs hint
                    from .hand_evaluator import get_outs_hint
                    hint = get_outs_hint(self.hole_cards, community_cards)
                    if hint:
                        print(hint, end="")

                # Show win probability estimate
                win_pct = hand_strength_percent(
                    self.hole_cards, community_cards, num_opponents
                )
                bar = self._make_progress_bar(win_pct)
                print(f"  胜率估算: {bar} {win_pct:.1%}")
            except Exception:
                pass
        else:
            print("  等待翻牌 — 保持耐心，观察对手行为！")
            self._explain_starting_hand()

        if call_amount > 0 and pot > 0:
            pot_odds = call_amount / (pot + call_amount)
            print(f"  底池赔率: 你需要投入 {call_amount}，底池共 {pot}，赔率约 1:{pot / call_amount:.1f}")
            print(f"  （如果你的胜率高于 {pot_odds:.1%}，从数学上讲跟注是合算的）")

        print("  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    def _explain_starting_hand(self):
        """Give a quick rating of the starting hand quality."""
        if len(self.hole_cards) < 2:
            return
        c1, c2 = self.hole_cards
        v1, v2 = sorted([c1.value, c2.value], reverse=True)

        # Pocket pair
        if c1.value == c2.value:
            if v1 >= 10:
                print(f"  起手牌评级: ⭐⭐⭐ 高对子（{c1.rank}{c2.rank}），非常强！")
            elif v1 >= 7:
                print(f"  起手牌评级: ⭐⭐ 中对子（{c1.rank}{c2.rank}），较强")
            else:
                print(f"  起手牌评级: ⭐ 小对子（{c1.rank}{c2.rank}），一般")
            return

        suited = c1.suit == c2.suit
        gap = v1 - v2
        suffix = "同花" if suited else ""

        if v1 == 14 and v2 >= 10:
            print(f"  起手牌评级: ⭐⭐⭐ A大牌 {suffix}，顶级起手牌！")
        elif v1 >= 12 and v2 >= 10:
            print(f"  起手牌评级: ⭐⭐⭐ 大牌 {suffix}，很强")
        elif v1 == 14 and gap <= 3 and suited:
            print(f"  起手牌评级: ⭐⭐ A同花连牌，有潜力")
        elif v1 >= 10 and gap <= 2 and suited:
            print(f"  起手牌评级: ⭐⭐ 同花连牌，有顺子/同花潜力")
        elif gap <= 1 and v1 >= 8:
            print(f"  起手牌评级: ⭐ 连牌，有顺子潜力")
        else:
            print(f"  起手牌评级: 一般起手牌，谨慎行事")

    @staticmethod
    def _make_progress_bar(pct: float, width: int = 20) -> str:
        filled = int(pct * width)
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}]"


class AIPlayer(Player):
    """AI-controlled player with configurable difficulty."""

    def __init__(self, name: str, chips: int = 1000, difficulty: str = DIFFICULTY_EASY):
        super().__init__(name, chips)
        self.difficulty = difficulty

    def decide_action(self, game_state: dict) -> tuple[str, int]:
        """
        Decide an action based on difficulty level.
        Returns (action, amount).
        """
        call_amount = game_state["call_amount"]
        community_cards = game_state.get("community_cards", [])
        pot = game_state["pot"]
        num_opponents = game_state.get("num_active_opponents", 1)

        if self.difficulty == DIFFICULTY_EASY:
            return self._easy_strategy(call_amount, community_cards, pot)
        elif self.difficulty == DIFFICULTY_MEDIUM:
            return self._medium_strategy(call_amount, community_cards, pot, num_opponents)
        else:
            return self._hard_strategy(call_amount, community_cards, pot, num_opponents)

    def _hand_rank(self, community_cards: list[Card]) -> int:
        """Get the current hand rank (or estimate pre-flop)."""
        if len(community_cards) == 0:
            # Pre-flop: estimate from hole cards
            c1, c2 = self.hole_cards
            if c1.value == c2.value:
                return ONE_PAIR if c1.value < 10 else TWO_PAIR
            return HIGH_CARD
        try:
            return best_hand(self.hole_cards, community_cards).rank
        except Exception:
            return HIGH_CARD

    def _easy_strategy(self, call_amount: int, community_cards: list[Card], pot: int) -> tuple[str, int]:
        """Simple random strategy with slight bias toward good hands."""
        hand_rank = self._hand_rank(community_cards)
        r = random.random()

        if hand_rank >= THREE_OF_A_KIND:
            # Strong hand - bet/raise
            if r < 0.7:
                raise_to = call_amount + max(10, pot // 3)
                return ACTION_RAISE, min(raise_to, self.chips + call_amount)
            return ACTION_CALL, call_amount
        elif hand_rank >= ONE_PAIR:
            # Medium hand - mostly call
            if call_amount == 0:
                return ACTION_CHECK, 0
            if r < 0.6:
                return ACTION_CALL, call_amount
            return ACTION_FOLD, 0
        else:
            # Weak hand - mostly fold/check
            if call_amount == 0:
                return ACTION_CHECK, 0
            if r < 0.3 and call_amount <= pot // 4:
                return ACTION_CALL, call_amount
            return ACTION_FOLD, 0

    def _medium_strategy(self, call_amount: int, community_cards: list[Card],
                         pot: int, num_opponents: int) -> tuple[str, int]:
        """Strategy based on hand strength and pot odds."""
        if len(community_cards) >= 3:
            win_pct = hand_strength_percent(self.hole_cards, community_cards,
                                            num_opponents, simulations=200)
        else:
            hand_rank = self._hand_rank(community_cards)
            win_pct = 0.3 + (hand_rank - 1) * 0.08

        pot_odds = call_amount / (pot + call_amount) if (pot + call_amount) > 0 else 0

        if win_pct > 0.65:
            # Very strong - raise
            raise_to = call_amount + max(20, pot // 2)
            return ACTION_RAISE, min(raise_to, self.chips + call_amount)
        elif win_pct > pot_odds + 0.1:
            # Profitable call
            if call_amount == 0:
                if win_pct > 0.55:
                    raise_to = max(20, pot // 3)
                    return ACTION_RAISE, min(raise_to, self.chips)
                return ACTION_CHECK, 0
            return ACTION_CALL, call_amount
        else:
            if call_amount == 0:
                return ACTION_CHECK, 0
            return ACTION_FOLD, 0

    def _hard_strategy(self, call_amount: int, community_cards: list[Card],
                       pot: int, num_opponents: int) -> tuple[str, int]:
        """Advanced strategy with bluffing, position awareness, and aggression."""
        if len(community_cards) >= 3:
            win_pct = hand_strength_percent(self.hole_cards, community_cards,
                                            num_opponents, simulations=300)
        else:
            hand_rank = self._hand_rank(community_cards)
            win_pct = 0.25 + (hand_rank - 1) * 0.1

        pot_odds = call_amount / (pot + call_amount) if (pot + call_amount) > 0 else 0
        r = random.random()

        # Bluff occasionally (~15% of the time on weak hands)
        if win_pct < 0.3 and r < 0.15 and self.chips > call_amount * 2:
            bluff_amount = call_amount + max(pot // 2, 30)
            return ACTION_RAISE, min(bluff_amount, self.chips + call_amount)

        if win_pct > 0.7:
            # Monster hand - slow play sometimes to trap
            if r < 0.2 and call_amount > 0:
                return ACTION_CALL, call_amount  # slow play
            raise_to = call_amount + max(30, int(pot * 0.75))
            return ACTION_RAISE, min(raise_to, self.chips + call_amount)
        elif win_pct > pot_odds + 0.05:
            if call_amount == 0:
                if win_pct > 0.5 and r < 0.7:
                    raise_to = max(20, pot // 3)
                    return ACTION_RAISE, min(raise_to, self.chips)
                return ACTION_CHECK, 0
            return ACTION_CALL, call_amount
        else:
            if call_amount == 0:
                return ACTION_CHECK, 0
            return ACTION_FOLD, 0
