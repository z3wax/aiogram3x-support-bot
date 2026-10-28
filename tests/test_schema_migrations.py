"""Upgrade partially migrated SQLite databases without changing handler tuples."""
import asyncio
import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "support_bot_migrations", Path(__file__).resolve().parents[1] / "bot" / "database.py"
)
database = importlib.util.module_from_spec(spec)
spec.loader.exec_module(database)


class SchemaMigrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.previous_database = database.DB_NAME
        database.DB_NAME = str(Path(self.directory.name) / "legacy.sqlite3")

    async def asyncTearDown(self):
        database.DB_NAME = self.previous_database
        self.directory.cleanup()

    async def test_existing_user_columns_do_not_skip_ticket_closed_at(self):
        with sqlite3.connect(database.DB_NAME) as connection:
            connection.execute("""CREATE TABLE tickets (
                id INTEGER PRIMARY KEY, client_id INTEGER, operator_id INTEGER,
                status TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            connection.execute("""INSERT INTO tickets (id, client_id, operator_id, status)
                VALUES (1, 10, 20, 'in_progress')""")
        await database.init_db()
        await database.close_ticket(1)
        ticket = await database.get_ticket(1)
        self.assertEqual(ticket[3], "closed")
        self.assertIsNotNone(ticket[5])

    async def test_partial_user_schema_preserves_values_and_handler_column_order(self):
        with sqlite3.connect(database.DB_NAME) as connection:
            connection.execute("""CREATE TABLE users (
                user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT,
                role TEXT DEFAULT 'client', rating_score INTEGER DEFAULT 0,
                rating_count INTEGER DEFAULT 0, is_banned BOOLEAN DEFAULT 0
            )""")
            connection.execute("""INSERT INTO users
                (user_id, username, full_name, role, rating_score, rating_count)
                VALUES (20, 'operator20', 'Operator', 'operator', 12, 3)""")
        await database.init_db()
        expected = (20, "operator20", "Operator", "operator", 0, 1, "all", 12, 3, None)
        self.assertEqual(await database.get_user(20), expected)
        self.assertEqual(await database.get_operators(online_only=True), [expected])

        # Startup is repeatable and preserves user data after all columns exist.
        await database.init_db()
        self.assertEqual(await database.get_user(20), expected)

    async def test_concurrent_initialization_and_fresh_schema_are_compatible(self):
        await asyncio.gather(database.init_db(), database.init_db())
        await database.add_user(30, "client30", "Client")
        self.assertEqual(
            await database.get_user(30),
            (30, "client30", "Client", "client", 0, 1, "all", 0, 0, None),
        )


if __name__ == "__main__":
    unittest.main()
