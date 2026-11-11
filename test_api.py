"""تست خودکار API دارینو؛ با پایگاه داده موقت اجرا می‌شود:  py test_api.py"""
import json, os, tempfile, threading, unittest, urllib.request, urllib.error
from http.server import ThreadingHTTPServer

os.environ["DARINO_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
import db, server  # noqa: E402


def call(base, method, path, body=None, token=None):
    req = urllib.request.Request(base + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"})
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


class ApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init()
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = "http://127.0.0.1:%d" % cls.srv.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_full_flow(self):
        c = lambda *a, **k: call(self.base, *a, **k)
        s, d = c("GET", "/api/items")
        self.assertEqual((s, len(d["items"])), (200, 9))
        self.assertEqual(d["items"][0]["id"] > d["items"][-1]["id"], True)
        self.assertEqual(c("GET", "/api/items?cat=tool")[1]["items"].__len__(), 3)
        self.assertEqual(len(c("GET", "/api/items?q=" + urllib.request.quote("دوربین"))[1]["items"]), 2)
        p = [i["p"] for i in c("GET", "/api/items?sort=1")[1]["items"]]
        self.assertEqual(p, sorted(p))
        self.assertEqual(c("GET", "/api/favorites")[0], 401)
        s, d = c("POST", "/api/auth/register", {"name": "اب", "phone": "09120000000", "password": "123456"})
        self.assertEqual(s, 400)
        s, d = c("POST", "/api/auth/register", {"name": "علی رضایی", "phone": "۰۹۱۲۰۰۰۰۰۰۰", "password": "123456"})
        self.assertEqual(s, 201)
        tok = d["token"]
        self.assertEqual(c("POST", "/api/auth/register", {"name": "علی رضایی", "phone": "09120000000", "password": "123456"})[0], 409)
        self.assertEqual(c("POST", "/api/auth/login", {"phone": "09120000000", "password": "bad-pass"})[0], 401)
        s, d = c("POST", "/api/auth/login", {"phone": "09120000000", "password": "123456"})
        self.assertEqual(s, 200)
        self.assertEqual(c("GET", "/api/auth/me", token=tok)[1]["user"]["name"], "علی رضایی")
        # علاقه‌مندی
        self.assertTrue(c("POST", "/api/favorites/1", token=tok)[1]["on"])
        self.assertEqual(c("GET", "/api/favorites", token=tok)[1]["ids"], [1])
        self.assertEqual(len(c("GET", "/api/items?fav=1", token=tok)[1]["items"]), 1)
        self.assertFalse(c("POST", "/api/favorites/1", token=tok)[1]["on"])
        # کالای جدید
        s, d = c("POST", "/api/items", {"name": "پروژکتور", "category": "dig", "price": 300000, "city": "تهران", "description": "<b>x</b>"}, tok)
        self.assertEqual(s, 201)
        self.assertEqual(c("GET", "/api/auth/me", token=tok)[1]["user"]["items"], 1)
        self.assertEqual(c("POST", "/api/items", {"name": "پروژکتور", "category": "zzz", "price": 300000, "city": "تهران"}, tok)[0], 400)
        # پیام
        self.assertEqual(c("POST", "/api/items/1/messages", {"text": "سلام، آزاد است؟"}, tok)[0], 201)
        # درخواست اجاره
        body = {"item_id": 1, "start_date": "2099-01-01", "days": 3, "contact_name": "علی رضایی", "contact_phone": "09120000000"}
        self.assertEqual(c("POST", "/api/requests", dict(body, days=99), tok)[0], 400)
        s, d = c("POST", "/api/requests", body, tok)
        self.assertEqual((s, d["total"]), (201, c("GET", "/api/items/1")[1]["item"]["p"] * 3))
        rid = d["id"]
        self.assertEqual(len(c("GET", "/api/requests?status=draft", token=tok)[1]["requests"]), 1)
        self.assertEqual(c("POST", "/api/promo", {"code": "x"})[0], 404)
        self.assertEqual(c("POST", "/api/promo", {"code": "darino10"})[1]["percent"], 10)
        s, d = c("POST", "/api/requests/submit", {"promo": "DARINO10"}, tok)
        self.assertEqual((d["total"], d["discount"], d["final"]), (750000, 75000, 675000))
        self.assertEqual(c("POST", "/api/requests/submit", {}, tok)[0], 400)
        self.assertEqual(c("DELETE", "/api/requests/%d" % rid, token=tok)[0], 404)
        # خروج
        c("POST", "/api/auth/logout", token=tok)
        self.assertEqual(c("GET", "/api/auth/me", token=tok)[0], 401)

    def test_static(self):
        for path, ct in (("/", "text/html"), ("/css/style.css", "text/css"), ("/js/app.js", "javascript")):
            with urllib.request.urlopen(self.base + path) as r:
                self.assertIn(ct, r.headers["Content-Type"])
        with self.assertRaises(urllib.error.HTTPError):
            urllib.request.urlopen(self.base + "/..%2fserver.py")


if __name__ == "__main__":
    unittest.main(verbosity=2)
