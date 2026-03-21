"""
Hand evaluator for Texas Hold'em Poker.
Evaluates the best 5-card hand from any combination of hole cards + community cards.
"""
from itertools import combinations
from .card import Card, RANKS

# Hand rank constants (higher is better)
HIGH_CARD = 1
ONE_PAIR = 2
TWO_PAIR = 3
THREE_OF_A_KIND = 4
STRAIGHT = 5
FLUSH = 6
FULL_HOUSE = 7
FOUR_OF_A_KIND = 8
STRAIGHT_FLUSH = 9
ROYAL_FLUSH = 10

HAND_NAMES = {
    HIGH_CARD: "高牌",
    ONE_PAIR: "一对",
    TWO_PAIR: "两对",
    THREE_OF_A_KIND: "三条",
    STRAIGHT: "顺子",
    FLUSH: "同花",
    FULL_HOUSE: "葫芦",
    FOUR_OF_A_KIND: "四条（炸弹）",
    STRAIGHT_FLUSH: "同花顺",
    ROYAL_FLUSH: "皇家同花顺",
}

HAND_DESCRIPTIONS = {
    HIGH_CARD: "手中最大的单张牌",
    ONE_PAIR: "两张相同点数的牌",
    TWO_PAIR: "两组各两张相同点数的牌",
    THREE_OF_A_KIND: "三张相同点数的牌",
    STRAIGHT: "五张连续点数的牌（如 5-6-7-8-9）",
    FLUSH: "五张相同花色的牌",
    FULL_HOUSE: "三条 + 一对（如 KKK+QQ）",
    FOUR_OF_A_KIND: "四张相同点数的牌",
    STRAIGHT_FLUSH: "五张连续且相同花色的牌",
    ROYAL_FLUSH: "A-K-Q-J-10 且同花色，最强的手牌！",
}


class HandResult:
    """Represents the result of evaluating a 5-card hand."""

    def __init__(self, rank: int, tiebreakers: list[int], cards: list[Card]):
        self.rank = rank          # Hand category rank
        self.tiebreakers = tiebreakers  # Values to break ties within the same rank
        self.cards = cards        # The 5 best cards

    @property
    def name(self) -> str:
        return HAND_NAMES[self.rank]

    @property
    def description(self) -> str:
        return HAND_DESCRIPTIONS[self.rank]

    def __gt__(self, other: "HandResult") -> bool:
        if self.rank != other.rank:
            return self.rank > other.rank
        return self.tiebreakers > other.tiebreakers

    def __eq__(self, other: "HandResult") -> bool:
        return self.rank == other.rank and self.tiebreakers == other.tiebreakers

    def __lt__(self, other: "HandResult") -> bool:
        return not (self > other or self == other)

    def __str__(self) -> str:
        cards_str = " ".join(str(c) for c in self.cards)
        return f"{self.name} [{cards_str}]"


def _evaluate_five(cards: list[Card]) -> HandResult:
    """Evaluate exactly 5 cards and return a HandResult."""
    assert len(cards) == 5
    values = sorted([c.value for c in cards], reverse=True)
    suits = [c.suit for c in cards]
    is_flush = len(set(suits)) == 1

    # Check for straight (including A-2-3-4-5 wheel)
    is_straight = False
    straight_high = 0
    if max(values) - min(values) == 4 and len(set(values)) == 5:
        is_straight = True
        straight_high = max(values)
    elif set(values) == {14, 2, 3, 4, 5}:  # A-2-3-4-5 wheel
        is_straight = True
        straight_high = 5  # 5-high straight

    from collections import Counter
    counts = Counter(values)
    freq = sorted(counts.values(), reverse=True)         # e.g. [3,1,1] for three-of-a-kind
    # Sort by frequency first, then by value (descending) for tiebreaking
    groups = sorted(counts.items(), key=lambda x: (x[1], x[0]), reverse=True)
    tiebreak_values = [v for v, _ in groups]

    if is_straight and is_flush:
        if straight_high == 14:
            return HandResult(ROYAL_FLUSH, [straight_high], cards)
        return HandResult(STRAIGHT_FLUSH, [straight_high], cards)
    if freq[0] == 4:
        return HandResult(FOUR_OF_A_KIND, tiebreak_values, cards)
    if freq[0] == 3 and freq[1] == 2:
        return HandResult(FULL_HOUSE, tiebreak_values, cards)
    if is_flush:
        return HandResult(FLUSH, values, cards)
    if is_straight:
        return HandResult(STRAIGHT, [straight_high], cards)
    if freq[0] == 3:
        return HandResult(THREE_OF_A_KIND, tiebreak_values, cards)
    if freq[0] == 2 and freq[1] == 2:
        return HandResult(TWO_PAIR, tiebreak_values, cards)
    if freq[0] == 2:
        return HandResult(ONE_PAIR, tiebreak_values, cards)
    return HandResult(HIGH_CARD, values, cards)


def best_hand(hole_cards: list[Card], community_cards: list[Card]) -> HandResult:
    """
    Find the best 5-card hand from hole cards + community cards.
    Considers all C(n, 5) combinations.
    """
    all_cards = hole_cards + community_cards
    if len(all_cards) < 5:
        raise ValueError("Need at least 5 cards to evaluate a hand")

    best: HandResult | None = None
    for five in combinations(all_cards, 5):
        result = _evaluate_five(list(five))
        if best is None or result > best:
            best = result
    return best


def hand_strength_percent(hole_cards: list[Card], community_cards: list[Card],
                          num_opponents: int = 1, simulations: int = 500) -> float:
    """
    Estimate the win probability of hole_cards against `num_opponents` random hands
    using Monte Carlo simulation.
    Returns a float in [0, 1].
    """
    import random
    from .card import Deck, SUITS, RANKS

    # Build remaining deck (cards not in use)
    used = set(str(c) for c in hole_cards + community_cards)
    remaining_cards = [Card(r, s) for s in SUITS for r in RANKS if f"{s}{r}" not in used]

    wins = 0
    ties = 0

    for _ in range(simulations):
        deck_copy = remaining_cards[:]
        random.shuffle(deck_copy)
        idx = 0

        # Complete community cards to 5 total
        needed_community = 5 - len(community_cards)
        sim_community = community_cards + deck_copy[idx: idx + needed_community]
        idx += needed_community

        # Deal opponent hands
        opponent_hands = []
        for _ in range(num_opponents):
            opp_hole = deck_copy[idx: idx + 2]
            idx += 2
            if len(opp_hole) < 2:
                break
            opponent_hands.append(opp_hole)

        if len(opponent_hands) < num_opponents:
            continue

        my_best = best_hand(hole_cards, sim_community)
        opponent_bests = [best_hand(opp, sim_community) for opp in opponent_hands]

        if all(my_best > opp for opp in opponent_bests):
            wins += 1
        elif all(my_best == opp for opp in opponent_bests):
            ties += 1

    return (wins + ties * 0.5) / simulations


def get_outs_hint(hole_cards: list[Card], community_cards: list[Card]) -> str:
    """
    Provide a beginner-friendly hint about drawing outs.
    Only meaningful on the flop (3 community cards) or turn (4 community cards).
    """
    if len(community_cards) not in (3, 4):
        return ""

    from collections import Counter
    from .card import SUITS as ALL_SUITS, RANKS as ALL_RANKS

    used = set(str(c) for c in hole_cards + community_cards)
    remaining = [Card(r, s) for s in ALL_SUITS for r in ALL_RANKS if f"{s}{r}" not in used]

    current_best = best_hand(hole_cards, community_cards)
    outs = sum(
        1 for c in remaining
        if best_hand(hole_cards, community_cards + [c]) > current_best
    )

    total_unseen = len(remaining)
    if len(community_cards) == 3:
        # Two cards to come
        probability = 1 - ((total_unseen - outs) / total_unseen) * ((total_unseen - outs - 1) / (total_unseen - 1))
        stage = "翻牌后（还有两张公共牌）"
    else:
        # One card to come
        probability = outs / total_unseen
        stage = "转牌后（还有一张公共牌）"

    hint = (
        f"  💡 听牌提示：{stage}\n"
        f"     当前最佳牌型：{current_best.name}\n"
        f"     能改善你牌型的牌（outs）：约 {outs} 张\n"
        f"     摸到改善牌的概率：约 {probability:.1%}\n"
    )
    return hint
