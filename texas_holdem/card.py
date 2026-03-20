"""
Card and Deck classes for Texas Hold'em Poker.
"""
import random

SUITS = ['♠', '♥', '♦', '♣']
SUIT_NAMES = {'♠': '黑桃', '♥': '红心', '♦': '方块', '♣': '梅花'}
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
RANK_VALUES = {r: i + 2 for i, r in enumerate(RANKS)}  # 2→2, A→14


class Card:
    """Represents a single playing card."""

    def __init__(self, rank: str, suit: str):
        if rank not in RANKS:
            raise ValueError(f"Invalid rank: {rank}")
        if suit not in SUITS:
            raise ValueError(f"Invalid suit: {suit}")
        self.rank = rank
        self.suit = suit
        self.value = RANK_VALUES[rank]

    def __str__(self) -> str:
        return f"{self.suit}{self.rank}"

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other) -> bool:
        return isinstance(other, Card) and self.rank == other.rank and self.suit == other.suit

    def __lt__(self, other) -> bool:
        return self.value < other.value

    def display_cn(self) -> str:
        """Return Chinese-friendly display string."""
        return f"{SUIT_NAMES[self.suit]}{self.rank}"


class Deck:
    """Represents a standard 52-card deck."""

    def __init__(self):
        self.cards: list[Card] = []
        self.reset()

    def reset(self):
        """Re-create and shuffle the full deck."""
        self.cards = [Card(rank, suit) for suit in SUITS for rank in RANKS]
        self.shuffle()

    def shuffle(self):
        """Shuffle the deck in place."""
        random.shuffle(self.cards)

    def deal(self, count: int = 1) -> list[Card]:
        """Deal `count` cards from the top of the deck."""
        if count > len(self.cards):
            raise ValueError("Not enough cards in deck")
        dealt = self.cards[:count]
        self.cards = self.cards[count:]
        return dealt

    def deal_one(self) -> Card:
        """Deal a single card."""
        return self.deal(1)[0]

    def burn(self):
        """Burn the top card (discard without using)."""
        if self.cards:
            self.cards.pop(0)

    def __len__(self) -> int:
        return len(self.cards)
