"""SQLite persistence for canteen orders, order items, and demo payments."""

import os
import sqlite3
from contextlib import contextmanager


def connect(database_path):
    directory = os.path.dirname(database_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    connection = sqlite3.connect(database_path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def database_connection(database_path):
    connection = connect(database_path)
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database(database_path):
    """Create tables and safely migrate the original single-item schema."""
    with database_connection(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                phone_number TEXT,
                food_item TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity BETWEEN 1 AND 99),
                order_type TEXT NOT NULL CHECK (order_type IN ('normal', 'priority')),
                priority INTEGER,
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'completed')),
                created_at TEXT NOT NULL,
                completed_at TEXT,
                CHECK (
                    (order_type = 'normal' AND priority IS NULL)
                    OR (order_type = 'priority' AND priority BETWEEN 1 AND 5)
                )
            )
            """
        )
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(orders)")}
        if "payment_status" not in columns:
            connection.execute(
                "ALTER TABLE orders ADD COLUMN payment_status TEXT NOT NULL DEFAULT 'pending' "
                "CHECK (payment_status IN ('pending', 'paid'))"
            )
        if "total_amount" not in columns:
            connection.execute("ALTER TABLE orders ADD COLUMN total_amount REAL")

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
                item_name TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity BETWEEN 1 AND 99),
                unit_price REAL,
                line_total REAL,
                is_custom INTEGER NOT NULL DEFAULT 0 CHECK (is_custom IN (0, 1))
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_orders_status_created "
            "ON orders(status, created_at, id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id, id)"
        )
        # Legacy orders had no price history, so NULL means the amount was not recorded.
        connection.execute(
            """
            INSERT INTO order_items (order_id, item_name, quantity, unit_price, line_total, is_custom)
            SELECT orders.id, orders.food_item, orders.quantity, NULL, NULL, 1
            FROM orders
            WHERE NOT EXISTS (
                SELECT 1 FROM order_items WHERE order_items.order_id = orders.id
            )
            """
        )


def _order_from_row(row):
    return dict(row) if row is not None else None


def _get_order_items(connection, order_id):
    rows = connection.execute(
        "SELECT id, item_name, quantity, unit_price, line_total, is_custom "
        "FROM order_items WHERE order_id = ? ORDER BY id",
        (order_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def create_order(database_path, order, items):
    """Insert an order and all detail lines atomically."""
    with database_connection(database_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO orders (
                customer_name, phone_number, food_item, quantity, order_type,
                priority, status, created_at, payment_status, total_amount
            ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, 'pending', ?)
            """,
            (
                order["customer_name"], order["phone_number"], order["food_item"],
                order["quantity"], order["order_type"], order["priority"],
                order["created_at"], order["total_amount"],
            ),
        )
        order_id = cursor.lastrowid
        connection.executemany(
            """
            INSERT INTO order_items (
                order_id, item_name, quantity, unit_price, line_total, is_custom
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (order_id, item["item_name"], item["quantity"], item["unit_price"],
                 item["line_total"], int(item["is_custom"]))
                for item in items
            ],
        )
        saved_order = dict(order)
        saved_order.update(
            id=order_id, status="pending", payment_status="pending",
            completed_at=None, items=[dict(item) for item in items]
        )
        return saved_order


def get_orders(database_path, status=None):
    with database_connection(database_path) as connection:
        if status is None:
            rows = connection.execute("SELECT * FROM orders ORDER BY created_at, id").fetchall()
        else:
            rows = connection.execute(
                "SELECT * FROM orders WHERE status = ? ORDER BY created_at, id", (status,)
            ).fetchall()
        orders = []
        for row in rows:
            order = _order_from_row(row)
            order["items"] = _get_order_items(connection, order["id"])
            orders.append(order)
    return orders


def get_completed_orders(database_path):
    with database_connection(database_path) as connection:
        rows = connection.execute(
            "SELECT * FROM orders WHERE status = ? ORDER BY completed_at DESC, id DESC",
            ("completed",),
        ).fetchall()
        orders = []
        for row in rows:
            order = _order_from_row(row)
            order["items"] = _get_order_items(connection, order["id"])
            orders.append(order)
    return orders


def get_order(database_path, order_id):
    with database_connection(database_path) as connection:
        row = connection.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        order = _order_from_row(row)
        if order is not None:
            order["items"] = _get_order_items(connection, order_id)
    return order


def complete_order(database_path, order_id, completed_at):
    with database_connection(database_path) as connection:
        cursor = connection.execute(
            "UPDATE orders SET status = ?, completed_at = ? WHERE id = ? AND status = ?",
            ("completed", completed_at, order_id, "pending"),
        )
        return cursor.rowcount == 1


def set_payment_status(database_path, order_id, payment_status):
    if payment_status not in {"pending", "paid"}:
        return False
    with database_connection(database_path) as connection:
        cursor = connection.execute(
            "UPDATE orders SET payment_status = ? WHERE id = ?",
            (payment_status, order_id),
        )
        return cursor.rowcount == 1


def reset_orders(database_path):
    with database_connection(database_path) as connection:
        connection.execute("DELETE FROM order_items")
        connection.execute("DELETE FROM orders")
