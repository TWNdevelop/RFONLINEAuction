import unittest
from datetime import UTC, datetime, timedelta

from auction import (
    auction_has_ended,
    connect,
    create_auction,
    delete_auction,
    get_auction,
    get_winner,
    list_auctions,
    place_bid,
)


class AuctionTests(unittest.TestCase):
    def setUp(self):
        self.connection = connect(":memory:")

    def tearDown(self):
        self.connection.close()

    def test_creates_auction_and_saves_bids(self):
        create_auction(self.connection, "auction-1", "Sword", 60)
        place_bid(self.connection, "auction-1", "Player_1", 10)
        place_bid(self.connection, "auction-1", "Player_2", 20)

        auction, bids = get_auction(self.connection, "auction-1")
        self.assertEqual(auction["text"], "Sword")
        self.assertEqual(
            [(bid["nickname"], bid["points"]) for bid in bids],
            [("Player_1", 10), ("Player_2", 20)],
        )

    def test_rejects_duplicate_auction_id(self):
        create_auction(self.connection, "auction-1", "Sword", 60)
        with self.assertRaisesRegex(ValueError, "already exists"):
            create_auction(self.connection, "auction-1", "Shield", 60)

    def test_rejects_bid_for_missing_auction(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            place_bid(self.connection, "missing", "Player_1", 10)

    def test_lists_auction_and_bid_count(self):
        create_auction(self.connection, "auction-1", "Sword", 60)
        place_bid(self.connection, "auction-1", "Player_1", 10)
        auctions = list_auctions(self.connection)
        self.assertEqual(auctions[0]["bid_count"], 1)

    def test_ended_auction_rejects_bids_and_has_winner(self):
        create_auction(self.connection, "auction-1", "Sword", 60)
        place_bid(self.connection, "auction-1", "Player_1", 10)
        place_bid(self.connection, "auction-1", "Player_2", 20)
        past = datetime.now(UTC) - timedelta(seconds=1)
        self.connection.execute(
            "UPDATE auctions SET ends_at = ? WHERE id = ?",
            (past.isoformat(), "auction-1"),
        )
        self.connection.commit()

        auction, _ = get_auction(self.connection, "auction-1")
        self.assertTrue(auction_has_ended(auction))
        self.assertEqual(get_winner(self.connection, "auction-1")["nickname"], "Player_2")
        with self.assertRaisesRegex(ValueError, "ended"):
            place_bid(self.connection, "auction-1", "Player_3", 30)

    def test_deletes_auction_and_its_bids(self):
        create_auction(self.connection, "auction-1", "Sword", 60)
        place_bid(self.connection, "auction-1", "Player_1", 10)
        delete_auction(self.connection, "auction-1")
        self.assertEqual(list_auctions(self.connection), [])
        self.assertEqual(
            self.connection.execute("SELECT COUNT(*) FROM bids").fetchone()[0], 0
        )

    def test_cannot_delete_completed_auction(self):
        create_auction(self.connection, "auction-1", "Sword", 60)
        past = datetime.now(UTC) - timedelta(seconds=1)
        self.connection.execute(
            "UPDATE auctions SET ends_at = ? WHERE id = ?",
            (past.isoformat(), "auction-1"),
        )
        self.connection.commit()
        with self.assertRaisesRegex(ValueError, "cannot be deleted"):
            delete_auction(self.connection, "auction-1")
        self.assertEqual(len(list_auctions(self.connection)), 1)


if __name__ == "__main__":
    unittest.main()
