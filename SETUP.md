# SilaiGhar — Launch Checklist

This file tells you **exactly** what to do before going live. Work through it top-to-bottom.

---

## 1. Fill in your real business details

Open `data/business.json` and replace every placeholder with real values:

| Field | What to change |
|---|---|
| `phone_display` / `phone_tel` | Your real mobile number |
| `whatsapp_number` | Same number, digits only, no spaces or + (e.g. `919812345678`) |
| `email` | Your business email |
| `address_line1/2` | Your studio or home address |
| `pincode` | Your pincode |
| `latitude` / `longitude` | Exact coordinates (find on Google Maps) |
| `maps_url` | Link to your Google Maps listing |
| `instagram_url` / `facebook_url` | Your social profile URLs |
| `areas_served` | Add/remove localities based on where you actually operate |

---

## 2. Set environment variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Then fill in:

**SECRET_KEY** — generate a random one:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**ADMIN_PASSWORD_HASH** — generate a hash of your chosen password:
```bash
python3 -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('your-password-here'))"
```

Paste the output into `.env`.

**ADMIN_USERNAME** — change from `admin` to something less guessable.

**SITE_URL** — your live domain, e.g. `https://www.silaighar.in`

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

> Pillow is required to validate uploaded images server-side. If it fails to install, run: `pip install Pillow --break-system-packages`

---

## 4. Run in development

```bash
python app.py
```

Open `http://127.0.0.1:5000` in your browser.

---

## 5. Admin panel

Go to `http://127.0.0.1:5000/admin` (or `/admin/login` — you'll be redirected automatically).

**First steps in the admin:**
- Update the **hero section** headline and upload a real photo
- Add your **product designs** with real photos (PNG/JPG/WEBP, under 8 MB)
- Add **category entries** if you need more than the six defaults
- Add **offer messages** for the rolling ticker (e.g. "Free home measurement across Gurugram")

---

## 6. Replace placeholder product icons with real photos

Every product card and detail page will show the illustration icon until you upload a real photo. Upload photos via **Admin → Products → Edit** (the image upload field).

Recommended photo specs:
- Aspect ratio: **3:4** (portrait)
- Width: **800 px or more**
- Format: JPG or WEBP
- File size: **under 2 MB per image** (for fast load times)

---

## 7. Google Business Profile

1. Go to [business.google.com](https://business.google.com) and claim/create your listing.
2. Set business category to **Tailor** or **Clothing Alteration Service**.
3. Add your address, phone, website, and hours.
4. Upload at least 5 real photos of your work.
5. Ask early customers to leave a Google review.

This is the single biggest thing you can do for local SEO in Gurugram.

---

## 8. Google Search Console

1. Go to [search.google.com/search-console](https://search.google.com/search-console).
2. Add your domain and verify it.
3. Submit your sitemap: `https://www.silaighar.in/sitemap.xml`

---

## 9. Deploy to production (Gunicorn + Nginx)

**Do not use `python app.py` in production.** Use Gunicorn:

```bash
gunicorn app:app --workers 2 --bind 0.0.0.0:8000
```

Put Nginx in front as a reverse proxy and handle HTTPS with Let's Encrypt (Certbot).

Set `FLASK_ENV=production` and `FLASK_DEBUG=0` in your environment before starting.

---

## 10. Final checks before going live

- [ ] All phone numbers and WhatsApp numbers are real
- [ ] Admin password is strong and not `change-this-password`
- [ ] `SECRET_KEY` is a long random string, not the example value
- [ ] `FLASK_DEBUG=0` in production
- [ ] At least 5–10 products with real photos uploaded
- [ ] Hero section has a real headline and photo
- [ ] 3–5 offer ticker messages added
- [ ] Google Business Profile created and verified
- [ ] Sitemap submitted to Search Console
- [ ] HTTPS is working (SSL certificate installed)

---

## Local SEO pages

The following pages are automatically live once you deploy:

| URL | Purpose |
|---|---|
| `/gurugram` | Hub page for all Gurugram service areas |
| `/gurugram/blouse` | Blouses in Gurugram |
| `/gurugram/kurta` | Kurtas & Kurtis in Gurugram |
| `/gurugram/bridal` | Bridal in Gurugram |
| … one per category | Automatically created for each category |

These pages have **FAQ schema markup** built in, which helps them appear in Google's featured snippets.
