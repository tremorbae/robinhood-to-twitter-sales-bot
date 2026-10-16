"""Turns raw payment amounts into human prices and USD values."""
from __future__ import annotations

import logging
import time
from decimal import Decimal
from typing import Optional, Tuple

import requests

from chain import RPC, decode_string
from config import PAYMENT_TOKENS

log = logging.getLogger(__name__)

ETH_USD_URL = "https://api.coinbase.com/v2/prices/ETH-USD/spot"


class Pricer:
    def __init__(self, rpc: RPC):
        self.rpc = rpc
        self.tokens = dict(PAYMENT_TOKENS)
        self._eth_usd: Optional[Decimal] = None
        self._eth_usd_at = 0.0

    def token_info(self, token: str) -> dict:
        if token not in self.tokens:
            # A token we don't know yet: ask the contract. No USD value for these.
            try:
                symbol = decode_string(self.rpc.eth_call(token, "0x95d89b41"))
                decimals = int(self.rpc.eth_call(token, "0x313ce567"), 16)
            except Exception:
                symbol, decimals = "TOKENS", 18
            self.tokens[token] = {"symbol": symbol, "decimals": decimals, "peg": None}
        return self.tokens[token]

    def eth_usd(self) -> Optional[Decimal]:
        if self._eth_usd is None or time.time() - self._eth_usd_at > 60:
            try:
                resp = requests.get(ETH_USD_URL, timeout=10)
                resp.raise_for_status()
                self._eth_usd = Decimal(resp.json()["data"]["amount"])
                self._eth_usd_at = time.time()
            except Exception as e:
                log.warning("Couldn't fetch the ETH price (%s); using the last known price", e)
        return self._eth_usd

    def describe(self, token: str, amount: int) -> Tuple[Decimal, str, Optional[Decimal]]:
        """Returns (price, symbol, usd) for a raw on-chain amount."""
        info = self.token_info(token)
        price = Decimal(amount) / (Decimal(10) ** info["decimals"])
        usd = None
        if info["peg"] == "USD":
            usd = price
        elif info["peg"] == "ETH":
            rate = self.eth_usd()
            usd = price * rate if rate is not None else None
        return price, info["symbol"], usd
