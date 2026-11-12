import os
import tempfile
import unittest

import app as canteen_app
import database


class CanteenAppTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_directory.name, "orders.sqlite3")
        canteen_app.configure_database(self.database_path)
        canteen_app.app.config["TESTING"] = True
        self.client = canteen_app.app.test_client()

    def tearDown(self):
        self.temp_directory.cleanup()

    def add_order(self, customer, order_type="normal", priority="", phone=""):
        return self.client.post(
            "/add-order",
            data={
                "customer_name": customer,
                "phone_number": phone,
                "food_item": "Masala dosa",
                "quantity": "1",
                "order_type": order_type,
                "priority": priority,
            },
        )

    def test_phone_is_optional_and_supported_formats_are_saved(self):
        self.add_order("No phone")
        self.add_order("Local phone", phone="98765-43210")
        self.add_order("Country code", phone="+91 98765 43210")

        orders = database.get_orders(self.database_path)
        self.assertEqual([order["phone_number"] for order in orders], [None, "9876543210", "+919876543210"])
        self.assertEqual(len(orders), 3)

    def test_invalid_phone_shows_helpful_message_without_saving_order(self):
        self.add_order("Invalid phone", phone="12345")

        response = self.client.get("/")
        self.assertIn(b"Enter a valid Indian mobile number", response.data)
        self.assertEqual(database.get_orders(self.database_path), [])

    def test_pending_order_priority_and_ties_restore_after_restart(self):
        self.add_order("Normal first")
        self.add_order("Priority first", "priority", "5")
        self.add_order("Priority second", "priority", "5")
        self.add_order("Lower priority", "priority", "2")

        canteen_app.configure_database(self.database_path)
        self.assertEqual(
            [order["customer_name"] for order in canteen_app.get_pending_orders()],
            ["Priority first", "Priority second", "Lower priority", "Normal first"],
        )

        self.client.post("/process-next")
        self.assertEqual(database.get_completed_orders(self.database_path)[0]["customer_name"], "Priority first")
        self.assertEqual(len(database.get_orders(self.database_path, status="pending")), 3)
        self.assertEqual(len(database.get_orders(self.database_path, status="completed")), 1)

        canteen_app.configure_database(self.database_path)
        self.assertEqual(len(database.get_completed_orders(self.database_path)), 1)
        self.assertEqual(
            [order["customer_name"] for order in canteen_app.get_pending_orders()],
            ["Priority second", "Lower priority", "Normal first"],
        )

    def test_reset_clears_pending_and_completed_orders(self):
        self.add_order("Pending")
        self.client.post("/process-next")
        self.add_order("Still pending")

        self.client.post("/reset")

        self.assertEqual(database.get_orders(self.database_path), [])
        page = self.client.get("/").data
        self.assertEqual(page.count(b"<strong>0</strong>"), 2)

    def test_multiple_menu_items_save_server_calculated_totals(self):
        self.client.post(
            "/add-order",
            data={
                "customer_name": "Multi item customer",
                "phone_number": "",
                "order_type": "normal",
                "item_kind[]": ["menu", "menu"],
                "menu_key[]": ["masala-dosa", "tea"],
                "custom_name[]": ["", ""],
                "custom_price[]": ["", ""],
                "item_quantity[]": ["2", "3"],
                "unit_price[]": ["0.01", "0.01"],
            },
        )

        order = database.get_orders(self.database_path)[0]
        self.assertEqual(order["quantity"], 5)
        self.assertEqual(order["total_amount"], 205.0)
        self.assertEqual(
            [(item["item_name"], item["quantity"], item["unit_price"], item["line_total"]) for item in order["items"]],
            [("Masala Dosa", 2, 80.0, 160.0), ("Tea", 3, 15.0, 45.0)],
        )

    def test_custom_item_requires_valid_name_quantity_and_price(self):
        response = self.client.post(
            "/add-order",
            data={
                "customer_name": "Custom customer",
                "order_type": "normal",
                "item_kind[]": ["custom"],
                "menu_key[]": ["__custom__"],
                "custom_name[]": ["Campus special"],
                "custom_price[]": ["invalid"],
                "item_quantity[]": ["1"],
            },
            follow_redirects=True,
        )
        self.assertIn(b"Enter a valid custom item price", response.data)
        self.assertEqual(database.get_orders(self.database_path), [])

        self.client.post(
            "/add-order",
            data={
                "customer_name": "Custom customer",
                "order_type": "normal",
                "item_kind[]": ["custom"],
                "menu_key[]": ["__custom__"],
                "custom_name[]": ["Campus special"],
                "custom_price[]": ["42.50"],
                "item_quantity[]": ["2"],
            },
        )
        order = database.get_orders(self.database_path)[0]
        self.assertEqual(order["items"][0]["line_total"], 85.0)
        self.assertEqual(order["total_amount"], 85.0)

    def test_payment_details_completion_and_bill_persist(self):
        self.client.post(
            "/add-order",
            data={
                "customer_name": "Receipt customer",
                "order_type": "priority",
                "priority": "4",
                "item_kind[]": ["menu", "menu"],
                "menu_key[]": ["samosa", "coffee"],
                "custom_name[]": ["", ""],
                "custom_price[]": ["", ""],
                "item_quantity[]": ["2", "1"],
            },
        )
        order = database.get_orders(self.database_path)[0]
        order_id = order["id"]

        details = self.client.get(f"/orders/{order_id}/details")
        self.assertEqual(details.status_code, 200)
        self.assertEqual(details.get_json()["total_amount"], 65.0)
        self.assertEqual(len(details.get_json()["items"]), 2)

        self.client.post(f"/orders/{order_id}/payment", data={"payment_status": "paid"})
        self.assertEqual(database.get_order(self.database_path, order_id)["payment_status"], "paid")
        self.assertEqual(
            self.client.post(f"/orders/{order_id}/payment", data={"payment_status": "captured"}).status_code,
            302,
        )
        self.assertEqual(database.get_order(self.database_path, order_id)["payment_status"], "paid")

        self.client.post("/process-next")
        canteen_app.configure_database(self.database_path)
        completed = database.get_order(self.database_path, order_id)
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["payment_status"], "paid")
        bill = self.client.get(f"/orders/{order_id}/bill")
        self.assertEqual(bill.status_code, 200)
        self.assertIn(b"Print bill", bill.data)
        self.assertIn(b"Samosa", bill.data)
        self.assertIn(b"Coffee", bill.data)
        self.assertIn(b"65.00", bill.data)

    def test_empty_queue_and_missing_order_details_are_safe(self):
        response = self.client.post("/process-next", follow_redirects=True)
        self.assertIn(b"There are no pending orders", response.data)
        self.assertEqual(self.client.get("/orders/999/details").status_code, 404)
        self.assertEqual(self.client.get("/orders/999/bill").status_code, 404)


if __name__ == "__main__":
    unittest.main()
