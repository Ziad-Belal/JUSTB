"""
Receipt Visual Preview — JustB
================================
Run from your project root:
    python preview_receipt.py

Generates  receipt_preview.png  and opens it automatically.
Shows the receipt EXACTLY as it will print — including logo and QR code.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Fake sale data ─────────────────────────────────────────────────────────────
FAKE_SALE = {
    "id":           1,
    "user":         "Ziad",
    "items": [
        {"name": "Spiral Notebook A5",    "quantity": 2, "price": 45.00, "barcode": "001"},
        {"name": "Gel Pen Multicolor Set","quantity": 1, "price": 30.00, "barcode": "002"},
        {"name": "Gift Wrap Paper Roll",  "quantity": 3, "price": 15.00, "barcode": "003"},
        {"name": "Sticky Notes Pack",     "quantity": 2, "price": 20.00, "barcode": "004"},
    ],
    "subtotal":     220.00,
    "discount_pct": 10.0,
    "discount_amt": 22.00,
    "total":        198.00,
    "promo_code":   "SAVE10",
    "date":         "2026-03-06",
}

try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps
except ImportError:
    print("ERROR: Pillow not installed. Run:  pip install Pillow")
    sys.exit(1)

try:
    import qrcode
except ImportError:
    print("ERROR: qrcode not installed. Run:  pip install qrcode")
    sys.exit(1)

from datetime import datetime

# ══════════════════════════════════════════════════════════════════════════════
#  Settings
# ══════════════════════════════════════════════════════════════════════════════

LOGO_PATH   = r"C:\Users\Ziad\JUSTB\logo.png"
PAPER_W     = 384          # 58 mm thermal paper in dots
PAD         = 20           # left/right padding px
LINE_H      = 24           # pixels per text line
BG          = (255, 255, 255)
FG          = (15,  15,  15)
GRAY        = (150, 150, 150)
WEBSITE_URL = "https://justb-eg.com"

# ── Fonts (uses Courier New on Windows — perfect monospace match) ──────────────
def _font(size=13, bold=False):
    candidates_bold   = ["courbd.ttf", "DejaVuSansMono-Bold.ttf",  "LiberationMono-Bold.ttf"]
    candidates_normal = ["cour.ttf",   "DejaVuSansMono.ttf",       "LiberationMono.ttf"]
    candidates = candidates_bold if bold else candidates_normal
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            pass
    return ImageFont.load_default()

font_normal   = _font(13)
font_bold     = _font(14, bold=True)
font_large    = _font(18, bold=True)
font_small    = _font(11)

# ══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════════════════

def text_w(draw, text, font):
    try:
        return draw.textlength(text, font=font)
    except Exception:
        return len(text) * 8

def centered_x(draw, text, font, paper_w=PAPER_W, pad=PAD):
    w = text_w(draw, text, font)
    return pad + max(0, (paper_w - w) // 2)

# ══════════════════════════════════════════════════════════════════════════════
#  Build the preview image section by section
# ══════════════════════════════════════════════════════════════════════════════

sections = []   # list of PIL Image objects to stack vertically

def make_blank(h, bg=BG):
    return Image.new("RGB", (PAPER_W + PAD * 2, h), bg)

def add_text_img(text, font, color=FG, align="left", bg=BG, pad_top=4, pad_bot=4):
    img  = make_blank(LINE_H + pad_top + pad_bot, bg)
    draw = ImageDraw.Draw(img)
    w    = img.width
    if align == "center":
        x = centered_x(draw, text, font, PAPER_W, PAD)
    elif align == "right":
        x = PAD + PAPER_W - int(text_w(draw, text, font)) - 4
    else:
        x = PAD
    draw.text((x, pad_top), text, font=font, fill=color)
    return img

def add_divider(char="-", color=GRAY):
    img  = make_blank(16)
    draw = ImageDraw.Draw(img)
    line = char * 42
    draw.text((PAD, 2), line[:42], font=font_small, fill=color)
    return img

def add_spacer(h=10):
    return make_blank(h)

# ── 1. LOGO ────────────────────────────────────────────────────────────────────
if os.path.exists(LOGO_PATH):
    try:
        logo = Image.open(LOGO_PATH).convert("RGBA")
        # White background for transparency
        bg_logo = Image.new("RGB", logo.size, (255, 255, 255))
        bg_logo.paste(logo, mask=logo.split()[3])
        logo = bg_logo
        # Scale to paper width
        ratio  = PAPER_W / logo.width
        new_h  = max(1, int(logo.height * ratio))
        logo   = logo.resize((PAPER_W, new_h), Image.LANCZOS)
        # Paste centred
        canvas = make_blank(new_h + 10)
        canvas.paste(logo, (PAD, 5))
        sections.append(canvas)
        print("✓ Logo loaded")
    except Exception as e:
        print(f"⚠ Logo error: {e}")
        sections.append(add_text_img("[Logo not rendered]", font_small, GRAY, "center"))
else:
    print(f"⚠ Logo file not found at: {LOGO_PATH}")
    sections.append(add_text_img("[logo.png not found]", font_small, GRAY, "center"))

sections.append(add_spacer(8))

# ── 2. SHOP HEADER ─────────────────────────────────────────────────────────────
sections.append(add_text_img("JustB", font_large, FG, "center"))
sections.append(add_spacer(8))

# ── 3. METADATA ────────────────────────────────────────────────────────────────
sections.append(add_divider("="))
date_str = datetime.now().strftime("%d/%m/%Y  %H:%M")
sections.append(add_text_img(f"Receipt # : {FAKE_SALE['id']:06d}", font_normal, FG, "left"))
sections.append(add_text_img(f"Date      : {date_str}",             font_normal, FG, "left"))
sections.append(add_text_img(f"Cashier   : {FAKE_SALE['user']}",    font_normal, FG, "left"))
sections.append(add_divider("="))

# ── 4. ITEMS ───────────────────────────────────────────────────────────────────
MAX_NAME = 20
sections.append(add_text_img(
    f"{'ITEM':<20} {'QTY':>3}  {'PRICE':>6}  {'TOTAL':>7}",
    font_bold, FG, "left"))
sections.append(add_divider("-"))

subtotal = 0.0
for item in FAKE_SALE["items"]:
    name       = str(item["name"])
    qty        = int(item["quantity"])
    price      = float(item["price"])
    line_total = qty * price
    subtotal  += line_total
    sections.append(add_text_img(
        f"{name[:MAX_NAME]:<20} {qty:>3}  {price:>6.2f}  {line_total:>7.2f}",
        font_normal, FG, "left"))
    for start in range(MAX_NAME, len(name), MAX_NAME):
        sections.append(add_text_img(
            f"  {name[start:start+MAX_NAME]}", font_normal, FG, "left"))

sections.append(add_divider("-"))

# ── 5. TOTALS ──────────────────────────────────────────────────────────────────
LW = 22
disc_pct = FAKE_SALE["discount_pct"]
disc_amt = subtotal * (disc_pct / 100.0)
final    = subtotal - disc_amt

sections.append(add_text_img(
    f"{'Subtotal:':>{LW}}  {subtotal:>8.2f} EGP", font_normal, GRAY, "left"))

if disc_pct > 0:
    sections.append(add_text_img(
        f"{'Discount (' + str(int(disc_pct)) + '%):':>{LW}} -{disc_amt:>8.2f} EGP",
        font_normal, (34, 139, 34), "left"))

sections.append(add_divider("="))
sections.append(add_text_img(
    f"{'TOTAL:':>{LW}}  {final:>8.2f} EGP", font_large, FG, "left"))

if FAKE_SALE["promo_code"]:
    sections.append(add_text_img(
        f"{'Promo:':>{LW}}  {FAKE_SALE['promo_code']}", font_small, GRAY, "left"))

# ── 6. FOOTER ──────────────────────────────────────────────────────────────────
sections.append(add_spacer(10))
sections.append(add_divider("~"))
sections.append(add_text_img("Thank you for shopping at JustB!", font_normal, FG,   "center"))
sections.append(add_text_img("We hope to see you again  :)",     font_normal, GRAY, "center"))
sections.append(add_divider("~"))
sections.append(add_spacer(12))

# ── 7. QR CODE ─────────────────────────────────────────────────────────────────
try:
    qr = qrcode.QRCode(
        version=3,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=4,
        border=2,
    )
    qr.add_data(WEBSITE_URL)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    # Scale to 60% of paper width, centred
    target_w = int(PAPER_W * 0.60)
    ratio    = target_w / qr_img.width
    new_h    = max(1, int(qr_img.height * ratio))
    qr_img   = qr_img.resize((target_w, new_h), Image.LANCZOS)

    canvas_h = new_h + 10
    canvas   = make_blank(canvas_h)
    x_off    = PAD + (PAPER_W - target_w) // 2
    canvas.paste(qr_img, (x_off, 5))
    sections.append(canvas)
    print("✓ QR code generated for:", WEBSITE_URL)
except Exception as e:
    print(f"⚠ QR error: {e}")
    sections.append(add_text_img("[QR Code]", font_small, GRAY, "center"))

sections.append(add_text_img("Scan to visit our website!", font_small, GRAY, "center"))
sections.append(add_text_img("justb-eg.com",               font_normal, FG,   "center"))
sections.append(add_spacer(20))

# ══════════════════════════════════════════════════════════════════════════════
#  Stack all sections and save
# ══════════════════════════════════════════════════════════════════════════════

total_h = sum(s.height for s in sections)
final_img = Image.new("RGB", (PAPER_W + PAD * 2, total_h), BG)

y = 0
for s in sections:
    final_img.paste(s, (0, y))
    y += s.height

# Add a subtle drop shadow border
bordered = ImageOps.expand(final_img, border=2, fill=(220, 220, 220))

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "receipt_preview.png")
bordered.save(out_path)

print(f"\n✓ Receipt preview saved!\n  → {out_path}\n")

# Auto-open
try:
    os.startfile(out_path)
    print("  Opening automatically...")
except Exception:
    print("  Open receipt_preview.png manually to view it.")