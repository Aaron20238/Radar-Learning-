"""
Texas Hold'em Game Engine.
Manages game flow: dealing, betting rounds, showdown, and pot distribution.
"""
import time
from .card import Deck, Card
from .player import (
    Player, HumanPlayer, AIPlayer,
    ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE, ACTION_ALL_IN,
    ACTION_NAMES,
)
from .hand_evaluator import best_hand, HAND_NAMES

# Betting round names
ROUND_PRE_FLOP = "翻牌前（Pre-Flop）"
ROUND_FLOP = "翻牌（Flop）"
ROUND_TURN = "转牌（Turn）"
ROUND_RIVER = "河牌（River）"

SEPARATOR = "─" * 50


def _pause(delay: float = 0.8):
    """Brief pause for dramatic effect."""
    time.sleep(delay)


class Game:
    """
    Manages a single Texas Hold'em game session (multiple hands).
    """

    def __init__(
        self,
        human_player: HumanPlayer,
        ai_players: list[AIPlayer],
        small_blind: int = 10,
        big_blind: int = 20,
        tutorial_mode: bool = True,
    ):
        self.human = human_player
        self.ai_players = ai_players
        self.players: list[Player] = [human_player] + ai_players
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.tutorial_mode = tutorial_mode
        self.deck = Deck()
        self.community_cards: list[Card] = []
        self.pot = 0
        self.dealer_idx = 0   # Tracks dealer button position
        self.hand_number = 0

    # ──────────────────────────────────────────────────
    #  Public interface
    # ──────────────────────────────────────────────────

    def play_session(self):
        """Play hands until only one player has chips, or the human quits."""
        print(f"\n{'=' * 50}")
        print("  🃏  欢迎来到德州扑克！")
        print(f"  小盲注: {self.small_blind}  大盲注: {self.big_blind}")
        if self.tutorial_mode:
            print("  📚 教学模式已开启 — 每次操作都会显示提示")
        print(f"{'=' * 50}")

        while True:
            # Check if game is over
            active = [p for p in self.players if p.chips > 0]
            if len(active) < 2:
                winner = active[0] if active else None
                self._announce_session_winner(winner)
                break

            # Remove broke AI players
            self.players = [p for p in self.players if p.chips > 0 or isinstance(p, HumanPlayer)]

            if self.human.chips <= 0:
                print("\n  😢 你的筹码已经耗尽！游戏结束。")
                print(f"  总共完成了 {self.hand_number} 手牌。")
                break

            self.play_hand()

            # Ask to continue
            print(f"\n  你当前的筹码: {self.human.chips}")
            choice = input("\n  继续下一手？(y/n，直接回车默认继续): ").strip().lower()
            if choice == "n":
                print("\n  感谢游玩！再见！👋")
                break

    def play_hand(self):
        """Play a single hand of Texas Hold'em."""
        self.hand_number += 1
        print(f"\n{'=' * 50}")
        print(f"  第 {self.hand_number} 手牌")
        print(f"{'=' * 50}")

        self._reset_hand()
        self._post_blinds()
        self._deal_hole_cards()

        # Betting rounds
        for round_name, num_community in [
            (ROUND_PRE_FLOP, 0),
            (ROUND_FLOP, 3),
            (ROUND_TURN, 1),
            (ROUND_RIVER, 1),
        ]:
            if num_community > 0:
                self._deal_community(num_community, round_name)
            else:
                print(f"\n  ── {round_name} ──")

            if not self._betting_round(round_name):
                break  # All but one folded

            if len(self._active_players()) <= 1:
                break

        self._showdown()
        self._print_chip_counts()

    # ──────────────────────────────────────────────────
    #  Setup helpers
    # ──────────────────────────────────────────────────

    def _reset_hand(self):
        """Reset state for a new hand."""
        self.deck.reset()
        self.community_cards = []
        self.pot = 0
        for p in self.players:
            p.reset_for_hand()
        # Rotate dealer button
        self.dealer_idx = (self.dealer_idx + 1) % len(self.players)

    def _post_blinds(self):
        """Post small blind and big blind."""
        n = len(self.players)
        sb_idx = (self.dealer_idx + 1) % n
        bb_idx = (self.dealer_idx + 2) % n

        sb_player = self.players[sb_idx]
        bb_player = self.players[bb_idx]

        sb_amount = sb_player.place_bet(self.small_blind)
        bb_amount = bb_player.place_bet(self.big_blind)
        self.pot += sb_amount + bb_amount

        print(f"\n  🎯 盲注：{sb_player.name} 小盲 {sb_amount}  |  {bb_player.name} 大盲 {bb_amount}")

    def _deal_hole_cards(self):
        """Deal 2 hole cards to each player."""
        for p in self.players:
            p.receive_cards(self.deck.deal(2))

        # Show human's cards
        print(f"\n  🃏 发牌完毕！你的手牌: {' '.join(str(c) for c in self.human.hole_cards)}")
        if self.tutorial_mode:
            print("  💡 底牌只有你自己能看到。保护好你的手牌信息！")

    def _deal_community(self, count: int, round_name: str):
        """Burn and deal community cards."""
        self.deck.burn()
        new_cards = self.deck.deal(count)
        self.community_cards.extend(new_cards)

        print(f"\n  ── {round_name} ──")
        print(f"  公共牌: {' '.join(str(c) for c in self.community_cards)}")

        if self.tutorial_mode and count == 3:
            print("  💡 翻牌是三张公共牌，所有玩家都可以使用。")
        elif self.tutorial_mode and count == 1 and len(self.community_cards) == 4:
            print("  💡 转牌是第四张公共牌，你现在有6张牌可以组合。")
        elif self.tutorial_mode and count == 1 and len(self.community_cards) == 5:
            print("  💡 河牌是最后一张公共牌，这是最终的牌局！")

    # ──────────────────────────────────────────────────
    #  Betting round
    # ──────────────────────────────────────────────────

    def _betting_round(self, round_name: str) -> bool:
        """
        Run one betting round.
        Returns True if betting finished normally (≥2 active players remain),
        False if all but one player folded.
        """
        # Reset per-round bets
        for p in self.players:
            p.reset_for_round()

        # Pre-flop: big blind has already posted, so current bet = big blind
        if round_name == ROUND_PRE_FLOP:
            current_bet = self.big_blind
            # BB player has already bet the big blind
            n = len(self.players)
            bb_idx = (self.dealer_idx + 2) % n
            self.players[bb_idx].current_bet = self.big_blind
            # Starting player is UTG (one after BB)
            start_idx = (self.dealer_idx + 3) % n
        else:
            current_bet = 0
            # Start from small blind (first active after dealer)
            n = len(self.players)
            start_idx = (self.dealer_idx + 1) % n

        min_raise = self.big_blind
        acted = set()  # Players who have already acted and are settled

        order = self._action_order(start_idx)

        while True:
            all_settled = True
            for p in order:
                if not p.is_active():
                    continue
                # If player has matched current bet and has already acted, skip
                if p.current_bet == current_bet and p in acted:
                    continue
                all_settled = False

                call_amt = current_bet - p.current_bet
                game_state = {
                    "call_amount": call_amt,
                    "min_raise": min_raise,
                    "pot": self.pot,
                    "community_cards": self.community_cards,
                    "tutorial_mode": self.tutorial_mode,
                    "num_active_opponents": len(self._active_players()) - 1,
                }

                # AI announcement
                if isinstance(p, AIPlayer):
                    _pause(0.6)
                    print(f"\n  {p.name} 思考中...")
                    _pause(0.5)

                action, amount = p.decide_action(game_state)
                self._execute_action(p, action, amount, current_bet)

                # Update current_bet tracking
                if action in (ACTION_RAISE, ACTION_ALL_IN):
                    new_bet = p.current_bet
                    if new_bet > current_bet:
                        min_raise = new_bet - current_bet
                        current_bet = new_bet
                        acted = {p}  # Others must re-act
                    else:
                        acted.add(p)
                elif action == ACTION_FOLD:
                    acted.add(p)
                else:
                    acted.add(p)

                # Check if only one active player remains
                if len(self._active_players()) <= 1:
                    # Award pot to remaining player immediately
                    remaining = self._active_players()
                    if remaining:
                        self._award_pot([remaining[0]])
                    return False

            if all_settled or all(
                p.current_bet == current_bet or not p.is_active()
                for p in self.players
            ):
                break

        return True

    def _action_order(self, start_idx: int) -> list[Player]:
        """Return players in action order starting from start_idx."""
        n = len(self.players)
        return [self.players[(start_idx + i) % n] for i in range(n)]

    def _execute_action(self, player: Player, action: str, amount: int, current_bet: int):
        """Execute an action and update the pot."""
        call_needed = current_bet - player.current_bet

        if action == ACTION_FOLD:
            player.is_folded = True
            print(f"  ❌ {player.name} 弃牌")

        elif action == ACTION_CHECK:
            print(f"  ✅ {player.name} 过牌")

        elif action == ACTION_CALL:
            actual = player.place_bet(call_needed)
            self.pot += actual
            print(f"  📞 {player.name} 跟注 {actual}")

        elif action == ACTION_RAISE:
            # amount is the total raise-to value; we need to compute delta from current state
            total_to_put_in = amount - player.current_bet
            if total_to_put_in <= 0:
                total_to_put_in = call_needed
            actual = player.place_bet(total_to_put_in)
            self.pot += actual
            print(f"  💥 {player.name} 加注到 {player.current_bet}")

        elif action == ACTION_ALL_IN:
            actual = player.place_bet(player.chips)
            self.pot += actual
            print(f"  🔥 {player.name} 全押！（{player.total_bet_in_hand} 筹码）")

    # ──────────────────────────────────────────────────
    #  Showdown & pot distribution
    # ──────────────────────────────────────────────────

    def _showdown(self):
        """Evaluate remaining hands and award the pot."""
        active = [p for p in self.players if not p.is_folded]

        if len(active) == 1:
            return  # Already handled in betting

        print(f"\n  {'─' * 50}")
        print("  🎴 摊牌！")
        print(f"  公共牌: {' '.join(str(c) for c in self.community_cards)}")
        print()

        results = []
        for p in active:
            hand = best_hand(p.hole_cards, self.community_cards)
            print(f"  {p.name}: {' '.join(str(c) for c in p.hole_cards)}  →  {hand.name}")
            if self.tutorial_mode or isinstance(p, HumanPlayer):
                print(f"         最佳5张: {' '.join(str(c) for c in hand.cards)}")
            results.append((p, hand))

        # Find winner(s)
        best_result = max(r for _, r in results)
        winners = [p for p, r in results if r == best_result]

        self._award_pot(winners)

    def _award_pot(self, winners: list[Player]):
        """Distribute the pot to the winner(s)."""
        share = self.pot // len(winners)
        remainder = self.pot % len(winners)

        for i, w in enumerate(winners):
            gain = share + (remainder if i == 0 else 0)
            w.chips += gain

        if len(winners) == 1:
            print(f"\n  🏆 {winners[0].name} 赢得了底池 {self.pot} 筹码！")
        else:
            names = "、".join(w.name for w in winners)
            print(f"\n  🤝 平局！{names} 各赢得 {share} 筹码")

        self.pot = 0

    # ──────────────────────────────────────────────────
    #  Helpers
    # ──────────────────────────────────────────────────

    def _active_players(self) -> list[Player]:
        """Return players who have not folded."""
        return [p for p in self.players if not p.is_folded]

    def _print_chip_counts(self):
        """Print current chip counts for all players."""
        print(f"\n  {'─' * 50}")
        print("  💰 各玩家筹码：")
        for p in self.players:
            status = ""
            if p.chips <= 0:
                status = " [出局]"
            print(f"    {p.name}: {p.chips}{status}")

    def _announce_session_winner(self, winner: Player | None):
        """Announce the overall session winner."""
        print(f"\n{'=' * 50}")
        if winner:
            print(f"  🎉 游戏结束！{winner.name} 是最终赢家！")
            print(f"  最终筹码：{winner.chips}")
        else:
            print("  游戏结束！")
        print(f"{'=' * 50}")
