import json
import unittest
from datetime import UTC, datetime, timedelta

from auction import connect, create_auction, get_auction, place_bid
from finalize_auctions import finalize_ready_auctions, result_memo


class FinalizeAuctionsTests(unittest.TestCase):
    def setUp(self):
        self.connection = connect(":memory:")

    def tearDown(self):
        self.connection.close()

    def end_auction(self, auction_id: str):
        past = datetime.now(UTC) - timedelta(seconds=1)
        self.connection.execute(
            "UPDATE auctions SET ends_at = ? WHERE id = ?",
            (past.isoformat(), auction_id),
        )
        self.connection.commit()

    def test_result_memo_contains_winner_negative_points_and_item(self):
        memo = result_memo("Player_1", 25, "Меч Архонта")
        self.assertEqual(json.loads(memo), ["Player_1", -25, "Меч Архонта"])

    def test_finalizes_once_and_saves_signature(self):
        create_auction(self.connection, "auction-1", "Sword", 60)
        place_bid(self.connection, "auction-1", "Player_1", 10)
        place_bid(self.connection, "auction-1", "Player_2", 20)
        self.end_auction("auction-1")
        sent: list[bytes] = []

        def sender(memo: bytes) -> str:
            sent.append(memo)
            return "test-signature"

        first = finalize_ready_auctions(self.connection, sender)
        second = finalize_ready_auctions(self.connection, sender)
        auction, _ = get_auction(self.connection, "auction-1")

        self.assertEqual(first, [("auction-1", "test-signature")])
        self.assertEqual(second, [])
        self.assertEqual(len(sent), 1)
        self.assertEqual(json.loads(sent[0]), ["Player_2", -20, "Sword"])
        self.assertEqual(auction["result_signature"], "test-signature")

    def test_finalizes_auction_without_bids_without_transaction(self):
        create_auction(self.connection, "auction-1", "Sword", 60)
        self.end_auction("auction-1")
        results = finalize_ready_auctions(
            self.connection,
            lambda memo: self.fail("sender must not be called"),
        )
        self.assertEqual(results, [("auction-1", None)])


if __name__ == "__main__":
    unittest.main()
