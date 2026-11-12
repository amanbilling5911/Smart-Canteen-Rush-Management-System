import os
import sqlite3
import tempfile
import unittest

import database


class DatabaseMigrationTests(unittest.TestCase):
    def test_original_order_schema_migrates_without_losing_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "legacy.sqlite3")
            connection = sqlite3.connect(path)
            connection.execute(
                """
                CREATE TABLE orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_name TEXT NOT NULL,
                    phone_number TEXT,
                    food_item TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    order_type TEXT NOT NULL,
                    priority INTEGER,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                )
                """
            )
            connection.execute(
                """
                INSERT INTO orders (
                    customer_name, food_item, quantity, order_type, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("Legacy customer", "Masala Dosa", 2, "normal", "pending", "2026-10-23T10:00:00+00:00"),
            )
            connection.commit()
            connection.close()

            database.initialize_database(path)
            migrated = database.get_orders(path)

            self.assertEqual(len(migrated), 1)
            self.assertEqual(migrated[0]["customer_name"], "Legacy customer")
            self.assertEqual(migrated[0]["payment_status"], "pending")
            self.assertEqual(migrated[0]["items"][0]["item_name"], "Masala Dosa")
            self.assertIsNone(migrated[0]["items"][0]["unit_price"])
            self.assertEqual(migrated[0]["status"], "pending")


if __name__ == "__main__":
    unittest.main()
