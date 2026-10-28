"""Shared acceptance tests: ticket ratings must be exact integers from 1 to 5."""
import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "support_bot_rating_contract", Path(__file__).resolve().parents[1] / "bot" / "database.py"
)
database = importlib.util.module_from_spec(spec)
spec.loader.exec_module(database)


class RatingValidationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.previous_database = database.DB_NAME
        database.DB_NAME = str(Path(self.directory.name) / "ratings.sqlite3")
        await database.init_db()
        await database.add_user(1, "client", "Client")
        await database.add_user(100, "operator", "Operator", role="operator")

    async def asyncTearDown(self):
        database.DB_NAME = self.previous_database
        self.directory.cleanup()

    async def closed_ticket(self):
        ticket = await database.create_ticket(1)
        self.assertTrue(await database.take_ticket(ticket, 100))
        await database.close_ticket(ticket)
        return ticket

    def snapshot(self):
        with sqlite3.connect(database.DB_NAME) as connection:
            rows = connection.execute("SELECT ticket_id, score FROM ratings ORDER BY ticket_id").fetchall()
            score = connection.execute("SELECT rating_score, rating_count FROM users WHERE user_id=100").fetchone()
        return rows, score

    async def test_invalid_scores_leave_all_rating_data_unchanged(self):
        for score in (-1, 0, 6, 99, True, False, 1.5, "5", None):
            with self.subTest(score=repr(score)):
                ticket = await self.closed_ticket()
                before = self.snapshot()
                self.assertIs(await database.save_rating(ticket, 1, 100, score), False)
                self.assertEqual(self.snapshot(), before)

    async def test_each_valid_integer_is_accepted_and_accumulated(self):
        for score in range(1, 6):
            ticket = await self.closed_ticket()
            self.assertIs(await database.save_rating(ticket, 1, 100, score), True)
        rows, total = self.snapshot()
        self.assertEqual([score for _, score in rows], [1, 2, 3, 4, 5])
        self.assertEqual(total, (15, 5))

    async def test_duplicate_rating_still_preserves_original_score(self):
        ticket = await self.closed_ticket()
        self.assertTrue(await database.save_rating(ticket, 1, 100, 3))
        before = self.snapshot()
        self.assertIs(await database.save_rating(ticket, 1, 100, 5), False)
        self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
    unittest.main()
