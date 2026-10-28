"""Real SQLite regressions for exclusive operator ownership of a ticket."""
import asyncio
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "support_bot_database", Path(__file__).resolve().parents[1] / "bot" / "database.py"
)
database = importlib.util.module_from_spec(spec)
spec.loader.exec_module(database)


class TicketClaimTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.previous_database = database.DB_NAME
        database.DB_NAME = str(Path(self.directory.name) / "tickets.sqlite3")
        await database.init_db()

    async def asyncTearDown(self):
        database.DB_NAME = self.previous_database
        self.directory.cleanup()

    async def test_missing_ticket_does_not_report_success(self):
        self.assertFalse(await database.take_ticket(9999, 100))
        self.assertIsNone(await database.get_ticket(9999))

    async def test_claimed_and_closed_tickets_keep_their_existing_assignment(self):
        ticket_id = await database.create_ticket(1)
        self.assertTrue(await database.take_ticket(ticket_id, 100))
        self.assertFalse(await database.take_ticket(ticket_id, 200))
        ticket = await database.get_ticket(ticket_id)
        self.assertEqual(ticket[2:4], (100, "in_progress"))

        await database.close_ticket(ticket_id)
        before = await database.get_ticket(ticket_id)
        self.assertFalse(await database.take_ticket(ticket_id, 200))
        self.assertEqual(await database.get_ticket(ticket_id), before)

    async def test_concurrent_claims_have_exactly_one_winner(self):
        ticket_id = await database.create_ticket(1)
        operators = list(range(100, 108))
        outcomes = await asyncio.gather(
            *(database.take_ticket(ticket_id, operator) for operator in operators)
        )
        self.assertEqual(sum(outcomes), 1, "a ticket must never be assigned successfully twice")
        winner = operators[outcomes.index(True)]
        ticket = await database.get_ticket(ticket_id)
        self.assertEqual(ticket[2:4], (winner, "in_progress"))


if __name__ == "__main__":
    unittest.main()
