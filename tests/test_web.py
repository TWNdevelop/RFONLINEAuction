from contextlib import closing
import tempfile
import unittest
from pathlib import Path

from auction import connect, create_auction
from web import create_app


class WebTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database = Path(self.temp_dir.name) / "test.sqlite3"
        with closing(connect(database)) as connection:
            create_auction(connection, "auction-1", "Test Sword", 60)
        self.app = create_app(database)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_lists_auctions(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test Sword", response.data)

    def test_creates_auction_from_form(self):
        response = self.client.post(
            "/auction/new",
            data={
                "auction_id": "auction-2",
                "text": "Test Shield",
                "lifetime_minutes": "30",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test Shield", response.data)
        self.assertIn(b"auction-timer", response.data)

    def test_saves_bid_from_form(self):
        response = self.client.post(
            "/auction/auction-1",
            data={"nickname": "Player_1", "points": "25"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Player_1", response.data)
        self.assertIn(b"25", response.data)

    def test_page_contains_countdown(self):
        response = self.client.get("/auction/auction-1")
        self.assertIn(b"auction-timer", response.data)

    def test_deletes_auction(self):
        response = self.client.post(
            "/auction/auction-1/delete", follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"Test Sword", response.data)

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.json, {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
