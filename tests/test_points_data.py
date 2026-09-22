import json
import tempfile
import unittest
from pathlib import Path

from points_data import load_players, memo_bytes


class PointsDataTests(unittest.TestCase):
    def write_json(self, value) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        path = Path(temp_dir.name) / "players.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_loads_nickname_and_points_only(self):
        players = load_players(
            self.write_json([{"nickname": "DarkKnight", "points": 150}])
        )
        self.assertEqual(players[0].nickname, "DarkKnight")
        self.assertEqual(players[0].points, 150)
        self.assertEqual(memo_bytes(players), b'[["DarkKnight",150]]')

    def test_memo_does_not_depend_on_list_order(self):
        first = load_players(
            self.write_json(
                [
                    {"nickname": "One", "points": 1},
                    {"nickname": "Two", "points": 2},
                ]
            )
        )
        second = load_players(
            self.write_json(
                [
                    {"nickname": "Two", "points": 2},
                    {"nickname": "One", "points": 1},
                ]
            )
        )
        self.assertEqual(memo_bytes(first), memo_bytes(second))
        self.assertEqual(memo_bytes(first), b'[["One",1],["Two",2]]')

    def test_rejects_more_than_50_players(self):
        path = self.write_json(
            [{"nickname": f"Player{i}", "points": i + 1} for i in range(51)]
        )
        with self.assertRaisesRegex(ValueError, "more than 50"):
            load_players(path)

    def test_rejects_duplicate_nickname(self):
        path = self.write_json(
            [
                {"nickname": "Player", "points": 1},
                {"nickname": "player", "points": 2},
            ]
        )
        with self.assertRaisesRegex(ValueError, "duplicate nickname"):
            load_players(path)

    def test_rejects_extra_fields(self):
        path = self.write_json(
            [{"nickname": "Player", "points": 1, "player_id": 100}]
        )
        with self.assertRaisesRegex(ValueError, "only nickname and points"):
            load_players(path)


if __name__ == "__main__":
    unittest.main()
