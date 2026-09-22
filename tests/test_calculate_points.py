import unittest

from calculate_points import parse_points_memo


class ParsePointsMemoTests(unittest.TestCase):
    def test_reads_rpc_prefixed_complete_list(self):
        self.assertEqual(
            parse_points_memo('[35] [["Player_1",10],["Player_2",20]]'),
            [("Player_1", 10), ("Player_2", 20)],
        )

    def test_ignores_old_hash_memo(self):
        self.assertIsNone(parse_points_memo("[70] RFOA1:abc123"))

    def test_ignores_unrelated_or_invalid_memo(self):
        self.assertIsNone(parse_points_memo(None))
        self.assertIsNone(parse_points_memo("hello"))
        self.assertIsNone(parse_points_memo('[["Player",0]]'))


if __name__ == "__main__":
    unittest.main()
