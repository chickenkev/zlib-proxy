from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Credentials come from environment variables (set these on Render)
ZLIB_EMAIL = os.environ.get("ZLIB_EMAIL")
ZLIB_PASSWORD = os.environ.get("ZLIB_PASSWORD")
BASE_URL = os.environ.get("ZLIB_BASE_URL", "https://z-lib.gd")

session = requests.Session()
logged_in = False

def login():
    global logged_in
    if not ZLIB_EMAIL or not ZLIB_PASSWORD:
        print("Missing ZLIB_EMAIL or ZLIB_PASSWORD environment variables")
        return False

    try:
        r = session.post(
            f"{BASE_URL}/eapi/user/login",
            data={"email": ZLIB_EMAIL, "password": ZLIB_PASSWORD},
            timeout=15
        )
        if r.status_code == 200 and r.json().get("success") == 1:
            logged_in = True
            print("Logged in successfully")
            return True
    except Exception as e:
        print("Login failed:", e)

    logged_in = False
    return False

@app.route("/")
def home():
    return "Z-Library proxy is running"

@app.route("/search")
def search():
    if not logged_in:
        if not login():
            return jsonify({"error": "Login failed. Check credentials."}), 401

    query = request.args.get("q") or request.args.get("title") or ""
    if not query:
        return jsonify({"results": []})

    try:
        r = session.post(
            f"{BASE_URL}/eapi/book/search",
            data={
                "message": query,
                "limit": 30,
                "page": 1,
                "order": "popular"
            },
            timeout=20
        )
        data = r.json()
        books = data.get("books", [])

        results = []
        for book in books:
            results.append({
                "title": book.get("title"),
                "author": book.get("author") or book.get("authors"),
                "year": book.get("year"),
                "extension": book.get("extension"),
                "size": book.get("filesize") or book.get("size"),
                "language": book.get("language"),
                "url": book.get("href") or f"{BASE_URL}/book/{book.get('id')}",
                "id": str(book.get("id")),
                "cover": book.get("cover")
            })

        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port)