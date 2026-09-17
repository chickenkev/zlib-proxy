from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Credentials from environment variables
ZLIB_EMAIL = os.environ.get("ZLIB_EMAIL")
ZLIB_PASSWORD = os.environ.get("ZLIB_PASSWORD")

# List of domains to try (in order)
DOMAINS = [
    "https://zlib.bz",
    "https://z-lib.cx",
    "https://z-lib.mx",
    "https://z-lib.tv",
    "https://z-lib.gd",
    "https://z-lib.gl",
    "https://z-library.ec",
]

session = requests.Session()
working_domain = None
logged_in = False

def try_login(domain):
    """Try to log in on a specific domain"""
    try:
        r = session.post(
            f"{domain}/eapi/user/login",
            data={"email": ZLIB_EMAIL, "password": ZLIB_PASSWORD},
            timeout=12
        )
        if r.status_code == 200:
            data = r.json()
            if data.get("success") == 1:
                print(f"Logged in successfully on {domain}")
                return True
    except Exception as e:
        print(f"Login failed on {domain}: {e}")
    return False

def find_working_domain():
    """Try all domains until one works"""
    global working_domain, logged_in

    for domain in DOMAINS:
        print(f"Trying domain: {domain}")
        if try_login(domain):
            working_domain = domain
            logged_in = True
            return domain

    logged_in = False
    working_domain = None
    return None

@app.route("/")
def home():
    return "Z-Library proxy is running"

@app.route("/search")
def search():
    global working_domain, logged_in

    if not ZLIB_EMAIL or not ZLIB_PASSWORD:
        return jsonify({"error": "Missing ZLIB_EMAIL or ZLIB_PASSWORD"}), 500

    # If we don't have a working domain yet, find one
    if not logged_in or not working_domain:
        domain = find_working_domain()
        if not domain:
            return jsonify({"error": "Could not log in on any domain"}), 500
    else:
        domain = working_domain

    query = request.args.get("q") or request.args.get("title") or ""
    if not query:
        return jsonify({"results": []})

    try:
        r = session.post(
            f"{domain}/eapi/book/search",
            data={
                "message": query,
                "limit": 30,
                "page": 1,
                "order": "popular"
            },
            timeout=20
        )
        data = r.json()

        # If the session expired, try to re-login
        if data.get("success") == 0:
            print("Session may have expired, re-logging in...")
            domain = find_working_domain()
            if not domain:
                return jsonify({"error": "Re-login failed"}), 500

            r = session.post(
                f"{domain}/eapi/book/search",
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
                "url": book.get("href") or f"{domain}/book/{book.get('id')}",
                "id": str(book.get("id")),
                "cover": book.get("cover")
            })

        return jsonify({"results": results})

    except Exception as e:
        # If the current domain fails, clear it so we try others next time
        working_domain = None
        logged_in = False
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port)