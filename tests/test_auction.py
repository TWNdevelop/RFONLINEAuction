import sqlite3
import unittest

from auction import create_auction, get_auction, list_auctions, place_bid


class AuctionTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(
            """
            CREATE TABLE auctions (id TEXT PRIMARY KEY, text TEXT NOT NULL);
            CREATE TABLE bids (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                auction_id TEXT NOT NULL REFERENCES auctions(id),
                nickname TEXT NOT NULL,
                points INTEGER NOT NULL CHECK (points > 0),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

    def tearDown(self):
        self.connection.close()

    def test_creates_auction_and_saves_bids(self):
        create_auction(self.connection, "auction-1", "Sword")
        place_bid(self.connection, "auction-1", "Player_1", 10)
        place_bid(self.connection, "auction-1", "Player_2", 20)

        auction, bids = get_auction(self.connection, "auction-1")
        self.assertEqual(auction["text"], "Sword")
        self.assertEqual(
            [(bid["nickname"], bid["points"]) for bid in bids],
            [("Player_1", 10), ("Player_2", 20)],
        )

    def test_rejects_duplicate_auction_id(self):
        create_auction(self.connection, "auction-1", "Sword")
        with self.assertRaisesRegex(ValueError, "already exists"):
            create_auction(self.connection, "auction-1", "Shield")

    def test_rejects_bid_for_missing_auction(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            place_bid(self.connection, "missing", "Player_1", 10)

    def test_lists_auction_and_bid_count(self):
        create_auction(self.connection, "auction-1", "Sword")
        place_bid(self.connection, "auction-1", "Player_1", 10)
        auctions = list_auctions(self.connection)
        self.assertEqual(auctions[0]["bid_count"], 1)


if __name__ == "__main__":
    unittest.main()
