# Smart Canteen Rush Management System

A beginner-friendly Flask application for managing a busy college canteen. The project combines FIFO and priority queues with SQLite-backed multi-item orders, an editable food menu, demo payment tracking, and printable receipts.

## Objectives

- Serve normal orders fairly in arrival order and priority orders by urgency.
- Let a customer create one order containing multiple menu or custom food items.
- Calculate item and order totals on the server and keep an order history across restarts.
- Track service completion separately from a simple demo payment status.
- Provide a responsive counter dashboard and a printable bill for each order.

## Technologies and files

- Python, Flask, HTML, CSS, JavaScript, SQLite (`sqlite3`), and `unittest`.
- `app.py` contains the routes, server-side validation, queue restoration, and amount calculations.
- `database.py` initializes/migrates the local schema and performs parameterized SQLite reads and writes.
- `menu.py` is the central menu and INR price configuration. Edit `MENU_ITEMS` there to update names and prices.
- `queue_system.py` implements normal-order FIFO with `collections.deque`.
- `priority_queue.py` implements priority service with `heapq` and arrival sequence tie-breaking.
- `templates/index.html` is the order dashboard and details dialog; `templates/bill.html` is the receipt; `templates/not_found.html` handles unknown orders.
- `static/style.css` defines the forest-green glass design, responsive layout, and print styles.
- `static/images/temporary-canteen-hero.svg` is the local temporary food visual; `static/images/smart-canteen-logo.svg` is the original logo.
- `tests/` contains queue, database migration, and Flask integration tests.
- `canteen_orders.sqlite3` is created automatically in this project folder. It is local application data, not source code.

Flask is the only dependency to install. SQLite is built into Python. The local SVG artwork avoids external image requests at runtime.

## Database schema and migration

`orders` stores the order ID, customer name, optional phone number, order type, priority, service status, demo payment status, timestamps, and server-calculated total. `order_items` stores each line's food name, quantity, unit price, line total, and whether it is custom; each line references its parent order.

At startup, `database.py` creates missing tables and adds missing total/payment columns safely. Original single-item orders are retained and receive a detail row with a `NULL` historical price because the old database never recorded prices. The app does not invent historical totals. New orders and all their item rows are committed in one transaction. SQL values use placeholders. A guarded update only completes an order still marked pending.

## Menu and multi-item totals

The menu has 30 Indian canteen items. The `menu.py` catalogue is the single place to adjust the illustrative INR prices. The browser previews unit prices, line totals, and the subtotal as quantities or selections change. Submitted menu prices are ignored: `app.py` looks up the selected menu key and recalculates all amounts on the server. Custom foods require a non-empty name, positive price (up to ₹100,000 with at most two decimal places), and a valid quantity. An order can contain up to 20 item rows and 99 total units. No tax or service fee is added, so the subtotal is the bill total.

## Queue and payment behavior

Normal orders enter a `deque`; adding and removing at the ends are **O(1)**. Priority orders enter a binary heap as `(-priority, sequence, order)`, so a larger priority number is served first and earlier arrivals win equal-priority ties. Heap insertion and removal are **O(log n)**. On restart, pending SQLite rows are restored in creation/ID order, rebuilding the same FIFO and priority tie behavior. Completed orders remain in SQLite and are not enqueued again.

Payment is an independent `pending`/`paid` field used only as a demo tracker. Marking an order paid does not collect money; there is no gateway, SMS, or payment confirmation integration. Payment changes use a server-side POST and persist in SQLite.

## Order details and bill printing

Click a pending or completed order row to load its saved details and item lines. Phone numbers are not shown in the queue tables; they appear in that order's details and receipt only when provided. The receipt is generated from the stored order and item rows, shows whether the order is pending or completed, and has a browser print action. If a historical order has no saved price, its receipt says the price was not recorded. The print stylesheet hides the dashboard-only controls. A pending order's receipt is clearly labelled pending.

## Install and run on Windows

Open the project folder in VS Code with **File > Open Folder...**, or from its parent folder run `code .\Smart_Canteen_Project`. In a PowerShell terminal opened in the project folder:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

If PowerShell blocks activation, activate from Command Prompt with `.venv\Scripts\activate.bat`, then run the install and application commands. Browse to **http://127.0.0.1:5000**. Stop Flask with `Ctrl+C`.

## Run tests

From the project folder with the environment active:

```powershell
python -m unittest discover -s tests -v
```

Integration and migration tests use temporary database files so the saved project history is not reset by the tests.

## Replace the visual assets

Place your own image in `static/images/` and replace `temporary-canteen-hero.svg` while keeping its filename, or update the hero image source in `templates/index.html`. The image is local and can be a PNG, JPG, or SVG; keep an appropriate `alt` description. Replace `smart-canteen-logo.svg` with your own logo using the same filename. No Python changes or remote image service are needed.

## Future scope

Possible academic extensions include staff login, menu availability, daily sales reports, exportable receipts, and role-based access. A production payment provider would require a separately designed secure integration; the current payment status is intentionally only a local demonstration.
