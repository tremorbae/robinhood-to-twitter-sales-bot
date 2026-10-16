"""Looks up a wallet's primary ENS name (e.g. vitalik.eth) on Ethereum mainnet.

Robinhood Chain wallets normally share their address with the owner's Ethereum
wallet, so the same primary name applies. A name only counts if it also points
back to the address, so nobody can claim someone else's wallet.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Dict, Optional, Tuple

from Crypto.Hash import keccak

from chain import RPC, RPCError, decode_string

log = logging.getLogger(__name__)

ENS_REGISTRY = "0x00000000000c2e074ec69a0dfb2997ba6c7d2e1e"
RESOLVER = "0x0178b8bf"  # resolver(bytes32)
NAME = "0x691f3431"      # name(bytes32)
ADDR = "0x3b3b57de"      # addr(bytes32)
CACHE_SECONDS = 6 * 3600
EMPTY = "0x" + "0" * 40


def _keccak(data: bytes) -> bytes:
    return keccak.new(digest_bits=256, data=data).digest()


def namehash(name: str) -> bytes:
    node = b"\0" * 32
    for label in reversed(name.split(".")) if name else []:
        node = _keccak(node + _keccak(label.encode()))
    return node


ADDR_REVERSE = namehash("addr.reverse")


class ENS:
    def __init__(self, rpc_url: str):
        self.rpc = RPC(rpc_url)
        self.cache: Dict[str, Tuple[Optional[str], float]] = {}
        self.lock = threading.Lock()

    def _resolver(self, node: bytes) -> Optional[str]:
        address = "0x" + self.rpc.eth_call(ENS_REGISTRY, RESOLVER + node.hex())[-40:]
        return None if address == EMPTY else address

    def _lookup(self, address: str) -> Optional[str]:
        node = _keccak(ADDR_REVERSE + _keccak(address[2:].encode()))
        resolver = self._resolver(node)
        if not resolver:
            return None
        name = decode_string(self.rpc.eth_call(resolver, NAME + node.hex())).strip()
        if not name or not name.isprintable() or len(name) > 40:
            return None
        forward_node = namehash(name.lower())
        forward_resolver = self._resolver(forward_node)
        if not forward_resolver:
            return None
        points_to = "0x" + self.rpc.eth_call(forward_resolver, ADDR + forward_node.hex())[-40:]
        return name if points_to == address else None

    def name(self, address: str) -> Optional[str]:
        """The primary ENS name, or None (also None if the lookup fails, so posts never wait on ENS)."""
        address = address.lower()
        with self.lock:
            cached = self.cache.get(address)
        if cached and time.time() - cached[1] < CACHE_SECONDS:
            return cached[0]
        try:
            name = self._lookup(address)
        except (RPCError, ValueError, IndexError):
            name = None  # a contract reverted or returned junk: treat as "no name"
        except Exception as e:
            log.warning("ENS lookup for %s failed: %s", address, e)
            return None
        with self.lock:
            self.cache[address] = (name, time.time())
        return name
