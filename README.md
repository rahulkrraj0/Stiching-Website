# SilaiGhar — Multi-Page Tailoring Storefront (Prototype)

A multi-page Flask website: 30 dummy products, no prices shown anywhere,
built around Trending / Top 10 / Stitch the Look / Bestsellers / Shop by
Category / Best Designs sections, plus a video spot for your reel.

## Run it

```bash
pip install -r requirements.txt
python app.py
```

Then open **http://127.0.0.1:5000**

## Project structure

```
silaighar_shop/
├── app.py                     # Flask routes
├── requirements.txt
├── data/
│   └── products.json          # 30 products (edit this to add/change products)
├── templates/
│   ├── base.html              # shared layout (nav, footer, FAB, snackbar)
│   ├── _macros.html           # reusable SVG "product photo" generator
│   ├── index.html             # homepage — all sections
│   ├── category.html          # category / trending / bestsellers listing
│   ├── product.html           # single product detail page
│   ├── look.html              # "Stitch the Look" page
│   ├── about.html
│   └── 404.html
└── static/
    ├── css/style.css          # vibrant Material Design theme
    ├── js/main.js             # ripple, snackbar, form, video fallback
    └── video/
        └── stitch-the-look.mp4   ← put your video here (see note in that folder)
```

## Adding / editing products

Everything lives in `data/products.json`. Each product looks like:

```json
{
  "id": 31,
  "name": "Your Design Name",
  "category": "kurta",
  "icon": "kurta",
  "color": "#6C3CE9",
  "fabric": "Cotton",
  "tags": ["trending", "bestseller"],
  "rank": null,
  "desc": "Short description shown on the product card and detail page."
}
```

- `category` must be one of: `blouse`, `kurta`, `saree-fall`, `suit`, `bridal`, `indo-western`
- `icon` must be one of: `blouse`, `kurta`, `saree`, `suit`, `bridal`, `indo`
- `tags` can include any of: `trending`, `bestseller`, `best_design`, `look`
- `rank` (1–10, or `null`) controls the **Top 10** section
- No `price` field exists anywhere in the app by design — add one back in `product.html` and `data/products.json` when you're ready to sell.

## Adding your video

Drop an `.mp4` file into `static/video/` named `stitch-the-look.mp4`.
It plays on the homepage and the `/stitch-the-look` page automatically.
If it's missing, a styled placeholder is shown instead — the site never breaks.

## Notes

- All product "photos" are generated inline SVGs (no stock images), so there's nothing to license or replace before going live.
- This is a prototype: the booking form and "Enquire" buttons show a confirmation message but do not send real requests anywhere yet.
