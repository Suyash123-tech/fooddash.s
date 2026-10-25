import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import html
import math
import os
import random
import re
import secrets
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime
from http.cookies import CookieError, SimpleCookie
from urllib.parse import urlsplit

# AI Food Delivery Demo
# Runs with Python's standard library; no packages or API keys needed.
# Start the browser chatbot with: python assignment.py --web

DATA_FILE = Path(__file__).with_name("food_delivery_data.json")
ORDER_DB_FILE = Path(os.environ.get("FOODDASH_DB_PATH", Path(__file__).with_name("food_delivery_orders.sqlite3")))
DEMO_TAX_RATE = 0.05  # Sample rate for the assignment demo; change as needed.
ADMIN_COOKIE_NAME = "fooddash_admin"
ADMIN_SESSION_SECONDS = 12 * 60 * 60
ADMIN_LOGIN_WINDOW_SECONDS = 15 * 60
ADMIN_LOGIN_MAX_ATTEMPTS = 5

# Example neighborhoods and restaurant locations on a simple map (x, y).
LOCATIONS = {
    "Campus": (0, 0),
    "North": (0, 4),
    "South": (0, -4),
    "East": (4, 0),
    "West": (-4, 0),
}

MENU = [
    {"id": 1, "name": "Paneer Wrap", "restaurant": "Green Bowl", "location": "Campus", "category": "vegetarian", "price": 150, "prep": 12, "rating": 4.7, "tags": ["paneer", "spicy", "wrap"]},
    {"id": 2, "name": "Veggie Burger", "restaurant": "Green Bowl", "location": "Campus", "category": "vegetarian", "price": 180, "prep": 15, "rating": 4.5, "tags": ["burger", "cheese", "mild"]},
    {"id": 3, "name": "Masala Dosa", "restaurant": "South Spice", "location": "South", "category": "vegetarian", "price": 120, "prep": 14, "rating": 4.6, "tags": ["south indian", "spicy", "crispy"]},
    {"id": 4, "name": "Veg Thali", "restaurant": "South Spice", "location": "South", "category": "vegetarian", "price": 210, "prep": 18, "rating": 4.8, "tags": ["indian", "thali", "mild"]},
    {"id": 5, "name": "Chicken Biryani", "restaurant": "Spice Route", "location": "East", "category": "non-vegetarian", "price": 240, "prep": 20, "rating": 4.8, "tags": ["chicken", "rice", "spicy"]},
    {"id": 6, "name": "Chicken Sandwich", "restaurant": "North Kitchen", "location": "North", "category": "non-vegetarian", "price": 170, "prep": 10, "rating": 4.3, "tags": ["chicken", "sandwich", "mild"]},
    {"id": 7, "name": "Falafel Bowl", "restaurant": "Green Bowl", "location": "Campus", "category": "vegan", "price": 190, "prep": 13, "rating": 4.6, "tags": ["vegan", "healthy", "mild"]},
    {"id": 8, "name": "Mushroom Noodles", "restaurant": "West Wok", "location": "West", "category": "vegan", "price": 160, "prep": 11, "rating": 4.4, "tags": ["vegan", "noodles", "spicy"]},
    {"id": 9, "name": "Aloo Tikki Burger", "restaurant": "Green Bowl", "location": "Campus", "category": "vegetarian", "price": 130, "prep": 12, "rating": 4.5, "tags": ["burger", "potato", "crispy"]},
    {"id": 10, "name": "Chole Rice Bowl", "restaurant": "South Spice", "location": "South", "category": "vegan", "price": 175, "prep": 16, "rating": 4.6, "tags": ["chickpea", "rice", "spicy", "vegan"]},
    {"id": 11, "name": "Margherita Pizza", "restaurant": "Campus Oven", "location": "Campus", "category": "vegetarian", "price": 220, "prep": 18, "rating": 4.7, "tags": ["pizza", "cheese", "basil"]},
    {"id": 12, "name": "Paneer Tikka Bowl", "restaurant": "Spice Route", "location": "East", "category": "vegetarian", "price": 230, "prep": 19, "rating": 4.8, "tags": ["paneer", "tikka", "spicy"]},
    {"id": 13, "name": "Veg Hakka Noodles", "restaurant": "West Wok", "location": "West", "category": "vegan", "price": 180, "prep": 14, "rating": 4.5, "tags": ["noodles", "vegan", "mild"]},
    {"id": 14, "name": "Grilled Chicken Bowl", "restaurant": "North Kitchen", "location": "North", "category": "non-vegetarian", "price": 260, "prep": 18, "rating": 4.8, "tags": ["chicken", "healthy", "rice"]},
    {"id": 15, "name": "Egg Masala Roll", "restaurant": "Spice Route", "location": "East", "category": "non-vegetarian", "price": 145, "prep": 11, "rating": 4.4, "tags": ["egg", "roll", "spicy"]},
    {"id": 16, "name": "Rajma Chawal", "restaurant": "South Spice", "location": "South", "category": "vegan", "price": 160, "prep": 17, "rating": 4.6, "tags": ["kidney beans", "rice", "vegan"]},
    {"id": 17, "name": "BBQ Chicken Wrap", "restaurant": "North Kitchen", "location": "North", "category": "non-vegetarian", "price": 210, "prep": 13, "rating": 4.5, "tags": ["chicken", "wrap", "barbecue"]},
    {"id": 18, "name": "Spinach Corn Sandwich", "restaurant": "Green Bowl", "location": "Campus", "category": "vegetarian", "price": 155, "prep": 10, "rating": 4.3, "tags": ["spinach", "corn", "sandwich"]},
    {"id": 19, "name": "Tofu Stir-Fry", "restaurant": "West Wok", "location": "West", "category": "vegan", "price": 205, "prep": 16, "rating": 4.7, "tags": ["tofu", "healthy", "spicy"]},
    {"id": 20, "name": "Fish Curry Rice", "restaurant": "Coastal Kitchen", "location": "East", "category": "non-vegetarian", "price": 280, "prep": 22, "rating": 4.8, "tags": ["fish", "curry", "rice", "spicy"]},
    {"id": 21, "name": "Mushroom Cheese Toast", "restaurant": "Campus Oven", "location": "Campus", "category": "vegetarian", "price": 140, "prep": 9, "rating": 4.4, "tags": ["mushroom", "cheese", "toast"]},
    {"id": 22, "name": "Lentil Quinoa Salad", "restaurant": "Green Bowl", "location": "Campus", "category": "vegan", "price": 215, "prep": 15, "rating": 4.7, "tags": ["lentil", "quinoa", "healthy", "vegan"]},
    {"id": 23, "name": "Chicken Tikka Rice", "restaurant": "Spice Route", "location": "East", "category": "non-vegetarian", "price": 250, "prep": 20, "rating": 4.7, "tags": ["chicken", "rice", "tikka", "spicy"]},
]

MEAL_EMOJIS = {
    "Paneer Wrap": "🌯",
    "Veggie Burger": "🍔",
    "Masala Dosa": "🥞",
    "Veg Thali": "🍛",
    "Chicken Biryani": "🍲",
    "Chicken Sandwich": "🥪",
    "Falafel Bowl": "🥙",
    "Mushroom Noodles": "🍜",
    "Aloo Tikki Burger": "🍔",
    "Chole Rice Bowl": "🍚",
    "Margherita Pizza": "🍕",
    "Paneer Tikka Bowl": "🍢",
    "Veg Hakka Noodles": "🍜",
    "Grilled Chicken Bowl": "🍗",
    "Egg Masala Roll": "🌯",
    "Rajma Chawal": "🍛",
    "BBQ Chicken Wrap": "🌯",
    "Spinach Corn Sandwich": "🥪",
    "Tofu Stir-Fry": "🥘",
    "Fish Curry Rice": "🐟",
    "Mushroom Cheese Toast": "🍞",
    "Lentil Quinoa Salad": "🥗",
    "Chicken Tikka Rice": "🍗",
}
CHAT_SESSIONS = {}
CHAT_SESSIONS_LOCK = threading.Lock()
ADMIN_SESSIONS = {}
ADMIN_SESSIONS_LOCK = threading.Lock()
ADMIN_LOGIN_ATTEMPTS = {}
ADMIN_LOGIN_ATTEMPTS_LOCK = threading.Lock()
MAX_CHAT_REQUEST_BYTES = 4096
ORDER_STATUSES = (
    "Restaurant is preparing your food",
    "Out for delivery",
    "Delivered",
    "Cancelled",
)


def load_data():
    """Load saved customer order history; start fresh if there is no data yet."""
    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, dict):
            data.setdefault("order_history", [])
            data.setdefault("orders", [])
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"order_history": [], "orders": []}


def save_data(data):
    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def read_number(prompt, minimum, maximum=None):
    while True:
        raw = input(prompt).strip()
        try:
            value = int(raw)
            if value < minimum or (maximum is not None and value > maximum):
                raise ValueError
            return value
        except ValueError:
            limit = f" and at most {maximum}" if maximum is not None else ""
            print(f"Please enter a whole number of at least {minimum}{limit}.")


def choose_location():
    names = list(LOCATIONS)
    print("\nChoose your delivery area:")
    for number, name in enumerate(names, start=1):
        print(f"  {number}. {name}")
    choice = read_number("Area number: ", 1, len(names))
    return names[choice - 1]


def distance_km(customer_location, restaurant_location):
    x1, y1 = LOCATIONS[customer_location]
    x2, y2 = LOCATIONS[restaurant_location]
    # Each map unit represents about 1.2 km.
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2) * 1.2


def estimate_delivery(meal, customer_location):
    distance = distance_km(customer_location, meal["location"])
    travel_minutes = max(5, math.ceil(distance * 3))
    return distance, meal["prep"] + travel_minutes


def recommendation_score(meal, budget, eta, history):
    """Score meals using ratings, budget fit, delivery time, and past orders."""
    past_orders = sum(1 for item in history if item == meal["name"])
    budget_fit = max(0, (budget - meal["price"]) / max(budget, 1))
    return (
        meal["rating"] * 2.0
        + budget_fit * 3.0
        + max(0, 30 - eta) / 10.0
        + min(past_orders, 3) * 1.5
    )


def chat_reply(message, conversation_id, order_history, orders=None):
    """Return a local, rule-based chatbot reply and matching meals."""
    text = message.strip()
    normalized = text.lower()
    if not text:
        return {"reply": "Type what you're craving and I'll look for a match.", "meals": []}

    if re.search(r"\b(reset|start over|clear preferences)\b", normalized):
        with CHAT_SESSIONS_LOCK:
            CHAT_SESSIONS.pop(conversation_id, None)
        return {"reply": "All set — I cleared those filters. Tell me what kind of meal you're in the mood for.", "meals": []}

    if re.search(r"\b(order history|my orders|track order|past orders)\b", normalized):
        recent_orders = (orders or [])[-3:][::-1]
        if recent_orders:
            summary = ", ".join(
                f"#{order.get('order_id', '—')}, {order.get('meal', 'meal')} ({order.get('status', 'status unavailable')})"
                for order in recent_orders
            )
            return {"reply": f"Your latest orders: {summary}.", "meals": []}
        return {"reply": "You don't have any saved orders yet. Tell me what you'd like to eat and I'll find some options.", "meals": []}

    if re.match(r"^(hi|hello|hey|good morning|good afternoon)\b", normalized):
        return {"reply": "Hi! What are you craving? Mention a food type, budget, delivery area, or time limit.", "meals": []}
    if re.search(r"\b(help|what can you do)\b", normalized):
        return {"reply": "I can suggest meals from our sample menu. Try “vegan under ₹200 near Campus”, “something spicy in 30 minutes”, or ask about your orders.", "meals": []}

    with CHAT_SESSIONS_LOCK:
        preferences = CHAT_SESSIONS.setdefault(conversation_id, {
            "category": "all",
            "budget": 250,
            "max_eta": 45,
            "location": "Campus",
            "tags": [],
            "meal_name": "",
        })
        if re.search(r"\bvegan\b", normalized):
            preferences["category"] = "vegan"
        elif re.search(r"\bnon[\s-]?vegetarian\b|\bnon[\s-]?veg\b|\bchicken\b|\bmeat\b|\bfish\b", normalized):
            preferences["category"] = "non-vegetarian"
        elif re.search(r"\bvegetarian\b|\bveg\b", normalized):
            preferences["category"] = "vegetarian"
        elif re.search(r"\b(any|all) (food|type|category|meal)s?\b", normalized):
            preferences["category"] = "all"

        amount = re.search(
            r"(?:under|below|less than|budget(?: of)?|max(?:imum)?(?: budget)?|₹|rs\.?)\s*₹?\s*(\d{2,5})(?!\s*(?:minutes?|mins?|min\b))",
            normalized,
        )
        if amount:
            preferences["budget"] = int(amount.group(1))
        else:
            amount = re.search(r"\b(\d{2,5})\s*(?:rupees|rs\.?)\b", normalized)
            if amount:
                preferences["budget"] = int(amount.group(1))

        time_limit = re.search(
            r"(?:within|in|under|below|max(?:imum)?|ready in)\s*(\d{1,2})\s*(?:minutes?|mins?|min\b)",
            normalized,
        )
        if time_limit:
            preferences["max_eta"] = int(time_limit.group(1))

        for area in LOCATIONS:
            if re.search(rf"\b{re.escape(area)}\b", text, re.IGNORECASE):
                preferences["location"] = area
                break

        found_tags = {
            tag
            for meal in MENU
            for tag in meal["tags"]
            if tag in normalized
        }
        if found_tags:
            preferences["tags"] = sorted(found_tags)

        named_meal = next((meal for meal in MENU if meal["name"].lower() in normalized), None)
        if named_meal:
            preferences["meal_name"] = named_meal["name"]
            preferences["category"] = "all"

        active_preferences = dict(preferences)

    has_preferences = (
        active_preferences["category"] != "all"
        or active_preferences["budget"] != 250
        or active_preferences["max_eta"] != 45
        or active_preferences["location"] != "Campus"
        or active_preferences["tags"]
        or active_preferences["meal_name"]
    )
    if not has_preferences and not re.search(r"\b(recommend|suggest|hungry|food|meal|eat|craving|menu)\b", normalized):
        return {"reply": "I can help find a meal. Try a food type, something spicy, a meal under ₹200, or options near North.", "meals": []}

    matches = []
    for meal in MENU:
        if active_preferences["category"] != "all" and meal["category"] != active_preferences["category"]:
            continue
        if meal["price"] > active_preferences["budget"]:
            continue
        distance, eta = estimate_delivery(meal, active_preferences["location"])
        if eta > active_preferences["max_eta"]:
            continue
        if active_preferences["meal_name"] and meal["name"] != active_preferences["meal_name"]:
            continue
        if active_preferences["tags"] and not any(tag in meal["tags"] for tag in active_preferences["tags"]):
            continue
        score = recommendation_score(meal, active_preferences["budget"], eta, order_history)
        matches.append((score, meal, distance, eta))

    matches.sort(key=lambda row: row[0], reverse=True)
    if not matches:
        return {
            "reply": (
                f"I couldn't find a match under ₹{active_preferences['budget']} and within "
                f"{active_preferences['max_eta']} minutes near {active_preferences['location']}. "
                "Try a higher budget or delivery time."
            ),
            "location": active_preferences["location"],
            "meals": [],
        }

    reply = (
        f"Here are my top picks near {active_preferences['location']} "
        f"(up to ₹{active_preferences['budget']}, ready within {active_preferences['max_eta']} minutes):"
    )
    meals = [
        {
            "id": meal["id"],
            "name": meal["name"],
            "restaurant": meal["restaurant"],
            "category": meal["category"],
            "price": meal["price"],
            "rating": meal["rating"],
            "emoji": MEAL_EMOJIS[meal["name"]],
            "distance": round(distance, 1),
            "eta": eta,
        }
        for _, meal, distance, eta in matches[:3]
    ]
    return {"reply": reply, "location": active_preferences["location"], "meals": meals}


@contextmanager
def open_order_database():
    ORDER_DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(ORDER_DB_FILE, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_order_database():
    with open_order_database() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY,
                meal TEXT NOT NULL,
                restaurant TEXT NOT NULL,
                area TEXT NOT NULL,
                customer_name TEXT NOT NULL,
                customer_phone TEXT NOT NULL,
                delivery_address TEXT NOT NULL,
                subtotal REAL NOT NULL,
                delivery_fee REAL NOT NULL,
                tax REAL NOT NULL,
                total REAL NOT NULL,
                eta_minutes INTEGER NOT NULL,
                status TEXT NOT NULL,
                issued_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                delivery_deadline REAL,
                items_json TEXT NOT NULL DEFAULT '[]'
            )
            """
        )
        columns = {
            column["name"]
            for column in connection.execute("PRAGMA table_info(orders)").fetchall()
        }
        if "delivery_deadline" not in columns:
            connection.execute("ALTER TABLE orders ADD COLUMN delivery_deadline REAL")
        if "items_json" not in columns:
            connection.execute("ALTER TABLE orders ADD COLUMN items_json TEXT NOT NULL DEFAULT '[]'")
        connection.execute(
            """
            UPDATE orders
            SET delivery_deadline = CAST(strftime('%s', created_at) AS REAL) + eta_minutes * 60
            WHERE delivery_deadline IS NULL
            """
        )


def serialize_order(row):
    order = dict(row)
    order["items"] = json.loads(order.pop("items_json", "[]"))
    if not order["items"]:
        order["items"] = [{
            "name": order["meal"],
            "restaurant": order["restaurant"],
            "quantity": 1,
            "unit_price": order["subtotal"],
            "line_total": order["subtotal"],
        }]
    return order


class FoodDashRequestHandler(BaseHTTPRequestHandler):
    def send_json(self, status, data, cookie=None):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(payload)

    def read_json_body(self):
        if self.headers.get_content_type() != "application/json":
            self.send_json(415, {"error": "Send requests as JSON."})
            return None
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_json(400, {"error": "Invalid request length."})
            return None
        if content_length < 1 or content_length > MAX_CHAT_REQUEST_BYTES:
            self.send_json(413, {"error": "Request is empty or too large."})
            return None
        try:
            payload = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_json(400, {"error": "Request must contain valid JSON."})
            return None
        if not isinstance(payload, dict):
            self.send_json(400, {"error": "Request must be a JSON object."})
            return None
        return payload

    def request_is_same_origin(self):
        origin = self.headers.get("Origin")
        host = self.headers.get("Host")
        return bool(origin and host and urlsplit(origin).netloc.lower() == host.lower())

    def admin_session_id(self):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
        except CookieError:
            return None
        morsel = cookie.get(ADMIN_COOKIE_NAME)
        if morsel is None:
            return None
        session_id = morsel.value
        with ADMIN_SESSIONS_LOCK:
            expires_at = ADMIN_SESSIONS.get(session_id)
            if expires_at is None:
                return None
            if expires_at <= time.time():
                del ADMIN_SESSIONS[session_id]
                return None
        return session_id

    def require_admin(self):
        if self.admin_session_id() is not None:
            return True
        self.send_json(401, {"error": "Admin login required."})
        return False

    def clear_login_attempts(self, client_ip):
        with ADMIN_LOGIN_ATTEMPTS_LOCK:
            ADMIN_LOGIN_ATTEMPTS.pop(client_ip, None)

    def login_is_limited(self, client_ip):
        now = time.time()
        with ADMIN_LOGIN_ATTEMPTS_LOCK:
            attempts = [
                timestamp
                for timestamp in ADMIN_LOGIN_ATTEMPTS.get(client_ip, [])
                if now - timestamp < ADMIN_LOGIN_WINDOW_SECONDS
            ]
            ADMIN_LOGIN_ATTEMPTS[client_ip] = attempts
            return len(attempts) >= ADMIN_LOGIN_MAX_ATTEMPTS

    def record_failed_login(self, client_ip):
        now = time.time() 
        with ADMIN_LOGIN_ATTEMPTS_LOCK:
            attempts = [
                timestamp
                for timestamp in ADMIN_LOGIN_ATTEMPTS.get(client_ip, [])
                if now - timestamp < ADMIN_LOGIN_WINDOW_SECONDS
            ]
            attempts.append(now)
            ADMIN_LOGIN_ATTEMPTS[client_ip] = attempts

    def handle_admin_login(self):
        if not self.request_is_same_origin():
            self.send_json(403, {"error": "Request origin is not allowed."})
            return
        password = os.environ.get("FOODDASH_ADMIN_PASSWORD", "")
        if not password:
            self.send_json(503, {"error": "Admin login is disabled. Set FOODDASH_ADMIN_PASSWORD before starting the server."})
            return
        client_ip = self.client_address[0]
        if self.login_is_limited(client_ip):
            self.send_json(429, {"error": "Too many login attempts. Try again in 15 minutes."})
            return
        payload = self.read_json_body()
        if payload is None:
            return
        supplied_password = payload.get("password")
        if not isinstance(supplied_password, str) or not hmac.compare_digest(supplied_password, password):
            self.record_failed_login(client_ip)
            self.send_json(401, {"error": "Incorrect admin password."})
            return
        self.clear_login_attempts(client_ip)
        session_id = secrets.token_urlsafe(32)
        with ADMIN_SESSIONS_LOCK:
            ADMIN_SESSIONS[session_id] = time.time() + ADMIN_SESSION_SECONDS
        secure = "; Secure" if os.environ.get("RENDER_EXTERNAL_HOSTNAME") else ""
        self.send_json(
            200,
            {"authenticated": True},
            cookie=(
                f"{ADMIN_COOKIE_NAME}={session_id}; HttpOnly; SameSite=Strict; "
                f"Path=/; Max-Age={ADMIN_SESSION_SECONDS}{secure}"
            ),
        )

    def handle_admin_logout(self):
        if not self.request_is_same_origin():
            self.send_json(403, {"error": "Request origin is not allowed."})
            return
        session_id = self.admin_session_id()
        if session_id:
            with ADMIN_SESSIONS_LOCK:
                ADMIN_SESSIONS.pop(session_id, None)
        secure = "; Secure" if os.environ.get("RENDER_EXTERNAL_HOSTNAME") else ""
        self.send_json(
            200,
            {"authenticated": False},
            cookie=f"{ADMIN_COOKIE_NAME}=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0{secure}",
        )

    def handle_admin_orders(self):
        if not self.require_admin():
            return
        with open_order_database() as connection:
            rows = connection.execute("SELECT * FROM orders ORDER BY created_at DESC, order_id DESC").fetchall()
        self.send_json(200, {"orders": [serialize_order(row) for row in rows]})

    def handle_create_order(self):
        if not self.request_is_same_origin():
            self.send_json(403, {"error": "Request origin is not allowed."})
            return
        payload = self.read_json_body()
        if payload is None:
            return
        requested_items = payload.get("items")
        if requested_items is None and "meal_id" in payload:
            requested_items = [{"meal_id": payload.get("meal_id"), "quantity": 1}]
        area = payload.get("area")
        customer_name = payload.get("customer_name", "").strip() if isinstance(payload.get("customer_name", ""), str) else None
        customer_phone = payload.get("customer_phone", "").strip() if isinstance(payload.get("customer_phone", ""), str) else None
        delivery_address = payload.get("delivery_address", "").strip() if isinstance(payload.get("delivery_address", ""), str) else None
        if not isinstance(requested_items, list) or not requested_items or len(requested_items) > len(MENU):
            self.send_json(400, {"error": "Add at least one available menu item to your cart."})
            return
        if not isinstance(area, str) or area not in LOCATIONS:
            self.send_json(400, {"error": "Choose a valid delivery area."})
            return
        if customer_name is None or len(customer_name) > 80:
            self.send_json(400, {"error": "Customer name must be at most 80 characters."})
            return
        if customer_phone is None or len(customer_phone) > 30:
            self.send_json(400, {"error": "Customer phone must be at most 30 characters."})
            return
        if not delivery_address or len(delivery_address) > 160:
            self.send_json(400, {"error": "Delivery address is required and must be at most 160 characters."})
            return
        meals_by_id = {item["id"]: item for item in MENU}
        items = []
        seen_ids = set()
        for requested_item in requested_items:
            if not isinstance(requested_item, dict):
                self.send_json(400, {"error": "Cart items must include a menu item and quantity."})
                return
            meal_id = requested_item.get("meal_id")
            quantity = requested_item.get("quantity")
            if type(meal_id) is not int or meal_id not in meals_by_id:
                self.send_json(400, {"error": "That menu item is not available."})
                return
            if type(quantity) is not int or quantity < 1 or quantity > 20:
                self.send_json(400, {"error": "Each cart quantity must be between 1 and 20."})
                return
            if meal_id in seen_ids:
                self.send_json(400, {"error": "Each menu item should appear only once in the cart."})
                return
            seen_ids.add(meal_id)
            meal = meals_by_id[meal_id]
            items.append({
                "id": meal_id,
                "name": meal["name"],
                "restaurant": meal["restaurant"],
                "quantity": quantity,
                "unit_price": meal["price"],
                "line_total": meal["price"] * quantity,
            })

        subtotal = sum(item["line_total"] for item in items)
        restaurant_distances = {}
        eta = 0
        for item in items:
            meal = meals_by_id[item["id"]]
            distance, meal_eta = estimate_delivery(meal, area)
            restaurant_distances[meal["restaurant"]] = distance
            eta = max(eta, meal_eta)
        delivery_fee = sum(25 + math.ceil(distance * 5) for distance in restaurant_distances.values())
        tax = round((subtotal + delivery_fee) * DEMO_TAX_RATE, 2)
        total = round(subtotal + delivery_fee + tax, 2)
        meal_summary = ", ".join(
            f"{item['name']} × {item['quantity']}" if item["quantity"] > 1 else item["name"]
            for item in items
        )
        restaurant_summary = ", ".join(restaurant_distances)
        order = {
            "meal": meal_summary,
            "restaurant": restaurant_summary,
            "area": area,
            "customer_name": customer_name or "Walk-in Customer",
            "customer_phone": customer_phone or "Not provided",
            "delivery_address": delivery_address,
            "subtotal": subtotal,
            "delivery_fee": delivery_fee,
            "tax": tax,
            "total": total,
            "eta_minutes": eta,
            "status": ORDER_STATUSES[0],
            "issued_at": datetime.now().strftime("%d %b %Y, %I:%M %p"),
            "delivery_deadline": time.time() + eta * 60,
            "items": items,
            "items_json": json.dumps(items, ensure_ascii=False),
        }
        with open_order_database() as connection:
            while True:
                order["order_id"] = random.randint(10000, 99999)
                try:
                    connection.execute(
                        """
                        INSERT INTO orders (
                            order_id, meal, restaurant, area, customer_name, customer_phone,
                            delivery_address, subtotal, delivery_fee, tax, total, eta_minutes,
                            status, issued_at, delivery_deadline, items_json
                        ) VALUES (
                            :order_id, :meal, :restaurant, :area, :customer_name, :customer_phone,
                            :delivery_address, :subtotal, :delivery_fee, :tax, :total, :eta_minutes,
                            :status, :issued_at, :delivery_deadline, :items_json
                        )
                        """,
                        order,
                    )
                    break
                except sqlite3.IntegrityError:
                    continue
        self.send_json(201, {"order": order})

    def handle_admin_order_status(self, request_path):
        if not self.request_is_same_origin():
            self.send_json(403, {"error": "Request origin is not allowed."})
            return
        if not self.require_admin():
            return
        match = re.fullmatch(r"/api/admin/orders/(\d+)/status", request_path)
        if not match:
            self.send_json(404, {"error": "Order not found."})
            return
        payload = self.read_json_body()
        if payload is None:
            return
        status = payload.get("status")
        if status not in ORDER_STATUSES:
            self.send_json(400, {"error": "Choose a valid order status."})
            return
        order_id = int(match.group(1))
        with open_order_database() as connection:
            cursor = connection.execute("UPDATE orders SET status = ? WHERE order_id = ?", (status, order_id))
            row = connection.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        if cursor.rowcount == 0:
            self.send_json(404, {"error": "Order not found."})
            return
        self.send_json(200, {"order": serialize_order(row)})

    def do_GET(self):
        request_path = urlsplit(self.path).path
        if request_path == "/healthz":
            self.send_json(200, {"status": "ok"})
            return
        if request_path == "/fooddash-logo.svg":
            logo_path = Path(__file__).with_name("fooddash-logo.svg")
            try:
                logo = logo_path.read_bytes()
            except OSError as error:
                self.send_error(500, f"Could not read fooddash-logo.svg: {error}")
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
            self.send_header("Content-Length", str(len(logo)))
            self.send_header("Cache-Control", "public, max-age=3600")
            self.end_headers()
            self.wfile.write(logo)
            return
        if request_path == "/api/admin/session":
            self.send_json(
                200,
                {
                    "authenticated": self.admin_session_id() is not None,
                    "configured": bool(os.environ.get("FOODDASH_ADMIN_PASSWORD")),
                },
            )
            return
        if request_path == "/api/admin/orders":
            self.handle_admin_orders()
            return
        if request_path not in {"/", "/assignment.html"}:
            self.send_error(404, "Not found")
            return
        page_path = Path(__file__).with_name("assignment.html")
        try:
            page = page_path.read_bytes()
        except OSError as error:
            self.send_error(500, f"Could not read assignment.html: {error}")
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page)

    def do_POST(self):
        request_path = urlsplit(self.path).path
        if request_path == "/api/admin/login":
            self.handle_admin_login()
            return
        if request_path == "/api/admin/logout":
            self.handle_admin_logout()
            return
        if request_path == "/api/orders":
            self.handle_create_order()
            return
        if request_path.startswith("/api/admin/orders/") and request_path.endswith("/status"):
            self.handle_admin_order_status(request_path)
            return
        if request_path != "/api/chat":
            self.send_error(404, "Not found")
            return
        payload = self.read_json_body()
        if payload is None:
            return
        message = payload.get("message")
        conversation_id = payload.get("conversation_id")
        if not isinstance(message, str) or len(message) > 240:
            self.send_json(400, {"error": "Message must be text with at most 240 characters."})
            return
        if not isinstance(conversation_id, str) or not conversation_id or len(conversation_id) > 80:
            self.send_json(400, {"error": "Conversation ID is missing or invalid."})
            return
        raw_history = payload.get("order_history", [])
        order_history = raw_history if isinstance(raw_history, list) else []
        order_history = [meal for meal in order_history if isinstance(meal, str)][-20:]
        raw_orders = payload.get("orders", [])
        orders = raw_orders if isinstance(raw_orders, list) else []
        orders = [
            order for order in orders
            if isinstance(order, dict)
            and isinstance(order.get("meal"), str)
            and isinstance(order.get("order_id"), (str, int))
            and isinstance(order.get("status"), str)
        ][-20:]
        self.send_json(200, chat_reply(message, conversation_id, order_history, orders))


def run_web_server(host="127.0.0.1", port=8000):
    initialize_order_database()
    if not os.environ.get("FOODDASH_ADMIN_PASSWORD"):
        print("Admin dashboard disabled: set FOODDASH_ADMIN_PASSWORD before starting to enable it.")
    with ThreadingHTTPServer((host, port), FoodDashRequestHandler) as server:
        print(f"FoodDash chatbot running at http://{host}:{port}/")
        print("Press Ctrl+C to stop the server.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nFoodDash chatbot stopped.")


def show_menu(customer_location):
    print("\nAVAILABLE MENU")
    for meal in MENU:
        distance, eta = estimate_delivery(meal, customer_location)
        print(
            f"{meal['id']}. {meal['name']} | {meal['restaurant']} | "
            f"₹{meal['price']} | {eta} min | {meal['rating']}/5 | "
            f"{distance:.1f} km away | {meal['category']}"
        )


def recommend_meals(data):
    print("\nTell the assistant what you want today.")
    location = choose_location()
    category = input("Food type (all / vegetarian / vegan / non-vegetarian): ").strip().lower()
    if category not in {"all", "vegetarian", "vegan", "non-vegetarian"}:
        print("I didn't recognize that type, so I'll include all foods.")
        category = "all"
    budget = read_number("Maximum meal budget in rupees: ₹", 1)
    max_eta = read_number("Maximum delivery time in minutes: ", 1)

    candidates = []
    for meal in MENU:
        if category != "all" and meal["category"] != category:
            continue
        if meal["price"] > budget:
            continue
        distance, eta = estimate_delivery(meal, location)
        if eta > max_eta:
            continue
        score = recommendation_score(meal, budget, eta, data["order_history"])
        candidates.append((score, meal, distance, eta))

    candidates.sort(key=lambda row: row[0], reverse=True)
    if not candidates:
        print("\nNo meals match all those choices. Try a higher budget or delivery time.")
        return

    print("\nTOP RECOMMENDATIONS")
    for number, (score, meal, distance, eta) in enumerate(candidates[:5], start=1):
        print(
            f"{number}. {meal['name']} from {meal['restaurant']} — "
            f"₹{meal['price']}, about {eta} min, rating {meal['rating']}/5"
        )

    choice = read_number("\nEnter a recommendation number to order, or 0 to go back: ", 0, min(5, len(candidates)))
    if choice == 0:
        return
    _, meal, distance, eta = candidates[choice - 1]
    place_order(data, meal, distance, eta, location)


def place_order(data, meal, distance, eta, customer_location):
    customer_name = input("Customer name for invoice: ").strip() or "Walk-in Customer"
    customer_phone = input("Customer phone (optional): ").strip() or "Not provided"
    delivery_address = input("Delivery address: ").strip() or customer_location

    subtotal = meal["price"]
    delivery_fee = 25 + math.ceil(distance * 5)
    tax = round((subtotal + delivery_fee) * DEMO_TAX_RATE, 2)
    total = round(subtotal + delivery_fee + tax, 2)
    print("\nORDER SUMMARY")
    print(f"Meal: {meal['name']} from {meal['restaurant']}")
    print(f"Delivery address: {delivery_address}")
    print(f"Meal price: ₹{subtotal:.2f}")
    print(f"Delivery fee: ₹{delivery_fee}")
    print(f"Demo tax ({DEMO_TAX_RATE:.0%}): ₹{tax:.2f}")
    print(f"Total: ₹{total:.2f}")
    print(f"Estimated delivery: {eta} minutes")
    order = {
        "order_id": random.randint(10000, 99999),
        "meal": meal["name"],
        "restaurant": meal["restaurant"],
        "area": customer_location,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "delivery_address": delivery_address,
        "subtotal": subtotal,
        "delivery_fee": delivery_fee,
        "tax": tax,
        "total": total,
        "eta_minutes": eta,
        "status": "Restaurant is preparing your food",
    }
    data["orders"].append(order)
    data["order_history"].append(meal["name"])
    save_data(data)
    safe = html.escape
    issued_at = datetime.now().strftime("%d %b %Y, %I:%M %p")
    invoice_html = f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Invoice #{order["order_id"]} - FoodDash Demo</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; padding: 36px 16px; background: #f1f5f3; color: #1c2b25; font: 15px Arial, sans-serif; }}
    .invoice {{ max-width: 780px; margin: auto; padding: 42px; background: white; border-radius: 14px; box-shadow: 0 8px 32px #163a2b18; }}
    .top {{ display: flex; justify-content: space-between; gap: 20px; border-bottom: 2px solid #1f7652; padding-bottom: 24px; }}
    h1 {{ margin: 0 0 7px; color: #17633f; font-size: 28px; }}
    .muted {{ color: #65746c; line-height: 1.55; }}
    .badge {{ display: inline-block; margin-top: 12px; padding: 6px 10px; border-radius: 20px; background: #e4f4eb; color: #17633f; font-size: 12px; font-weight: bold; letter-spacing: .06em; }}
    .number {{ text-align: right; line-height: 1.8; }}
    .parties {{ display: grid; grid-template-columns: 1fr 1fr; gap: 22px; margin: 28px 0; }}
    .card {{ padding: 16px; border: 1px solid #e0e8e3; border-radius: 9px; line-height: 1.6; }}
    .label {{ margin-bottom: 7px; color: #65746c; font-size: 11px; font-weight: bold; letter-spacing: .1em; text-transform: uppercase; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 14px; }}
    th {{ padding: 12px 8px; background: #f3f8f5; color: #52635a; text-align: left; font-size: 12px; text-transform: uppercase; }}
    td {{ padding: 15px 8px; border-bottom: 1px solid #e7ece8; }}
    .right {{ text-align: right; }}
    .totals {{ width: min(100%, 330px); margin: 18px 0 0 auto; }}
    .row {{ display: flex; justify-content: space-between; padding: 7px 0; }}
    .grand {{ margin-top: 6px; padding-top: 13px; border-top: 2px solid #1f7652; color: #17633f; font-size: 20px; font-weight: bold; }}
    .footer {{ margin-top: 30px; padding-top: 16px; border-top: 1px solid #e7ece8; color: #65746c; font-size: 12px; line-height: 1.6; }}
    .print {{ display: block; margin: 22px auto 0; padding: 11px 18px; border: 0; border-radius: 7px; background: #17633f; color: white; font-size: 14px; cursor: pointer; }}
    @media print {{ body {{ padding: 0; background: white; }} .invoice {{ max-width: none; padding: 18px; border-radius: 0; box-shadow: none; }} .print {{ display: none; }} }}
    @media (max-width: 600px) {{ .invoice {{ padding: 24px 18px; }} .top {{ flex-direction: column; }} .number {{ text-align: left; }} .parties {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <main class="invoice">
    <header class="top">
      <div><h1>FoodDash Demo</h1><div class="muted">Food delivery service<br>Assignment prototype</div><span class="badge">SAMPLE INVOICE</span></div>
      <div class="number"><strong>Invoice #{order["order_id"]}</strong><br><span class="muted">Issued {safe(issued_at)}<br>Order status: {safe(order["status"])}</span></div>
    </header>
    <section class="parties">
      <div class="card"><div class="label">Restaurant</div><strong>{safe(meal["restaurant"])}</strong><br><span class="muted">FoodDash Demo partner</span></div>
      <div class="card"><div class="label">Bill to / Deliver to</div><strong>{safe(customer_name)}</strong><br><span class="muted">{safe(customer_phone)}<br>{safe(delivery_address)}</span></div>
    </section>
    <div class="label">Order details</div>
    <table><thead><tr><th>Item</th><th>Qty</th><th class="right">Unit price</th><th class="right">Amount</th></tr></thead>
    <tbody><tr><td>{safe(meal["name"])}</td><td>1</td><td class="right">₹{subtotal:.2f}</td><td class="right">₹{subtotal:.2f}</td></tr></tbody></table>
    <section class="totals">
      <div class="row"><span>Subtotal</span><span>₹{subtotal:.2f}</span></div>
      <div class="row"><span>Delivery fee</span><span>₹{delivery_fee:.2f}</span></div>
      <div class="row"><span>Demo tax ({DEMO_TAX_RATE:.0%})</span><span>₹{tax:.2f}</span></div>
      <div class="row grand"><span>Total paid</span><span>₹{total:.2f}</span></div>
    </section>
    <footer class="footer">Estimated delivery: {eta} minutes.<br>This is a classroom demo invoice. Business details and the sample tax rate are placeholders.</footer>
    <button class="print" onclick="window.print()">Print / Save as PDF</button>
  </main>
</body>
</html>'''
    invoice_path = DATA_FILE.parent / f"invoice_{order['order_id']}.html"
    invoice_path.write_text(invoice_html, encoding="utf-8")
    print(f"\nOrder placed! Your order number is {order['order_id']}.")
    print(order["status"] + ".")
    print(f"\nInvoice saved to: {invoice_path.name}")
    print("Open the invoice file in a browser to view it or print/save as PDF.")
    print("Your past orders are saved and will help improve future recommendations.")


def track_order(data):
    if not data["orders"]:
        print("\nYou have no saved orders yet.")
        return
    print("\nYOUR ORDERS")
    for order in reversed(data["orders"][-5:]):
        print(
            f"#{order['order_id']} — {order['meal']} — {order['status']} — "
            f"estimated {order['eta_minutes']} min"
        )


def main():
    data = load_data()
    print("=" * 45)
    print("AI FOOD DELIVERY ASSISTANT")
    print("=" * 45)
    while True:
        print("\n1. Get AI meal recommendations and order")
        print("2. Browse the menu")
        print("3. Track saved orders")
        print("4. Exit")
        option = read_number("Choose an option: ", 1, 4)
        if option == 1:
            recommend_meals(data)
        elif option == 2:
            location = choose_location()
            show_menu(location)
        elif option == 3:
            track_order(data)
        else:
            print("Thanks for trying the food delivery demo!")
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FoodDash classroom demo")
    parser.add_argument(
        "--web",
        action="store_true",
        help="run the browser chatbot using the local Python backend",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("HOST", "127.0.0.1"),
        help="web server address (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", "8000")),
        help="web server port (default: PORT environment variable or 8000)",
    )
    args = parser.parse_args()
    if args.web:
        run_web_server(args.host, args.port)
    else:
        main()
