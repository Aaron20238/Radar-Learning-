"""
Tests for the Texas Hold'em Poker game.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from texas_holdem.card import Card, Deck, SUITS, RANKS
from texas_holdem.hand_evaluator import (
    best_hand, _evaluate_five,
    HIGH_CARD, ONE_PAIR, TWO_PAIR, THREE_OF_A_KIND,
    STRAIGHT, FLUSH, FULL_HOUSE, FOUR_OF_A_KIND,
    STRAIGHT_FLUSH, ROYAL_FLUSH,
)
from texas_holdem.player import (
    HumanPlayer, AIPlayer,
    DIFFICULTY_EASY, DIFFICULTY_MEDIUM, DIFFICULTY_HARD,
    ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE, ACTION_ALL_IN,
)


# ─────────────────────────────────────────────────────
#  Card & Deck
# ─────────────────────────────────────────────────────

class TestCard:
    def test_card_creation(self):
        c = Card("A", "♠")
        assert c.rank == "A"
        assert c.suit == "♠"
        assert c.value == 14

    def test_card_str(self):
        c = Card("K", "♥")
        assert str(c) == "♥K"

    def test_card_comparison(self):
        low = Card("2", "♠")
        high = Card("A", "♥")
        assert low < high
        assert high > low
        assert not (low == high)

    def test_invalid_rank(self):
        with pytest.raises(ValueError):
            Card("1", "♠")

    def test_invalid_suit(self):
        with pytest.raises(ValueError):
            Card("A", "X")

    def test_card_equality(self):
        c1 = Card("A", "♠")
        c2 = Card("A", "♠")
        assert c1 == c2

    def test_two_value(self):
        assert Card("2", "♣").value == 2

    def test_ace_value(self):
        assert Card("A", "♦").value == 14


class TestDeck:
    def test_deck_has_52_cards(self):
        d = Deck()
        assert len(d) == 52

    def test_all_unique(self):
        d = Deck()
        cards_str = [str(c) for c in d.cards]
        assert len(cards_str) == len(set(cards_str))

    def test_deal_removes_cards(self):
        d = Deck()
        d.deal(5)
        assert len(d) == 47

    def test_deal_one(self):
        d = Deck()
        c = d.deal_one()
        assert isinstance(c, Card)
        assert len(d) == 51

    def test_burn(self):
        d = Deck()
        d.burn()
        assert len(d) == 51

    def test_not_enough_cards(self):
        d = Deck()
        with pytest.raises(ValueError):
            d.deal(53)

    def test_reset_restores_52(self):
        d = Deck()
        d.deal(10)
        d.reset()
        assert len(d) == 52


# ─────────────────────────────────────────────────────
#  Hand Evaluator
# ─────────────────────────────────────────────────────

def make_cards(*specs) -> list[Card]:
    """Helper: make cards from ('rank', 'suit') tuples."""
    return [Card(r, s) for r, s in specs]


class TestHandEvaluator:
    def test_royal_flush(self):
        cards = make_cards(("A","♠"),("K","♠"),("Q","♠"),("J","♠"),("10","♠"))
        result = _evaluate_five(cards)
        assert result.rank == ROYAL_FLUSH

    def test_straight_flush(self):
        cards = make_cards(("9","♥"),("8","♥"),("7","♥"),("6","♥"),("5","♥"))
        result = _evaluate_five(cards)
        assert result.rank == STRAIGHT_FLUSH

    def test_four_of_a_kind(self):
        cards = make_cards(("K","♠"),("K","♥"),("K","♦"),("K","♣"),("2","♠"))
        result = _evaluate_five(cards)
        assert result.rank == FOUR_OF_A_KIND

    def test_full_house(self):
        cards = make_cards(("A","♠"),("A","♥"),("A","♦"),("K","♣"),("K","♠"))
        result = _evaluate_five(cards)
        assert result.rank == FULL_HOUSE

    def test_flush(self):
        cards = make_cards(("A","♣"),("J","♣"),("9","♣"),("5","♣"),("2","♣"))
        result = _evaluate_five(cards)
        assert result.rank == FLUSH

    def test_straight(self):
        cards = make_cards(("8","♠"),("7","♥"),("6","♦"),("5","♣"),("4","♠"))
        result = _evaluate_five(cards)
        assert result.rank == STRAIGHT

    def test_wheel_straight(self):
        cards = make_cards(("A","♠"),("2","♥"),("3","♦"),("4","♣"),("5","♠"))
        result = _evaluate_five(cards)
        assert result.rank == STRAIGHT
        assert result.tiebreakers[0] == 5  # 5-high straight

    def test_three_of_a_kind(self):
        cards = make_cards(("J","♠"),("J","♥"),("J","♦"),("8","♣"),("3","♠"))
        result = _evaluate_five(cards)
        assert result.rank == THREE_OF_A_KIND

    def test_two_pair(self):
        cards = make_cards(("A","♠"),("A","♥"),("K","♦"),("K","♣"),("7","♠"))
        result = _evaluate_five(cards)
        assert result.rank == TWO_PAIR

    def test_one_pair(self):
        cards = make_cards(("Q","♠"),("Q","♥"),("9","♦"),("6","♣"),("2","♠"))
        result = _evaluate_five(cards)
        assert result.rank == ONE_PAIR

    def test_high_card(self):
        cards = make_cards(("A","♠"),("J","♥"),("8","♦"),("5","♣"),("2","♠"))
        result = _evaluate_five(cards)
        assert result.rank == HIGH_CARD

    def test_best_hand_from_seven(self):
        # Give player two aces + a pair of kings on the board → should find full house or best
        hole = make_cards(("A","♠"),("A","♥"))
        community = make_cards(("A","♦"),("K","♣"),("K","♠"),("2","♦"),("3","♥"))
        result = best_hand(hole, community)
        assert result.rank == FULL_HOUSE

    def test_best_hand_royal_flush_from_seven(self):
        hole = make_cards(("A","♠"),("K","♠"))
        community = make_cards(("Q","♠"),("J","♠"),("10","♠"),("2","♦"),("3","♥"))
        result = best_hand(hole, community)
        assert result.rank == ROYAL_FLUSH

    def test_hand_ordering(self):
        """Higher ranked hands should beat lower ranked hands."""
        cards_rf = make_cards(("A","♠"),("K","♠"),("Q","♠"),("J","♠"),("10","♠"))
        cards_fk = make_cards(("K","♠"),("K","♥"),("K","♦"),("K","♣"),("2","♠"))
        rf = _evaluate_five(cards_rf)
        fk = _evaluate_five(cards_fk)
        assert rf > fk

    def test_tiebreaker(self):
        """Two pairs: higher pair wins."""
        cards1 = make_cards(("A","♠"),("A","♥"),("K","♦"),("K","♣"),("7","♠"))
        cards2 = make_cards(("Q","♠"),("Q","♥"),("J","♦"),("J","♣"),("7","♦"))
        r1 = _evaluate_five(cards1)
        r2 = _evaluate_five(cards2)
        assert r1 > r2


# ─────────────────────────────────────────────────────
#  Player
# ─────────────────────────────────────────────────────

class TestPlayer:
    def test_human_player_initial_state(self):
        p = HumanPlayer("Alice", chips=1000)
        assert p.chips == 1000
        assert not p.is_folded
        assert not p.is_all_in
        assert p.hole_cards == []

    def test_place_bet(self):
        p = HumanPlayer("Alice", chips=1000)
        actual = p.place_bet(200)
        assert actual == 200
        assert p.chips == 800
        assert p.current_bet == 200

    def test_place_bet_capped_by_chips(self):
        p = HumanPlayer("Alice", chips=50)
        actual = p.place_bet(200)
        assert actual == 50
        assert p.chips == 0
        assert p.is_all_in

    def test_reset_for_hand(self):
        p = HumanPlayer("Alice", chips=1000)
        p.place_bet(100)
        p.is_folded = True
        p.receive_cards([Card("A", "♠"), Card("K", "♥")])
        p.reset_for_hand()
        assert p.current_bet == 0
        assert not p.is_folded
        assert p.hole_cards == []

    def test_ai_easy_does_not_crash(self):
        ai = AIPlayer("Bot", chips=1000, difficulty=DIFFICULTY_EASY)
        ai.receive_cards([Card("A", "♠"), Card("K", "♥")])
        state = {"call_amount": 0, "min_raise": 20, "pot": 100,
                 "community_cards": [], "num_active_opponents": 1}
        action, amount = ai.decide_action(state)
        assert action in (ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE, ACTION_ALL_IN)

    def test_ai_medium_does_not_crash(self):
        ai = AIPlayer("Bot", chips=1000, difficulty=DIFFICULTY_MEDIUM)
        ai.receive_cards([Card("A", "♠"), Card("A", "♥")])
        community = [Card("A", "♦"), Card("K", "♣"), Card("Q", "♠")]
        state = {"call_amount": 20, "min_raise": 20, "pot": 100,
                 "community_cards": community, "num_active_opponents": 1}
        action, amount = ai.decide_action(state)
        assert action in (ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE, ACTION_ALL_IN)

    def test_ai_hard_does_not_crash(self):
        ai = AIPlayer("Bot", chips=1000, difficulty=DIFFICULTY_HARD)
        ai.receive_cards([Card("2", "♠"), Card("7", "♥")])
        community = [Card("A", "♦"), Card("K", "♣"), Card("Q", "♠")]
        state = {"call_amount": 50, "min_raise": 20, "pot": 200,
                 "community_cards": community, "num_active_opponents": 2}
        action, amount = ai.decide_action(state)
        assert action in (ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE, ACTION_ALL_IN)

    def test_ai_folds_with_bad_hand_and_big_bet(self):
        """Hard AI should generally fold terrible hand against large bet."""
        import random
        random.seed(42)  # Fix seed to make test deterministic
        fold_count = 0
        for _ in range(20):
            ai = AIPlayer("Bot", chips=1000, difficulty=DIFFICULTY_HARD)
            ai.receive_cards([Card("2", "♠"), Card("7", "♣")])
            community = [Card("A", "♦"), Card("K", "♣"), Card("Q", "♠")]
            state = {"call_amount": 500, "min_raise": 20, "pot": 100,
                     "community_cards": community, "num_active_opponents": 2}
            action, _ = ai.decide_action(state)
            if action == ACTION_FOLD:
                fold_count += 1
        # Should fold most of the time (at least 60% given low pot odds)
        assert fold_count >= 12


# ─────────────────────────────────────────────────────
#  Integration: Game flow (smoke test)
# ─────────────────────────────────────────────────────

class TestGameIntegration:
    def test_single_hand_completes(self, monkeypatch):
        """Simulate a complete hand where all AIs play against each other."""
        from texas_holdem.game import Game

        human = HumanPlayer("TestPlayer", chips=1000)
        ai1 = AIPlayer("AI1", chips=1000, difficulty=DIFFICULTY_EASY)
        ai2 = AIPlayer("AI2", chips=1000, difficulty=DIFFICULTY_EASY)

        game = Game(human, [ai1, ai2], tutorial_mode=False)

        # Simulate human always checking/folding (fold immediately)
        responses = iter(["1"])  # Choose fold/check option
        monkeypatch.setattr("builtins.input", lambda _: next(responses, "1"))

        # This should not raise an exception
        game.play_hand()

        # Total chips should be conserved (or slightly changed due to blinds returning)
        total_chips = human.chips + ai1.chips + ai2.chips
        assert total_chips == 3000

    def test_deck_fully_dealt_in_hand(self):
        """Ensure the deck is used correctly over a hand."""
        d = Deck()
        # Pre-flop: 2 cards × 3 players = 6 cards
        # + 1 burn + 3 flop = 4 cards
        # + 1 burn + 1 turn = 2 cards
        # + 1 burn + 1 river = 2 cards
        # Total: 6 + 4 + 2 + 2 = 14 cards dealt/burned
        cards_used = 6 + 1 + 3 + 1 + 1 + 1 + 1
        d.deal(6)    # hole cards
        d.burn(); d.deal(3)  # flop
        d.burn(); d.deal(1)  # turn
        d.burn(); d.deal(1)  # river
        assert len(d) == 52 - (6 + 1 + 3 + 1 + 1 + 1 + 1)
