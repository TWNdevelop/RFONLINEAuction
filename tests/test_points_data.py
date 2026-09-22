import json
import tempfile
import unittest
from pathlib import Path

from points_data import load_batch, memo_bytes


class PointsDataTests(unittest.TestCase):
    def write_json(self, value) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        path = Path(temp_dir.name) / "players.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_loads_valid_batch_and_encodes_memo(self):
        batch = load_batch(
            self.write_json(
                {
                    "operation_id": "daily-2026-09-22",
                    "players": [
                        {"player_id": 101, "nickname": "DarkKnight", "points": 150}
                    ],
                }
            )
        )
        record = json.loads(memo_bytes(batch.operation_id, batch.players[0]))
        self.assertEqual(record["player_id"], 101)
        self.assertEqual(record["nickname"], "DarkKnight")
        self.assertEqual(record["points"], 150)

    def test_rejects_duplicate_player_id(self):
        path = self.write_json(
            {
                "operation_id": "daily-1",
                "players": [
                    {"player_id": 101, "nickname": "One", "points": 1},
                    {"player_id": 101, "nickname": "Two", "points": 2},
                ],
            }
        )
        with self.assertRaisesRegex(ValueError, "duplicate player_id"):
            load_batch(path)

    def test_rejects_non_positive_points(self):
        path = self.write_json(
            {
                "operation_id": "daily-1",
                "players": [{"player_id": 101, "nickname": "One", "points": 0}],
            }
        )
        with self.assertRaisesRegex(ValueError, "positive integer"):
            load_batch(path)


if __name__ == "__main__":
    unittest.main()
