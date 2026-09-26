from dataclasses import dataclass
from typing import List, Sequence


@dataclass(frozen=True)
class Offer:
    household_id: str
    ask_price: float  # Rs/kWh -- only used for ordering; the cycle settles at one clearing price
    kwh: float


@dataclass(frozen=True)
class Bid:
    household_id: str
    kwh: float


@dataclass(frozen=True)
class Pairing:
    seller_id: str
    buyer_id: str
    amount_kwh: float


def match(offers: Sequence[Offer], bids: Sequence[Bid]) -> List[Pairing]:
    """Greedy two-pointer matching: sellers cheapest ask first, buyers neediest first,
    each pair trades min(seller's remaining, buyer's remaining), and whichever side
    empties moves on to its next household. Stops when either list is exhausted.

    Ties break by household id so the same inputs always give the same pairings.
    Pure -- no I/O, no mutation of its inputs.
    """
    sellers = sorted((o for o in offers if o.kwh > 0), key=lambda o: (o.ask_price, o.household_id))
    buyers = sorted((b for b in bids if b.kwh > 0), key=lambda b: (-b.kwh, b.household_id))

    pairings: List[Pairing] = []
    si = bi = 0
    seller_left = sellers[0].kwh if sellers else 0.0
    buyer_left = buyers[0].kwh if buyers else 0.0

    while si < len(sellers) and bi < len(buyers):
        amount = round(min(seller_left, buyer_left), 3)
        if amount > 0:
            pairings.append(Pairing(sellers[si].household_id, buyers[bi].household_id, amount))
        seller_left = round(seller_left - amount, 3)
        buyer_left = round(buyer_left - amount, 3)

        if seller_left <= 0:
            si += 1
            seller_left = sellers[si].kwh if si < len(sellers) else 0.0
        if buyer_left <= 0:
            bi += 1
            buyer_left = buyers[bi].kwh if bi < len(buyers) else 0.0

    return pairings
