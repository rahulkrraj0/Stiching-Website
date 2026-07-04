"""
SilaiGhar — multi-page Flask storefront for a Gurugram tailoring business.

Setup:
  1. Copy .env.example to .env and fill in real values (SECRET_KEY, admin
     login, etc.) — see SETUP.md for the full launch checklist.
  2. pip install -r requirements.txt
  3. python app.py   (dev)   |   gunicorn app:app   (production)

No prices are shown on the public site by design (see data/products.json
notes) — pricing is confirmed during the home visit.
"""

import functools
import json
import logging
import os
import re
import secrets
import uuid

from flask import (
    Flask, Response, abort, flash, jsonify, redirect,
    render_template, request, session, url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional in production if env vars are set another way

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# --------------------------------------------------------------------------
# App & config
# --------------------------------------------------------------------------

app = Flask(__name__)

IS_PRODUCTION = os.environ.get("FLASK_ENV", "development").lower() == "production"
DEBUG = os.environ.get("FLASK_DEBUG", "0" if IS_PRODUCTION else "1") == "1"

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or (
    None if IS_PRODUCTION else secrets.token_hex(32)
)
if not app.config["SECRET_KEY"]:
    raise RuntimeError(
        "SECRET_KEY is not set. Set it as an environment variable before "
        "running in production — see SETUP.md."
    )

app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB upload cap
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = IS_PRODUCTION

logging.basicConfig(level=logging.INFO if not DEBUG else logging.DEBUG)
logger = logging.getLogger("silaighar")


def _normalize_password_hash(raw_hash: str) -> str:
    """Normalize legacy Werkzeug password hashes to the current format."""
    if not raw_hash or raw_hash.count("$") != 2:
        return raw_hash

    method, salt, hashval = raw_hash.split("$", 2)
    if method.startswith(("scrypt:", "pbkdf2:")):
        return raw_hash

    if re.fullmatch(r"\d+:\d+:\d+", method):
        return f"scrypt:{method}${salt}${hashval}"

    if re.fullmatch(r"[a-z0-9_+-]+:\d+", method, re.IGNORECASE):
        return f"pbkdf2:{method}${salt}${hashval}"

    return raw_hash


ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = _normalize_password_hash(os.environ.get("ADMIN_PASSWORD_HASH", ""))
if not ADMIN_PASSWORD_HASH:
    # Dev-only fallback so the app still runs out of the box.
    # CHANGE THIS before deploying — see SETUP.md.
    ADMIN_PASSWORD_HASH = generate_password_hash("change-this-password", method="pbkdf2:sha256")
    if IS_PRODUCTION:
        raise RuntimeError(
            "ADMIN_PASSWORD_HASH is not set. Generate one with "
            "werkzeug.security.generate_password_hash and set it as an "
            "environment variable — see SETUP.md."
        )

BASE_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(BASE_DIR, "data", "products.json")
OFFERS_PATH = os.path.join(BASE_DIR, "data", "offers.json")
CATEGORIES_PATH = os.path.join(BASE_DIR, "data", "categories.json")
HERO_PATH = os.path.join(BASE_DIR, "data", "hero.json")
BUSINESS_PATH = os.path.join(BASE_DIR, "data", "business.json")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "img")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

SITE_URL = os.environ.get("SITE_URL", "https://www.silaighar.in")


# --------------------------------------------------------------------------
# Data helpers (all reads/writes are defensive — a corrupt/missing JSON
# file should degrade gracefully instead of crashing every page)
# --------------------------------------------------------------------------

def _read_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to read %s: %s", path, e)
        return default


def _write_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except OSError as e:
        logger.error("Failed to write %s: %s", path, e)
        return False


def load_products():
    return _read_json(DATA_PATH, [])


def save_products(products):
    return _write_json(DATA_PATH, products)


DEFAULT_CATEGORIES = {
    "blouse": "Blouses",
    "kurta": "Kurtas & Kurtis",
    "saree-fall": "Saree Fall & Pico",
    "suit": "Suits & Blazers",
    "bridal": "Bridal & Occasion Wear",
    "indo-western": "Indo-Western",
}


def load_categories():
    return _read_json(CATEGORIES_PATH, DEFAULT_CATEGORIES.copy())


def save_categories(categories):
    return _write_json(CATEGORIES_PATH, categories)


def load_offers():
    return _read_json(OFFERS_PATH, [])


def save_offers(offers):
    return _write_json(OFFERS_PATH, offers)


def load_hero():
    return _read_json(HERO_PATH, {})


def save_hero(hero):
    return _write_json(HERO_PATH, hero)


def load_business():
    return _read_json(BUSINESS_PATH, {"name": "SilaiGhar", "city": "Gurugram"})


def build_categories(products, categories):
    """Group products by category and pick a cover product for each."""
    cats = []
    for slug, label in categories.items():
        items = [p for p in products if p.get("category") == slug]
        if items:
            cats.append({
                "slug": slug,
                "label": label,
                "count": len(items),
                "cover": items[0],
            })
    return cats


def slugify(text):
    value = text.strip().lower()
    value = re.sub(r"[^a-z0-9\s-]", "", value)
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value


def allowed_file(filename):
    return bool(filename) and "." in filename and \
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload(file_storage, prefix=""):
    """Validate and save an uploaded image. Returns the saved filename or None.

    Validates both the extension AND (when Pillow is available) that the
    file content is actually a decodable image, so a renamed .php file
    can't slip through as a .jpg.
    """
    if not file_storage or not file_storage.filename:
        return None
    if not allowed_file(file_storage.filename):
        return None
    if HAS_PIL:
        try:
            file_storage.stream.seek(0)
            Image.open(file_storage.stream).verify()
            file_storage.stream.seek(0)
        except Exception:
            logger.warning("Rejected upload that failed image validation: %s",
                            file_storage.filename)
            return None
    filename = f"{prefix}{uuid.uuid4().hex}_{secure_filename(file_storage.filename)}"
    file_storage.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
    return filename


# --------------------------------------------------------------------------
# Auth (session-based admin login) + CSRF
# --------------------------------------------------------------------------

def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def get_csrf_token():
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(32)
    return session["_csrf_token"]


app.jinja_env.globals["csrf_token"] = get_csrf_token


@app.before_request
def enforce_csrf_on_admin_posts():
    if request.method == "POST" and request.path.startswith("/admin") \
            and request.endpoint != "admin_login":
        token = request.form.get("csrf_token", "")
        if not token or not secrets.compare_digest(token, session.get("_csrf_token", "")):
            abort(400, description="Invalid or missing CSRF token. Please refresh and try again.")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        valid_user = secrets.compare_digest(username, ADMIN_USERNAME)
        valid_pass = check_password_hash(ADMIN_PASSWORD_HASH, password)
        if valid_user and valid_pass:
            session.clear()
            session["is_admin"] = True
            session.permanent = True
            dest = request.args.get("next")
            if dest and dest.startswith("/admin"):
                return redirect(dest)
            return redirect(url_for("admin_dashboard"))
        error = "Incorrect username or password."
    return render_template("admin_login.html", error=error)


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


# --------------------------------------------------------------------------
# Global template context + security headers
# --------------------------------------------------------------------------

@app.context_processor
def inject_globals():
    return {
        "site_name": "SilaiGhar",
        "nav_categories": load_categories(),
        "ticker_messages": load_offers(),
        "business": load_business(),
        "site_url": SITE_URL,
    }


@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response


# --------------------------------------------------------------------------
# Admin routes (all protected by login_required)
# --------------------------------------------------------------------------

@app.route("/admin")
@login_required
def admin_dashboard():
    products = load_products()
    offers = load_offers()
    category_map = load_categories()
    categories = build_categories(products, category_map)
    tag_suggestions = sorted({tag for p in products for tag in p.get("tags", [])})
    hero = load_hero()
    business = load_business()
    return render_template(
        "admin.html",
        products=products,
        offers=offers,
        categories=categories,
        hero=hero,
        tag_suggestions=tag_suggestions,
        existing_categories=category_map,
        biz=business,
    )


@app.route("/admin/product/add", methods=["POST"])
@login_required
def admin_add_product():
    products = load_products()
    form = request.form
    file = request.files.get("image")
    try:
        next_id = max([p.get("id", 0) for p in products]) + 1 if products else 1
        product = {
            "id": int(form.get("id") or next_id),
            "name": (form.get("name") or "Untitled").strip(),
            "category": form.get("category") or "",
            "fabric": (form.get("fabric") or "").strip(),
            "hash_number": form.get("hash_number", "").strip(),
            "color": form.get("color") or "#6C3CE9",
            "icon": form.get("category") or "kurta",
            "desc": (form.get("desc") or "").strip(),
            "tags": [t.strip() for t in (form.get("tags") or "").split(",") if t.strip()],
        }
        if product["hash_number"]:
            duplicate = next(
                (p for p in products if p.get("category") == product["category"]
                 and p.get("hash_number") == product["hash_number"]), None)
            if duplicate:
                flash(f"Hash number '{product['hash_number']}' is already used in this category.", "error")
                return redirect(url_for("admin_dashboard") + "#admin-products")
        saved_filename = save_upload(file)
        if saved_filename:
            product["image"] = saved_filename
        elif file and file.filename:
            flash("Image was not saved — please upload a valid PNG/JPG/WEBP under 8MB.", "error")
        price = form.get("price")
        if price:
            try:
                product["price"] = float(price)
            except ValueError:
                pass
        discount = form.get("discount")
        if discount:
            try:
                product["discount"] = float(discount)
            except ValueError:
                pass
        products.append(product)
        save_products(products)
        flash("Product added.", "success")
        return redirect(url_for("admin_dashboard") + "#admin-products")
    except Exception:
        logger.exception("Failed to add product")
        flash("Something went wrong adding that product.", "error")
        return redirect(url_for("admin_dashboard") + "#admin-products")


@app.route("/admin/product/edit/<int:product_id>")
@login_required
def admin_edit_product(product_id):
    products = load_products()
    offers = load_offers()
    category_map = load_categories()
    categories = build_categories(products, category_map)
    product = next((p for p in products if p.get("id") == product_id), None)
    if not product:
        return redirect(url_for("admin_dashboard"))
    tag_suggestions = sorted({tag for p in products for tag in p.get("tags", [])})
    return render_template(
        "admin.html",
        products=products,
        offers=offers,
        categories=categories,
        edit_product=product,
        tag_suggestions=tag_suggestions,
        existing_categories=category_map,
        hero=load_hero(),
        biz=load_business(),
    )


@app.route("/admin/product/update", methods=["POST"])
@login_required
def admin_update_product():
    products = load_products()
    form = request.form
    file = request.files.get("image")
    try:
        pid = int(form.get("id"))
    except (TypeError, ValueError):
        return redirect(url_for("admin_dashboard"))
    prod = next((p for p in products if p.get("id") == pid), None)
    if not prod:
        return redirect(url_for("admin_dashboard"))
    prod["name"] = (form.get("name") or prod.get("name") or "").strip()
    prod["category"] = form.get("category") or prod.get("category")
    prod["fabric"] = (form.get("fabric") or prod.get("fabric") or "").strip()
    prod["color"] = form.get("color") or prod.get("color") or "#6C3CE9"
    prod["hash_number"] = form.get("hash_number", "").strip() or prod.get("hash_number", "")
    prod["desc"] = (form.get("desc") or prod.get("desc") or "").strip()
    prod["tags"] = [t.strip() for t in (form.get("tags") or "").split(",") if t.strip()]
    if prod["hash_number"]:
        duplicate = next(
            (p for p in products if p.get("id") != prod["id"]
             and p.get("category") == prod["category"]
             and p.get("hash_number") == prod["hash_number"]), None)
        if duplicate:
            flash(f"Hash number '{prod['hash_number']}' is already used in this category.", "error")
            return redirect(url_for("admin_dashboard") + "#admin-products")
    saved_filename = save_upload(file)
    if saved_filename:
        prod["image"] = saved_filename
    elif file and file.filename:
        flash("Image was not saved — please upload a valid PNG/JPG/WEBP under 8MB.", "error")
    price = form.get("price")
    if price:
        try:
            prod["price"] = float(price)
        except ValueError:
            pass
    else:
        prod.pop("price", None)
    discount = form.get("discount")
    if discount:
        try:
            prod["discount"] = float(discount)
        except ValueError:
            pass
    else:
        prod.pop("discount", None)
    save_products(products)
    flash("Product updated.", "success")
    return redirect(url_for("admin_dashboard") + "#admin-products")


@app.route("/admin/product/delete/<int:product_id>", methods=["POST"])
@login_required
def admin_delete_product(product_id):
    products = load_products()
    products = [p for p in products if p.get("id") != product_id]
    save_products(products)
    flash("Product deleted.", "success")
    return redirect(url_for("admin_dashboard") + "#admin-products")


@app.route("/admin/category/add", methods=["POST"])
@login_required
def admin_add_category():
    label = request.form.get("label", "").strip()
    if not label:
        return redirect(url_for("admin_dashboard") + "#admin-categories")
    categories = load_categories()
    slug = slugify(label)
    if not slug:
        return redirect(url_for("admin_dashboard") + "#admin-categories")
    original_slug = slug
    i = 1
    while slug in categories:
        i += 1
        slug = f"{original_slug}-{i}"
    categories[slug] = label
    save_categories(categories)
    flash("Category added.", "success")
    return redirect(url_for("admin_dashboard") + "#admin-categories")


@app.route("/admin/offer/add", methods=["POST"])
@login_required
def admin_add_offer():
    offers = load_offers()
    text = request.form.get("text", "").strip()
    if not text:
        return redirect(url_for("admin_dashboard") + "#admin-offers")
    offers.append({"text": text})
    save_offers(offers)
    flash("Offer added.", "success")
    return redirect(url_for("admin_dashboard") + "#admin-offers")


@app.route("/admin/offer/delete/<int:index>", methods=["POST"])
@login_required
def admin_delete_offer(index):
    offers = load_offers()
    if 0 <= index < len(offers):
        offers.pop(index)
        save_offers(offers)
    return redirect(url_for("admin_dashboard") + "#admin-offers")


@app.route("/admin/hero/update", methods=["POST"])
@login_required
def admin_update_hero():
    hero = load_hero()
    form = request.form
    file = request.files.get("hero_image")
    hero["headline"] = form.get("headline", "").strip()
    hero["subheadline"] = form.get("subheadline", "").strip()
    saved_filename = save_upload(file, prefix="hero_")
    if saved_filename:
        hero["image"] = saved_filename
    save_hero(hero)
    flash("Hero section updated.", "success")
    return redirect(url_for("admin_dashboard") + "#admin-offers")


# --------------------------------------------------------------------------
# Public routes
# --------------------------------------------------------------------------

@app.route("/")
def home():
    products = load_products()
    trending = [p for p in products if "trending" in p.get("tags", [])][:8]
    bestsellers = [p for p in products if "bestseller" in p.get("tags", [])][:8]
    best_designs = [p for p in products if "best_design" in p.get("tags", [])][:8]
    stitch_the_look = [p for p in products if "look" in p.get("tags", [])][:6]
    top10 = sorted([p for p in products if p.get("rank")], key=lambda p: p["rank"])[:10]
    category_map = load_categories()
    categories = build_categories(products, category_map)
    hero = load_hero()
    return render_template(
        "index.html",
        trending=trending,
        bestsellers=bestsellers,
        best_designs=best_designs,
        stitch_the_look=stitch_the_look,
        top10=top10,
        categories=categories,
        hero=hero,
    )


@app.route("/category/<slug>")
def category(slug):
    category_map = load_categories()
    if slug not in category_map:
        abort(404)
    products = load_products()
    items = [p for p in products if p["category"] == slug]
    return render_template("category.html", label=category_map[slug], slug=slug, items=items)


@app.route("/product/<int:product_id>")
def product(product_id):
    products = load_products()
    match = next((p for p in products if p["id"] == product_id), None)
    if not match:
        abort(404)
    related = [p for p in products if p["category"] == match["category"] and p["id"] != match["id"]][:4]
    return render_template("product.html", p=match, related=related)


@app.route("/trending")
def trending_page():
    products = load_products()
    items = [p for p in products if "trending" in p.get("tags", [])]
    return render_template("category.html", label="Trending Now", slug="trending", items=items)


@app.route("/bestsellers")
def bestsellers_page():
    products = load_products()
    items = [p for p in products if "bestseller" in p.get("tags", [])]
    return render_template("category.html", label="Bestsellers", slug="bestsellers", items=items)


@app.route("/stitch-the-look")
def stitch_the_look_page():
    products = load_products()
    items = [p for p in products if "look" in p.get("tags", [])]
    return render_template("look.html", items=items)


@app.route("/about")
def about():
    return render_template("about.html")


# --------------------------------------------------------------------------
# Local SEO: Gurugram + category landing pages
# --------------------------------------------------------------------------

LOCAL_SEO_FAQS = [
    ("Do you provide home measurement visits across Gurugram?",
     "Yes — we cover all major sectors and localities in Gurugram. Book a "
     "free home measurement visit and our team will confirm a convenient time."),
    ("How long does stitching usually take?",
     "Most designs are ready within a few days of your measurement visit and "
     "fabric confirmation. Structured designs that need a trial fitting may "
     "take a little longer."),
    ("Do I need to visit a shop?",
     "No — measurement, fabric selection, fitting, and delivery all happen "
     "at your doorstep in Gurugram."),
    ("How is pricing decided?",
     "Pricing depends on fabric, fit, and finishing details, and is "
     "confirmed during your free home measurement visit."),
]


@app.route("/gurugram")
def gurugram_hub():
    products = load_products()
    category_map = load_categories()
    categories = build_categories(products, category_map)
    business = load_business()
    return render_template(
        "local_seo_hub.html",
        categories=categories,
        business=business,
    )


@app.route("/gurugram/<slug>")
def gurugram_category(slug):
    category_map = load_categories()
    if slug not in category_map:
        abort(404)
    products = load_products()
    items = [p for p in products if p["category"] == slug]
    business = load_business()
    return render_template(
        "local_seo.html",
        label=category_map[slug],
        slug=slug,
        items=items,
        business=business,
        faqs=LOCAL_SEO_FAQS,
    )


# --------------------------------------------------------------------------
# SEO infrastructure: robots.txt + sitemap.xml
# --------------------------------------------------------------------------

@app.route("/robots.txt")
def robots_txt():
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin",
        f"Sitemap: {SITE_URL.rstrip('/')}/sitemap.xml",
    ]
    return Response("\n".join(lines), mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap_xml():
    products = load_products()
    category_map = load_categories()
    base = SITE_URL.rstrip("/")
    urls = [
        base + url_for("home"),
        base + url_for("about"),
        base + url_for("trending_page"),
        base + url_for("bestsellers_page"),
        base + url_for("stitch_the_look_page"),
        base + url_for("gurugram_hub"),
    ]
    for slug in category_map:
        urls.append(base + url_for("category", slug=slug))
        urls.append(base + url_for("gurugram_category", slug=slug))
    for p in products:
        urls.append(base + url_for("product", product_id=p["id"]))
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        xml.append(f"  <url><loc>{u}</loc></url>")
    xml.append("</urlset>")
    return Response("\n".join(xml), mimetype="application/xml")


# --------------------------------------------------------------------------
# Error handlers
# --------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(400)
def bad_request(e):
    return render_template("404.html", message=str(getattr(e, "description", "Bad request."))), 400


@app.errorhandler(500)
def server_error(e):
    logger.exception("Server error")
    return render_template("404.html", message="Something went wrong on our end."), 500


if __name__ == "__main__":
    app.run(debug=DEBUG, host=os.environ.get("HOST", "127.0.0.1"),
             port=int(os.environ.get("PORT", 5000)))
