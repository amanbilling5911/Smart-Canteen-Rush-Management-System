from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import os
import re
from threading import RLock

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

import database
from menu import MENU_ITEMS, find_menu_item_by_name
from priority_queue import PriorityOrderQueue
from queue_system import OrderQueue

app = Flask(__name__)
app.config["SECRET_KEY"] = "smart-canteen-demo-key"
app.config["DATABASE"] = os.path.join(app.root_path, "canteen_orders.sqlite3")
app.config["MAX_ORDER_ITEMS"] = 20

normal_orders = OrderQueue()
priority_orders = PriorityOrderQueue()
orders_lock = RLock()


def format_time(value):
    if not value:
        return "—"
    return datetime.fromisoformat(value).astimezone().strftime("%d %b %Y, %I:%M %p")


def prepare_display_order(order):
    display_order = dict(order)
    display_order["created_at_display"] = format_time(order.get("created_at"))
    display_order["completed_at_display"] = format_time(order.get("completed_at"))
    display_order["total_amount"] = (
        float(order["total_amount"]) if order.get("total_amount") is not None else None
    )
    for item in display_order.get("items", []):
        if item.get("unit_price") is not None:
            item["unit_price"] = float(item["unit_price"])
            item["line_total"] = float(item["line_total"])
    return display_order


def restore_pending_orders():
    """Rebuild the algorithm queues from pending rows in database arrival order."""
    global normal_orders, priority_orders
    normal_orders = OrderQueue()
    priority_orders = PriorityOrderQueue()
    for order in database.get_orders(app.config["DATABASE"], status="pending"):
        if order["order_type"] == "priority":
            priority_orders.enqueue(order, order["priority"])
        else:
            normal_orders.enqueue(order)


def configure_database(database_path):
    app.config["DATABASE"] = database_path
    database.initialize_database(database_path)
    with orders_lock:
        restore_pending_orders()


def get_pending_orders():
    orders = priority_orders.get_all() + normal_orders.get_all()
    return [prepare_display_order(order) for order in orders]


def normalize_indian_phone(phone_number):
    compact_number = re.sub(r"[\s-]", "", phone_number)
    if not compact_number:
        return None
    if not re.fullmatch(r"(?:\+91)?[6-9]\d{9}", compact_number):
        return ""
    return compact_number


def parse_quantity(value):
    try:
        quantity = int(value)
    except (TypeError, ValueError):
        raise ValueError("Each item quantity must be a whole number.") from None
    if quantity < 1 or quantity > 99:
        raise ValueError("Each item quantity must be between 1 and 99.")
    return quantity


def parse_custom_price(value):
    try:
        price = Decimal(value)
    except (InvalidOperation, TypeError):
        raise ValueError("Enter a valid custom item price.") from None
    if not price.is_finite() or price <= 0 or price > Decimal("100000"):
        raise ValueError("Custom item price must be greater than ₹0 and at most ₹100,000.")
    if price.as_tuple().exponent < -2:
        raise ValueError("Custom item prices can have at most two decimal places.")
    return price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def read_order_items(form):
    item_kinds = form.getlist("item_kind[]")
    menu_keys = form.getlist("menu_key[]")
    custom_names = form.getlist("custom_name[]")
    custom_prices = form.getlist("custom_price[]")
    quantities = form.getlist("item_quantity[]")

    # Keep the previous single-item form payload usable for bookmarked/manual clients.
    if not item_kinds and form.get("food_item"):
        legacy_name = form.get("food_item", "").strip()
        menu_match = find_menu_item_by_name(legacy_name)
        item_kinds = ["menu" if menu_match else "custom"]
        menu_keys = [next((key for key, value in MENU_ITEMS.items() if value is menu_match), "")]
        custom_names = [legacy_name]
        custom_prices = [form.get("custom_price", "")]
        quantities = [form.get("quantity", "")]

    if not item_kinds or len(item_kinds) > app.config["MAX_ORDER_ITEMS"]:
        raise ValueError(f"Add between 1 and {app.config['MAX_ORDER_ITEMS']} items to an order.")
    if not all(len(values) == len(item_kinds) for values in (menu_keys, custom_names, custom_prices, quantities)):
        raise ValueError("One or more item details are missing. Please check each item row.")

    items = []
    for index, kind in enumerate(item_kinds):
        quantity = parse_quantity(quantities[index])
        if kind == "menu":
            key = menu_keys[index]
            menu_item = MENU_ITEMS.get(key)
            if menu_item is None:
                raise ValueError("Choose a valid item from the canteen menu.")
            name = menu_item["name"]
            unit_price = Decimal(str(menu_item["price"])).quantize(Decimal("0.01"))
            is_custom = False
        elif kind == "custom":
            name = custom_names[index].strip()
            if not name or len(name) > 100:
                raise ValueError("Custom item names must contain 1 to 100 characters.")
            unit_price = parse_custom_price(custom_prices[index])
            is_custom = True
        else:
            raise ValueError("Choose a menu item or enter a custom item.")

        line_total = (unit_price * quantity).quantize(Decimal("0.01"))
        items.append({
            "item_name": name,
            "quantity": quantity,
            "unit_price": float(unit_price),
            "line_total": float(line_total),
            "is_custom": is_custom,
        })

    if sum(item["quantity"] for item in items) > 99:
        raise ValueError("The total quantity in one order cannot exceed 99.")
    return items


def order_summary(items):
    subtotal = sum((Decimal(str(item["line_total"])) for item in items), Decimal("0.00"))
    return subtotal.quantize(Decimal("0.01"))


def prepare_order_for_database(customer_name, phone_number, order_type, priority, items):
    total = order_summary(items)
    item_names = ", ".join(item["item_name"] for item in items)
    return {
        "customer_name": customer_name,
        "phone_number": phone_number,
        "food_item": item_names[:500],
        "quantity": sum(item["quantity"] for item in items),
        "order_type": order_type,
        "priority": priority,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total_amount": float(total),
    }


def order_for_detail(order_id):
    order = database.get_order(app.config["DATABASE"], order_id)
    return prepare_display_order(order) if order else None


def menu_with_keys():
    return [{"key": key, **item} for key, item in MENU_ITEMS.items()]


database.initialize_database(app.config["DATABASE"])
restore_pending_orders()


@app.route("/", methods=["GET"])
def index():
    with orders_lock:
        pending_orders = get_pending_orders()
        completed_orders = [
            prepare_display_order(order)
            for order in database.get_completed_orders(app.config["DATABASE"])
        ]
    return render_template(
        "index.html",
        pending_orders=pending_orders,
        completed_orders=completed_orders,
        menu_items=menu_with_keys(),
    )


@app.route("/add-order", methods=["POST"])
def add_order():
    customer_name = request.form.get("customer_name", "").strip()
    phone_input = request.form.get("phone_number", "").strip()
    order_type = request.form.get("order_type", "normal").strip().lower()
    if not customer_name or len(customer_name) > 80:
        flash("Customer name is required and must be at most 80 characters.", "error")
        return redirect(url_for("index"))
    phone_number = normalize_indian_phone(phone_input)
    if phone_number == "":
        flash("Enter a valid Indian mobile number, such as 9876543210 or +919876543210.", "error")
        return redirect(url_for("index"))
    if order_type not in {"normal", "priority"}:
        flash("Choose either a normal or priority order.", "error")
        return redirect(url_for("index"))

    priority = None
    if order_type == "priority":
        try:
            priority = int(request.form.get("priority", ""))
        except (TypeError, ValueError):
            flash("Choose a priority level from 1 to 5.", "error")
            return redirect(url_for("index"))
        if priority < 1 or priority > 5:
            flash("Priority level must be from 1 to 5.", "error")
            return redirect(url_for("index"))

    try:
        items = read_order_items(request.form)
    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("index"))

    order = prepare_order_for_database(customer_name, phone_number, order_type, priority, items)
    with orders_lock:
        saved_order = database.create_order(app.config["DATABASE"], order, items)
        if order_type == "priority":
            priority_orders.enqueue(saved_order, priority)
        else:
            normal_orders.enqueue(saved_order)

    flash(f"Order #{saved_order['id']} was added. Total: ₹{order['total_amount']:.2f}.", "success")
    return redirect(url_for("index"))


@app.route("/process-next", methods=["POST"])
def process_next():
    with orders_lock:
        queue = priority_orders if not priority_orders.is_empty() else normal_orders
        order = queue.peek()
        if order is None:
            flash("There are no pending orders to process.", "error")
        else:
            completed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            if database.complete_order(app.config["DATABASE"], order["id"], completed_at):
                queue.dequeue()
                flash(f"Order #{order['id']} for {order['customer_name']} is complete.", "success")
            else:
                restore_pending_orders()
                flash("That order was already processed. The queue has been refreshed.", "error")
    return redirect(url_for("index"))


@app.route("/orders/<int:order_id>/details", methods=["GET"])
def order_details(order_id):
    order = order_for_detail(order_id)
    if order is None:
        return jsonify({"error": "Order not found."}), 404
    return jsonify(order)


@app.route("/orders/<int:order_id>/payment", methods=["POST"])
def update_payment(order_id):
    payment_status = request.form.get("payment_status", "")
    if payment_status not in {"pending", "paid"}:
        flash("Choose a valid demo payment status.", "error")
    elif not database.set_payment_status(app.config["DATABASE"], order_id, payment_status):
        flash("Order not found; payment status was not changed.", "error")
    else:
        label = "Paid" if payment_status == "paid" else "Pending"
        flash(f"Demo payment status for order #{order_id} is now {label}.", "success")
    return redirect(url_for("index") + f"#order-{order_id}")


@app.route("/orders/<int:order_id>/bill", methods=["GET"])
def order_bill(order_id):
    order = order_for_detail(order_id)
    if order is None:
        return render_template("not_found.html"), 404
    return render_template("bill.html", order=order)


@app.route("/reset", methods=["POST"])
def reset():
    with orders_lock:
        database.reset_orders(app.config["DATABASE"])
        restore_pending_orders()
    flash("All pending and completed demo orders have been cleared.", "success")
    return redirect(url_for("index"))


@app.errorhandler(404)
def not_found(_error):
    return render_template("not_found.html"), 404


if __name__ == "__main__":
    app.run(debug=True)
