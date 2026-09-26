"""Tamper-evident trade ledger: each trade row stores the hash of the row before it.

hash_n = sha256(hash_{n-1} || canonical JSON of trade n's fields)

Change, delete or reorder any past trade and every hash after it stops matching.
This is blockchain-*inspired* (a hash chain in an ordinary database), not a
distributed ledger or smart contract -- see the README's "Why not blockchain".
"""

import hashlib
import json
from dataclasses import dataclass
from typing import Iterable, Mapping, Optional

GENESIS_HASH = "0" * 64

# Every field that defines a trade. Values are hashed exactly as SQLite stores
# them (booleans as 0/1), so a row read back later hashes identically.
HASHED_FIELDS = (
    "id",
    "seller_id",
    "buyer_id",
    "amount_kwh",
    "price_per_kwh",
    "timestamp",
    "listing_id",
    "fulfilled_as_listed",
    "tick",
)


def canonical(trade: Mapping) -> str:
    fields = {k: trade[k] for k in HASHED_FIELDS}
    if isinstance(fields["fulfilled_as_listed"], bool):
        fields["fulfilled_as_listed"] = int(fields["fulfilled_as_listed"])
    return json.dumps(fields, sort_keys=True, separators=(",", ":"))


def trade_hash(prev_hash: str, trade: Mapping) -> str:
    return hashlib.sha256((prev_hash + canonical(trade)).encode("utf-8")).hexdigest()


@dataclass
class ChainCheck:
    valid: bool
    trades_checked: int
    head_hash: str
    first_invalid_trade_id: Optional[int] = None


def verify_chain(rows: Iterable[Mapping]) -> ChainCheck:
    """`rows` in id order, each with the hashed fields plus `prev_hash` and `hash`."""
    expected_prev = GENESIS_HASH
    checked = 0
    for row in rows:
        if row["prev_hash"] != expected_prev or row["hash"] != trade_hash(expected_prev, row):
            return ChainCheck(False, checked, expected_prev, first_invalid_trade_id=row["id"])
        expected_prev = row["hash"]
        checked += 1
    return ChainCheck(True, checked, expected_prev)
