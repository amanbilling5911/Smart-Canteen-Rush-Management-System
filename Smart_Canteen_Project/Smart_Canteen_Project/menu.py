"""Central menu catalogue; prices are in Indian rupees."""

MENU_ITEMS = {
    "masala-dosa": {"name": "Masala Dosa", "price": 80.00},
    "plain-dosa": {"name": "Plain Dosa", "price": 60.00},
    "idli-sambhar": {"name": "Idli Sambhar", "price": 50.00},
    "vada-pav": {"name": "Vada Pav", "price": 30.00},
    "samosa": {"name": "Samosa", "price": 20.00},
    "aloo-paratha": {"name": "Aloo Paratha", "price": 55.00},
    "paneer-paratha": {"name": "Paneer Paratha", "price": 75.00},
    "chole-bhature": {"name": "Chole Bhature", "price": 90.00},
    "chole-kulche": {"name": "Chole Kulche", "price": 75.00},
    "rajma-rice": {"name": "Rajma Rice", "price": 85.00},
    "chole-rice": {"name": "Chole Rice", "price": 80.00},
    "veg-sandwich": {"name": "Veg Sandwich", "price": 55.00},
    "grilled-sandwich": {"name": "Grilled Sandwich", "price": 70.00},
    "paneer-sandwich": {"name": "Paneer Sandwich", "price": 85.00},
    "veg-burger": {"name": "Veg Burger", "price": 65.00},
    "paneer-burger": {"name": "Paneer Burger", "price": 85.00},
    "french-fries": {"name": "French Fries", "price": 60.00},
    "veg-momos": {"name": "Veg Momos", "price": 70.00},
    "paneer-momos": {"name": "Paneer Momos", "price": 90.00},
    "hakka-noodles": {"name": "Hakka Noodles", "price": 90.00},
    "veg-fried-rice": {"name": "Veg Fried Rice", "price": 85.00},
    "pav-bhaji": {"name": "Pav Bhaji", "price": 80.00},
    "aloo-tikki": {"name": "Aloo Tikki", "price": 40.00},
    "gol-gappe": {"name": "Gol Gappe", "price": 40.00},
    "papdi-chaat": {"name": "Papdi Chaat", "price": 60.00},
    "dahi-bhalla": {"name": "Dahi Bhalla", "price": 65.00},
    "tea": {"name": "Tea", "price": 15.00},
    "coffee": {"name": "Coffee", "price": 25.00},
    "cold-coffee": {"name": "Cold Coffee", "price": 60.00},
    "fresh-lime-soda": {"name": "Fresh Lime Soda", "price": 45.00},
}


def find_menu_item_by_name(name):
    """Return a menu record matching a name without regard to letter case."""
    normalized_name = name.strip().casefold()
    for item in MENU_ITEMS.values():
        if item["name"].casefold() == normalized_name:
            return item
    return None
