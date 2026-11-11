#!/usr/bin/env python3
"""بک‌اند دارینو: سرو فایل‌های سایت (پوشه public) + API به‌صورت JSON.
فقط از کتابخانه استاندارد پایتون استفاده می‌کند؛ نصب بسته اضافه لازم نیست."""
import datetime, hashlib, hmac, json, os, re, secrets, sqlite3, sys, traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

import db

ROOT = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(ROOT, "public")
PROMOS = {"DARINO10": 10}  # کد تخفیف -> درصد
DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
PHONE_RE = re.compile(r"^09\d{9}$")
EMOJI = {"dig": "📷", "trip": "⛺", "tool": "🔧"}
MIME = {".html": "text/html", ".css": "text/css", ".js": "application/javascript",
        ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg",
        ".ico": "image/x-icon", ".json": "application/json", ".txt": "text/plain"}


class ApiError(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code, self.msg = code, msg


def need(cond, msg, code=400):
    if not cond:
        raise ApiError(code, msg)


def hash_pw(pw, salt):
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 150000).hex()


def clean_phone(v):
    return str(v or "").strip().translate(DIGITS)


def text(v, lo, hi, msg):
    v = str(v or "").strip()
    need(lo <= len(v) <= hi, msg)
    return v


def to_int(v, msg):
    try:
        return int(v)
    except (TypeError, ValueError):
        raise ApiError(400, msg)


def item_json(r):
    return {"id": r["id"], "c": r["category"], "e": r["emoji"], "n": r["name"], "p": r["price"],
            "city": r["city"], "o": r["owner_name"], "r": r["rating"] or 0,
            "d": r["description"] or "", "s": json.loads(r["specs"] or "[]")}


def user_json(con, u):
    n = con.execute("SELECT COUNT(*) FROM items WHERE owner_id=?", (u["id"],)).fetchone()[0]
    return {"id": u["id"], "name": u["name"], "phone": u["phone"], "items": n}


def auth(h, con):
    a = h.headers.get("Authorization", "")
    need(a.startswith("Bearer "), "ابتدا وارد حساب شو.", 401)
    row = con.execute("SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=?",
                      (a[7:].strip(),)).fetchone()
    need(row, "نشست منقضی شده؛ دوباره وارد شو.", 401)
    return row


def new_session(con, uid):
    tok = secrets.token_urlsafe(32)
    con.execute("INSERT INTO sessions(token,user_id) VALUES (?,?)", (tok, uid))
    return tok


def get_item(con, iid):
    r = con.execute("SELECT * FROM items WHERE id=?", (iid,)).fetchone()
    need(r, "کالا پیدا نشد.", 404)
    return r


ROUTES = []


def route(method, pattern):
    def deco(f):
        ROUTES.append((method, re.compile("^" + pattern + "$"), f))
        return f
    return deco


# ---------- حساب کاربری ----------
@route("POST", "/auth/register")
def register(h, con, m, q):
    b = h.read_json()
    name = text(b.get("name"), 3, 60, "نام و نام خانوادگی را کامل وارد کن.")
    phone = clean_phone(b.get("phone"))
    need(PHONE_RE.match(phone), "شماره تماس باید ۱۱ رقم و با ۰۹ شروع شود.")
    pw = str(b.get("password") or "")
    need(6 <= len(pw) <= 100, "رمز عبور حداقل ۶ نویسه باشد.")
    salt = secrets.token_hex(16)
    try:
        cur = con.execute("INSERT INTO users(name,phone,pw_hash,salt) VALUES (?,?,?,?)",
                          (name, phone, hash_pw(pw, salt), salt))
    except sqlite3.IntegrityError:
        raise ApiError(409, "این شماره قبلاً ثبت‌نام کرده است؛ وارد شو.")
    u = con.execute("SELECT * FROM users WHERE id=?", (cur.lastrowid,)).fetchone()
    return 201, {"token": new_session(con, u["id"]), "user": user_json(con, u)}


@route("POST", "/auth/login")
def login(h, con, m, q):
    b = h.read_json()
    phone, pw = clean_phone(b.get("phone")), str(b.get("password") or "")
    u = con.execute("SELECT * FROM users WHERE phone=?", (phone,)).fetchone()
    ok = u and hmac.compare_digest(u["pw_hash"], hash_pw(pw, u["salt"]))
    need(ok, "شماره تماس یا رمز عبور نادرست است.", 401)
    return {"token": new_session(con, u["id"]), "user": user_json(con, u)}


@route("GET", "/auth/me")
def me(h, con, m, q):
    return {"user": user_json(con, auth(h, con))}


@route("POST", "/auth/logout")
def logout(h, con, m, q):
    a = h.headers.get("Authorization", "")
    con.execute("DELETE FROM sessions WHERE token=?", (a[7:].strip(),))
    return {"ok": True}


# ---------- کالاها ----------
@route("GET", "/items")
def items_list(h, con, m, q):
    cat = q.get("cat", [""])[0]
    s = q.get("q", [""])[0].strip()
    sort = q.get("sort", ["0"])[0]
    sql, args, where = "SELECT i.* FROM items i", [], []
    if q.get("fav", [""])[0] == "1":
        sql += " JOIN favorites f ON f.item_id=i.id AND f.user_id=?"
        args.append(auth(h, con)["id"])
    if cat and cat != "all":
        where.append("i.category=?")
        args.append(cat)
    if s:
        where.append("(i.name LIKE ? OR i.description LIKE ? OR i.city LIKE ?)")
        args += ["%" + s + "%"] * 3
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += {"1": " ORDER BY i.price ASC", "2": " ORDER BY i.price DESC",
            "3": " ORDER BY i.rating DESC"}.get(sort, " ORDER BY i.id DESC")
    return {"items": [item_json(r) for r in con.execute(sql, args)]}


@route("GET", r"/items/(\d+)")
def item_one(h, con, m, q):
    return {"item": item_json(get_item(con, int(m.group(1))))}


@route("POST", "/items")
def item_create(h, con, m, q):
    u = auth(h, con)
    b = h.read_json()
    name = text(b.get("name"), 3, 80, "نام کالا را وارد کن (حداقل ۳ نویسه).")
    cat = str(b.get("category") or "")
    need(con.execute("SELECT 1 FROM categories WHERE key=?", (cat,)).fetchone(), "دسته‌بندی نامعتبر است.")
    price = to_int(b.get("price"), "قیمت نامعتبر است.")
    need(10000 <= price <= 100000000, "قیمت روزانه باید بین ۱۰٬۰۰۰ تا ۱۰۰٬۰۰۰٬۰۰۰ تومان باشد.")
    city = text(b.get("city"), 2, 40, "شهر را وارد کن.")
    desc = str(b.get("description") or "").strip()[:500] or "توضیحاتی ثبت نشده است."
    specs = ["ثبت‌شده توسط " + u["name"], "ودیعه: طبق توافق", "حداقل اجاره: ۱ روز"]
    cur = con.execute(
        "INSERT INTO items(category,emoji,name,price,city,owner_id,owner_name,rating,description,specs)"
        " VALUES (?,?,?,?,?,?,?,0,?,?)",
        (cat, EMOJI.get(cat, "📦"), name, price, city, u["id"], u["name"], desc,
         json.dumps(specs, ensure_ascii=False)))
    return 201, {"item": item_json(get_item(con, cur.lastrowid))}


@route("POST", r"/items/(\d+)/messages")
def message_send(h, con, m, q):
    u = auth(h, con)
    it = get_item(con, int(m.group(1)))
    body = text(h.read_json().get("text"), 3, 500, "متن پیام را بنویس (حداقل ۳ نویسه).")
    con.execute("INSERT INTO messages(item_id,sender_id,body) VALUES (?,?,?)", (it["id"], u["id"], body))
    return 201, {"ok": True, "to": it["owner_name"]}


# ---------- علاقه‌مندی‌ها ----------
@route("GET", "/favorites")
def fav_list(h, con, m, q):
    u = auth(h, con)
    return {"ids": [r[0] for r in con.execute("SELECT item_id FROM favorites WHERE user_id=?", (u["id"],))]}


@route("POST", r"/favorites/(\d+)")
def fav_toggle(h, con, m, q):
    u, iid = auth(h, con), get_item(con, int(m.group(1)))["id"]
    cur = con.execute("DELETE FROM favorites WHERE user_id=? AND item_id=?", (u["id"], iid))
    if cur.rowcount:
        return {"on": False}
    con.execute("INSERT INTO favorites VALUES (?,?)", (u["id"], iid))
    return {"on": True}


# ---------- درخواست‌های اجاره و تخفیف ----------
@route("POST", "/promo")
def promo_check(h, con, m, q):
    code = str(h.read_json().get("code") or "").strip().upper()
    need(code in PROMOS, "کد تخفیف معتبر نیست.", 404)
    return {"code": code, "percent": PROMOS[code]}


@route("GET", "/requests")
def req_list(h, con, m, q):
    u = auth(h, con)
    sql = ("SELECT r.id,r.item_id,r.start_date d,r.days k,r.total t,r.status,i.emoji e,i.name n "
           "FROM rental_requests r JOIN items i ON i.id=r.item_id WHERE r.user_id=?")
    args = [u["id"]]
    st = q.get("status", [""])[0]
    if st:
        sql += " AND r.status=?"
        args.append(st)
    return {"requests": [dict(r) for r in con.execute(sql + " ORDER BY r.id", args)]}


@route("POST", "/requests")
def req_create(h, con, m, q):
    u = auth(h, con)
    b = h.read_json()
    it = get_item(con, to_int(b.get("item_id"), "کالا نامعتبر است."))
    try:
        start = datetime.date.fromisoformat(str(b.get("start_date")))
    except ValueError:
        raise ApiError(400, "تاریخ شروع اجاره را انتخاب کن.")
    need(start >= datetime.date.today() - datetime.timedelta(days=1), "تاریخ شروع نمی‌تواند گذشته باشد.")
    days = to_int(b.get("days"), "تعداد روز نامعتبر است.")
    need(1 <= days <= 30, "تعداد روز باید بین ۱ تا ۳۰ باشد.")
    name = text(b.get("contact_name"), 3, 60, "نام و نام خانوادگی را کامل وارد کن.")
    phone = clean_phone(b.get("contact_phone"))
    need(PHONE_RE.match(phone), "شماره تماس باید ۱۱ رقم و با ۰۹ شروع شود.")
    cur = con.execute(
        "INSERT INTO rental_requests(user_id,item_id,start_date,days,total,contact_name,contact_phone)"
        " VALUES (?,?,?,?,?,?,?)", (u["id"], it["id"], start.isoformat(), days, it["price"] * days, name, phone))
    return 201, {"id": cur.lastrowid, "total": it["price"] * days}


@route("DELETE", r"/requests/(\d+)")
def req_delete(h, con, m, q):
    u = auth(h, con)
    cur = con.execute("DELETE FROM rental_requests WHERE id=? AND user_id=? AND status='draft'",
                      (int(m.group(1)), u["id"]))
    need(cur.rowcount, "درخواست پیدا نشد.", 404)
    return {"ok": True}


@route("POST", "/requests/submit")
def req_submit(h, con, m, q):
    u = auth(h, con)
    code = str(h.read_json().get("promo") or "").strip().upper()
    need(not code or code in PROMOS, "کد تخفیف معتبر نیست.")
    pct = PROMOS.get(code, 0)
    rows = con.execute("SELECT id,total FROM rental_requests WHERE user_id=? AND status='draft'",
                       (u["id"],)).fetchall()
    need(rows, "درخواستی برای ثبت وجود ندارد.")
    total = discount = 0
    for r in rows:
        d = round(r["total"] * pct / 100)
        con.execute("UPDATE rental_requests SET status='submitted',promo_code=?,discount=? WHERE id=?",
                    (code or None, d, r["id"]))
        total, discount = total + r["total"], discount + d
    return {"count": len(rows), "total": total, "discount": discount, "final": total - discount}


# ---------- سرور HTTP ----------
class Handler(BaseHTTPRequestHandler):
    server_version = "Darino/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

    def read_json(self):
        n = int(self.headers.get("Content-Length") or 0)
        need(n <= 100000, "حجم درخواست زیاد است.", 413)
        if not n:
            return {}
        try:
            d = json.loads(self.rfile.read(n).decode("utf-8"))
        except ValueError:
            raise ApiError(400, "قالب درخواست نامعتبر است.")
        need(isinstance(d, dict), "قالب درخواست نامعتبر است.")
        return d

    def send_json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def serve_static(self, path):
        rel = unquote(path).lstrip("/") or "index.html"
        full = os.path.normpath(os.path.join(PUBLIC, rel))
        if os.path.isdir(full):
            full = os.path.join(full, "index.html")
        if not full.startswith(PUBLIC + os.sep) or not os.path.isfile(full):
            raise ApiError(404, "صفحه پیدا نشد.")
        ctype = MIME.get(os.path.splitext(full)[1].lower(), "application/octet-stream")
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
            ctype += "; charset=utf-8"
        with open(full, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def api(self, method, path, q):
        con = db.connect()
        try:
            for mth, rx, f in ROUTES:
                mt = rx.match(path)
                if mt and mth == method:
                    res = f(self, con, mt, q)
                    con.commit()
                    code, obj = res if isinstance(res, tuple) else (200, res)
                    return self.send_json(code, obj)
            raise ApiError(404, "مسیر API پیدا نشد.")
        finally:
            con.close()

    def handle_any(self, method):
        u = urlparse(self.path)
        try:
            if u.path.startswith("/api/"):
                self.api(method, u.path[4:], parse_qs(u.query))
            elif method == "GET":
                self.serve_static(u.path)
            else:
                raise ApiError(405, "روش درخواست مجاز نیست.")
        except ApiError as e:
            self.send_json(e.code, {"error": e.msg})
        except Exception:
            traceback.print_exc()
            self.send_json(500, {"error": "خطای داخلی سرور."})

    def do_GET(self): self.handle_any("GET")
    def do_POST(self): self.handle_any("POST")
    def do_DELETE(self): self.handle_any("DELETE")


def main():
    port = int(os.environ.get("PORT", "8000"))
    db.init()
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print("دارینو اجرا شد: http://localhost:%d   (توقف: Ctrl+C)" % port)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nسرور متوقف شد.")


if __name__ == "__main__":
    main()
