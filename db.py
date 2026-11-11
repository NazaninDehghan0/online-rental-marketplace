"""لایه پایگاه داده دارینو (SQLite): ساخت جدول‌ها و داده‌های اولیه."""
import json, os, sqlite3

ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DARINO_DB", os.path.join(ROOT, "darino.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  phone TEXT NOT NULL UNIQUE,
  pw_hash TEXT NOT NULL,
  salt TEXT NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS sessions(
  token TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS categories(
  key TEXT PRIMARY KEY, name TEXT NOT NULL, emoji TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS items(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  category TEXT NOT NULL REFERENCES categories(key),
  emoji TEXT,
  name TEXT NOT NULL,
  price INTEGER NOT NULL CHECK(price > 0),
  city TEXT NOT NULL,
  owner_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  owner_name TEXT NOT NULL,
  rating REAL DEFAULT 0,
  description TEXT,
  specs TEXT DEFAULT '[]',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS favorites(
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
  PRIMARY KEY(user_id, item_id));
CREATE TABLE IF NOT EXISTS rental_requests(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
  start_date TEXT NOT NULL,
  days INTEGER NOT NULL CHECK(days BETWEEN 1 AND 30),
  total INTEGER NOT NULL,
  contact_name TEXT, contact_phone TEXT,
  status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','submitted')),
  promo_code TEXT, discount INTEGER DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS messages(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
  sender_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  body TEXT NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP);
"""


def connect():
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init():
    con = connect()
    con.executescript(SCHEMA)
    if not con.execute("SELECT 1 FROM categories LIMIT 1").fetchone():
        with open(os.path.join(ROOT, "seed.json"), encoding="utf-8") as f:
            seed = json.load(f)
        for c in seed["categories"]:
            con.execute("INSERT INTO categories VALUES (?,?,?)", (c["key"], c["name"], c["emoji"]))
        # به ترتیب معکوس درج می‌شود تا با «id نزولی» ترتیب اصلی نمایش حفظ شود
        for i in reversed(seed["items"]):
            con.execute(
                "INSERT INTO items(category,emoji,name,price,city,owner_name,rating,description,specs)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (i["c"], i["e"], i["n"], i["p"], i["city"], i["o"], i["r"], i["d"],
                 json.dumps(i["s"], ensure_ascii=False)))
    con.commit()
    con.close()
