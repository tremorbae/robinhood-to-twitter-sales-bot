"""Settings for the sales bot. Values come from the .env file (see .env.example)."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

# ---- Robinhood Chain constants -------------------------------------------------

CHAIN_ID = 4663
DEFAULT_RPC_URL = "https://rpc.mainnet.chain.robinhood.com"
DEFAULT_CONTRACT = "0x01f33271d74a9dcc91798c7232d3d788da93a1f6"  # Whales of WhaleStreet

NATIVE = "0x0000000000000000000000000000000000000000"  # stands in for plain ETH

# Tokens buyers pay with. "peg" says how to get a USD value: ETH-priced or 1:1 USD.
PAYMENT_TOKENS = {
    NATIVE: {"symbol": "ETH", "decimals": 18, "peg": "ETH"},
    "0x0bd7d308f8e1639fab988df18a8011f41eacad73": {"symbol": "ETH", "decimals": 18, "peg": "ETH"},  # WETH (offers); always 1:1 with ETH
    "0x5fc5360d0400a0fd4f2af552add042d716f1d168": {"symbol": "USDG", "decimals": 6, "peg": "USD"},
}

# Seaport is the exchange contract OpenSea settles trades through.
SEAPORT_ADDRESSES = {
    "0x0000000000000068f116a894984e2db1123eb395",  # Seaport 1.6
    "0x00000000000000adc04c56bf30ac9d3c0aaf14dc",  # Seaport 1.5
}
OPENSEA_FEE_RECIPIENT = "0x0000a26b00c1f0df003000390027140000faa719"

# Other marketplace contracts, by the address a buyer's transaction is sent to.
# Add entries here if your collection trades somewhere other than OpenSea.
MARKETPLACES: dict = {}


# ---- .env settings ---------------------------------------------------------------

def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _int(name: str, default: Optional[int]) -> Optional[int]:
    value = os.getenv(name, "").strip()
    return int(value) if value else default


def _float(name: str, default: float) -> float:
    value = os.getenv(name, "").strip()
    return float(value) if value else default


@dataclass
class Settings:
    contract: str
    collection_name: str
    emoji: str
    rpc_url: str
    poll_seconds: int
    confirmations: int
    max_block_range: int
    start_block: Optional[int]
    min_price_usd: float
    seconds_between_posts: float
    dry_run: bool
    ipfs_gateway: str
    ens_rpc_url: str
    image_url_template: str
    state_file: str
    x_api_key: str
    x_api_secret: str
    x_access_token: str
    x_access_token_secret: str

    @property
    def has_x_keys(self) -> bool:
        return all([self.x_api_key, self.x_api_secret, self.x_access_token, self.x_access_token_secret])


def load_settings() -> Settings:
    contract = (os.getenv("CONTRACT_ADDRESS", "").strip() or DEFAULT_CONTRACT).lower()
    if not re.fullmatch(r"0x[0-9a-f]{40}", contract):
        raise SystemExit("CONTRACT_ADDRESS must be your collection's 0x... contract address")

    gateway = os.getenv("IPFS_GATEWAY", "").strip() or "https://ipfs.filebase.io/ipfs/"
    if not gateway.endswith("/"):
        gateway += "/"

    return Settings(
        contract=contract,
        collection_name=os.getenv("COLLECTION_NAME", "").strip() or "Whale Street",
        emoji=os.getenv("EMOJI", "").strip() or "🐳",
        rpc_url=os.getenv("RPC_URL", "").strip() or DEFAULT_RPC_URL,
        poll_seconds=_int("POLL_SECONDS", 15),
        # ~2 seconds of blocks; protects against the rare sequencer reorg.
        confirmations=_int("CONFIRMATIONS", 20),
        max_block_range=_int("MAX_BLOCK_RANGE", 5000),
        start_block=_int("START_BLOCK", None),
        min_price_usd=_float("MIN_PRICE_USD", 0),
        seconds_between_posts=_float("SECONDS_BETWEEN_POSTS", 5),
        # Defaults to a dry run so nothing is posted until you opt in.
        dry_run=_bool("DRY_RUN", True),
        ipfs_gateway=gateway,
        # Ethereum mainnet RPC for ENS names; set ENS_RPC_URL= "off" to show plain addresses.
        ens_rpc_url=os.getenv("ENS_RPC_URL", "").strip() or "https://ethereum-rpc.publicnode.com",
        image_url_template=os.getenv("IMAGE_URL_TEMPLATE", "").strip(),
        state_file=os.getenv("STATE_FILE", "").strip() or "state.json",
        x_api_key=os.getenv("X_API_KEY", "").strip(),
        x_api_secret=os.getenv("X_API_SECRET", "").strip(),
        x_access_token=os.getenv("X_ACCESS_TOKEN", "").strip(),
        x_access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET", "").strip(),
    )
