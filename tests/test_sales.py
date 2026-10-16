"""Sale detection against real Robinhood Chain transactions saved in tests/fixtures.

Run with:  .venv/bin/python -m unittest discover tests
"""
import copy
import json
import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chain import ORDER_FULFILLED_TOPIC, nft_transfers, sales_in_transaction  # noqa: E402
from config import NATIVE  # noqa: E402
from media import _gateway_urls  # noqa: E402
from ens import namehash  # noqa: E402
from tweet import format_amount, format_tweet  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
WHALESTREET = "0x01f33271d74a9dcc91798c7232d3d788da93a1f6"
WETH = "0x0bd7d308f8e1639fab988df18a8011f41eacad73"
USDG = "0x5fc5360d0400a0fd4f2af552add042d716f1d168"


def load(name):
    return json.loads((FIXTURES / f"{name}.json").read_text())


def sales(fixture, contract):
    ours = [entry for entry in fixture["receipt"]["logs"] if entry["address"].lower() == contract]
    return sales_in_transaction(contract, nft_transfers(ours), fixture["receipt"], fixture["tx"])


class SaleDetectionTest(unittest.TestCase):
    def test_listing_bought_with_eth(self):
        [sale] = sales(load("listing_eth"), WHALESTREET)
        self.assertEqual(sale.token_id, 2863)
        self.assertEqual(sale.payment_token, NATIVE)
        self.assertEqual(sale.amount, 3849000000000000)  # equals the ETH the buyer sent
        self.assertEqual(sale.marketplace, "OpenSea")

    def test_two_sales_in_one_transaction(self):
        found = sales(load("two_sales_one_tx"), WHALESTREET)
        self.assertEqual(sorted(s.token_id for s in found), [2336, 2918])
        self.assertTrue(all(s.amount == 3100000000000000 for s in found))
        self.assertEqual(len({s.id for s in found}), 2)

    def test_accepted_offer_reports_gross_price_not_sellers_cut(self):
        # The bidder paid 0.0031 WETH; the seller's mirror order only shows their 0.002914 after fees.
        [sale] = sales(load("matched_bid_weth"), "0x481ba120a6632714d8c872d1f4b6b57c8769dc21")
        self.assertEqual(sale.token_id, 2577)
        self.assertEqual(sale.payment_token, WETH)
        self.assertEqual(sale.amount, 3100000000000000)
        self.assertEqual(sale.seller, "0x3483216ecaacd0c36170a07530983e895bf21825")
        self.assertEqual(sale.buyer, "0x443575ac1114d1166e57dd16cc10cee38575f9f9")

    def test_router_hop_is_one_sale_to_the_final_owner(self):
        # Bought into a multicall contract, then forwarded to the user in the same tx.
        [sale] = sales(load("router_hop_usdg"), "0x1a6eb6a352a7278fec853a7c4900ff7917fc8a94")
        self.assertEqual(sale.token_id, 628)
        self.assertEqual(sale.payment_token, USDG)
        self.assertEqual(sale.amount, 1800000)  # 1.80 USDG
        self.assertEqual(sale.seller, "0xb2d2fa4a9cd4afb9652a78f58bed22a95760d114")
        self.assertEqual(sale.buyer, "0xd26b28938c5572fe888fd201a96fec53daa71b4b")

    def test_transfer_without_payment_is_not_a_sale(self):
        fixture = copy.deepcopy(load("listing_eth"))
        fixture["receipt"]["logs"] = [
            entry for entry in fixture["receipt"]["logs"] if entry["topics"][0] != ORDER_FULFILLED_TOPIC
        ]
        fixture["tx"]["value"] = "0x0"
        self.assertEqual(sales(fixture, WHALESTREET), [])


class FormattingTest(unittest.TestCase):
    def test_amounts(self):
        self.assertEqual(format_amount(Decimal("1.06")), "1.06")
        self.assertEqual(format_amount(Decimal("0.003849")), "0.003849")
        self.assertEqual(format_amount(Decimal("0.0031")), "0.0031")
        self.assertEqual(format_amount(Decimal("0.123456")), "0.1235")
        self.assertEqual(format_amount(Decimal("1234.5")), "1,234.5")
        self.assertEqual(format_amount(Decimal("2")), "2")

    def test_tweet_matches_reference_layout(self):
        text = format_tweet(
            emoji="🐳", name="Whale Street", token_id=2863, price=Decimal("0.003849"), symbol="ETH",
            usd=Decimal("9.8634"), marketplace="OpenSea",
            seller="0xea0e00000000000000000000000000000000d9b1", buyer="0xb21a000000000000000000000000000000002ed4",
        )
        self.assertEqual(text, "🐳 Whale Street #2863 Bought\n💰 0.003849 ETH ($9.86)\n🛒 OpenSea\n👤 0xea0e...d9b1 → 0xb21a...2ed4")

    def test_unknown_marketplace_line_is_dropped(self):
        text = format_tweet(
            emoji="🐳", name="Whale Street", token_id=1, price=Decimal("1"), symbol="ETH", usd=None,
            marketplace=None, seller="0x" + "1" * 40, buyer="0x" + "2" * 40,
        )
        self.assertNotIn("🛒", text)
        self.assertIn("💰 1 ETH\n", text)

    def test_ens_names_replace_addresses(self):
        text = format_tweet(
            emoji="🐳", name="Whale Street", token_id=1, price=Decimal("1"), symbol="ETH", usd=None,
            marketplace="OpenSea", seller="0x" + "1" * 40, buyer="0x" + "2" * 40, buyer_name="whale.eth",
        )
        self.assertTrue(text.endswith("👤 0x1111...1111 → whale.eth"))

    def test_namehash(self):
        self.assertEqual(namehash("addr.reverse").hex(), "91d1777781884d03a6757a803996e38de2a42967fb37eeaca72729271025a9e2")
        self.assertEqual(namehash("").hex(), "00" * 32)

    def test_ipfs_uris(self):
        self.assertEqual(_gateway_urls("ipfs://Qm123/7", "https://gw.example/ipfs/")[0], "https://gw.example/ipfs/Qm123/7")
        self.assertEqual(_gateway_urls("ipfs://ipfs/Qm123", "https://gw.example/ipfs/")[0], "https://gw.example/ipfs/Qm123")
        self.assertEqual(_gateway_urls("ar://abc", "x"), ["https://arweave.net/abc"])


if __name__ == "__main__":
    unittest.main()
