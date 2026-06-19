# gui/pos_screen.py
import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
from utils.helpers import load_json, save_json, get_today_date
import os
from datetime import datetime

# ── Logo path (receipt printing) ───────────────────────────────────────────────
# Dynamic: look for logo.png next to this file, then next to main.py, then fallback.
def _find_logo():
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logo.png"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "logo.png"),
        r"C:\Users\A\Desktop\JUSTB\logo.png",
        r"C:\Users\Ziad\JUSTB\logo.png",
    ]
    for p in candidates:
        if os.path.exists(p):
            return os.path.normpath(p)
    return candidates[0]   # return first candidate even if missing (will fail gracefully)

LOGO_PATH    = _find_logo()
UI_LOGO_PATH = LOGO_PATH

# ── Win32 printing ─────────────────────────────────────────────────────────────
try:
    import win32print
    import win32ui
    from win32.lib import win32con
    import win32api
    WIN32_AVAILABLE    = True
    WIN32API_AVAILABLE = True
except Exception:
    WIN32_AVAILABLE    = False
    WIN32API_AVAILABLE = False

# ── Pillow ─────────────────────────────────────────────────────────────────────
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# ══════════════════════════════════════════════════════════════════════════════
#  DESIGN TOKENS  — JustB Bright Luxury
# ══════════════════════════════════════════════════════════════════════════════

C = {
    # Light backgrounds
    "bg_root":    "#F7F5FF",   # soft lavender-white canvas
    "bg_card":    "#FFFFFF",   # pure white cards
    "bg_header":  "#FFFFFF",   # header
    "bg_panel":   "#F0EDFF",   # soft purple panel
    "bg_row_alt": "#FAF8FF",   # alternating row tint
    "bg_input":   "#FFFFFF",   # input bg

    # JustB brand colours (from logo)
    "teal":       "#1BBFBF",   # J
    "pink":       "#F0569A",   # U
    "orange":     "#F97316",   # S
    "purple":     "#8B5CF6",   # T
    "green":      "#22C55E",   # B

    # Text
    "text_dark":  "#1A1035",   # near-black
    "text_mid":   "#6B6B8A",   # mid grey
    "text_light": "#A8A8C0",   # subtle

    # Accents
    "gold":       "#D97706",   # warm amber total
    "border":     "#E8E4F8",   # soft border
    "border_acc": "#C4B8F5",   # accent border

    # Semantic
    "success":    "#16A34A",
    "danger":     "#DC2626",
    "warning":    "#D97706",
}

# Brand letter colours list
BRAND_COLORS = ["#1BBFBF", "#F0569A", "#F97316", "#8B5CF6", "#22C55E"]

FONT_BRAND  = ("Georgia",   22, "bold")
FONT_HEAD   = ("Georgia",   13, "bold")
FONT_LABEL  = ("Segoe UI",  10)
FONT_LABEL_B= ("Segoe UI",  10, "bold")
FONT_ENTRY  = ("Segoe UI",  11)
FONT_TOTAL  = ("Georgia",   20, "bold")
FONT_SMALL  = ("Segoe UI",   9)
FONT_BTN    = ("Segoe UI",  10, "bold")
FONT_BTN_LG = ("Segoe UI",  13, "bold")
FONT_SECTION= ("Segoe UI",   8, "bold")


# ══════════════════════════════════════════════════════════════════════════════
#  ESC/POS constants  (receipt — untouched)
# ══════════════════════════════════════════════════════════════════════════════

PAPER_WIDTH_DOTS   = 384
RECEIPT_CHAR_WIDTH = 32

ESC = b'\x1b'
GS  = b'\x1d'

INIT         = ESC + b'@'
ALIGN_LEFT   = ESC + b'a\x00'
ALIGN_CENTER = ESC + b'a\x01'
ALIGN_RIGHT  = ESC + b'a\x02'
BOLD_ON      = ESC + b'E\x01'
BOLD_OFF     = ESC + b'E\x00'
DBL_HEIGHT   = ESC + b'!\x10'
NORMAL_SIZE  = ESC + b'!\x00'
FEED_3       = ESC + b'd\x03'
CUT          = GS  + b'V\x01'


def _enc(text):
    return text.encode('cp850', errors='replace')

def _divider(char='-', w=RECEIPT_CHAR_WIDTH):
    return _enc(char * w) + b'\n'


# ══════════════════════════════════════════════════════════════════════════════
#  Logo → ESC/POS  (receipt)
# ══════════════════════════════════════════════════════════════════════════════

def _logo_escpos(path):
    if not PIL_AVAILABLE or not os.path.exists(path):
        return b''
    try:
        img = Image.open(path).convert('RGBA')
        bg  = Image.new('RGB', img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg.convert('L')
        ratio = PAPER_WIDTH_DOTS / img.width
        new_h = max(1, int(img.height * ratio))
        img   = img.resize((PAPER_WIDTH_DOTS, new_h), Image.LANCZOS)
        img   = img.point(lambda p: 0 if p < 160 else 255, '1')
        w_bytes = (PAPER_WIDTH_DOTS + 7) // 8
        height  = img.height
        header  = (GS + b'v0\x00'
                   + bytes([w_bytes & 0xFF, (w_bytes >> 8) & 0xFF])
                   + bytes([height   & 0xFF, (height   >> 8) & 0xFF]))
        px   = img.load()
        rows = bytearray()
        for y in range(height):
            for bx in range(w_bytes):
                byte = 0
                for bit in range(8):
                    x = bx * 8 + bit
                    if x < PAPER_WIDTH_DOTS and px[x, y] == 0:
                        byte |= (0x80 >> bit)
                rows.append(byte)
        return ALIGN_CENTER + header + bytes(rows) + b'\n'
    except Exception as e:
        print(f"[Logo] {e}")
        return b''


# ══════════════════════════════════════════════════════════════════════════════
#  QR Code → ESC/POS  (receipt — untouched)
# ══════════════════════════════════════════════════════════════════════════════

def _qr_escpos(url):
    if not PIL_AVAILABLE:
        return b''
    try:
        import qrcode
        qr = qrcode.QRCode(version=3,
                           error_correction=qrcode.constants.ERROR_CORRECT_M,
                           box_size=4, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img      = qr.make_image(fill_color="black", back_color="white").convert('RGB')
        target_w = int(PAPER_WIDTH_DOTS * 0.60)
        ratio    = target_w / img.width
        new_h    = max(1, int(img.height * ratio))
        img      = img.resize((target_w, new_h), Image.LANCZOS)
        img      = img.convert('L').point(lambda p: 0 if p < 128 else 255, '1')
        pad_left = (PAPER_WIDTH_DOTS - target_w) // 2
        w_bytes  = (PAPER_WIDTH_DOTS + 7) // 8
        height   = img.height
        header   = (GS + b'v0\x00'
                    + bytes([w_bytes & 0xFF, (w_bytes >> 8) & 0xFF])
                    + bytes([height   & 0xFF, (height   >> 8) & 0xFF]))
        px   = img.load()
        rows = bytearray()
        for y in range(height):
            for bx in range(w_bytes):
                byte = 0
                for bit in range(8):
                    x_full = bx * 8 + bit
                    x_img  = x_full - pad_left
                    if 0 <= x_img < target_w and px[x_img, y] == 0:
                        byte |= (0x80 >> bit)
                rows.append(byte)
        return ALIGN_CENTER + header + bytes(rows) + b'\n'
    except Exception as e:
        print(f"[QR] {e}")
        return b''


# ══════════════════════════════════════════════════════════════════════════════
#  Barcode → ESC/POS
# ══════════════════════════════════════════════════════════════════════════════

def _barcode_escpos(sale_id):
    """
    Prints a CODE128 barcode encoding 'RCPT-XXXXXX' via ESC/POS.
    When scanned, the Receipt Database will decode this and jump to the receipt.
    Falls back gracefully if python-barcode is unavailable.
    """
    code = f"RCPT-{sale_id:06d}"
    try:
        import barcode as pybarcode
        from barcode.writer import ImageWriter
        import io
        bc_class = pybarcode.get_barcode_class("code128")
        bc = bc_class(code, writer=ImageWriter())
        buf = io.BytesIO()
        bc.write(buf, options={"write_text": True, "quiet_zone": 2,
                               "module_width": 0.8, "module_height": 8.0})
        buf.seek(0)
        if not PIL_AVAILABLE:
            return b''
        img = Image.open(buf).convert("L")
        # Scale to paper width
        ratio = PAPER_WIDTH_DOTS / img.width
        new_h = max(1, int(img.height * ratio))
        img   = img.resize((PAPER_WIDTH_DOTS, new_h), Image.LANCZOS)
        img   = img.point(lambda p: 0 if p < 128 else 255, '1')
        w_bytes = (PAPER_WIDTH_DOTS + 7) // 8
        height  = img.height
        header  = (GS + b'v0\x00'
                   + bytes([w_bytes & 0xFF, (w_bytes >> 8) & 0xFF])
                   + bytes([height   & 0xFF, (height   >> 8) & 0xFF]))
        px   = img.load()
        rows = bytearray()
        for y in range(height):
            for bx in range(w_bytes):
                byte = 0
                for bit in range(8):
                    x = bx * 8 + bit
                    if x < PAPER_WIDTH_DOTS and px[x, y] == 0:
                        byte |= (0x80 >> bit)
                rows.append(byte)
        return ALIGN_CENTER + header + bytes(rows) + b'\n'
    except Exception as e:
        print(f"[Barcode] {e}")
        # Fallback: print the code as plain text so it's at least visible
        return ALIGN_CENTER + _enc(f"[ {code} ]") + b'\n'


# ══════════════════════════════════════════════════════════════════════════════
#  Receipt assembler
# ══════════════════════════════════════════════════════════════════════════════

def build_receipt(sale_id, sale_record, cashier, discount_pct=0.0, promo_code="", payment_method="Cash"):
    W        = RECEIPT_CHAR_WIDTH
    date_str = datetime.now().strftime("%d/%m/%Y  %H:%M")
    raw      = bytearray()

    raw += INIT

    # ── Logo image at the top (same as receipt_preview.png) ───────────────────
    logo_bytes = _logo_escpos(LOGO_PATH)
    if logo_bytes:
        raw += logo_bytes
    else:
        # Fallback: only print "JustB" text if logo image is missing
        raw += ALIGN_CENTER
        raw += BOLD_ON + DBL_HEIGHT
        raw += _enc("JustB") + b'\n'
        raw += NORMAL_SIZE + BOLD_OFF

    raw += b'\n'
    raw += _divider('=')
    raw += ALIGN_LEFT
    raw += _enc(f"Receipt # : {sale_id:06d}") + b'\n'
    raw += _enc(f"Date      : {date_str}") + b'\n'
    raw += _enc(f"Cashier   : {cashier}") + b'\n'
    raw += _enc(f"Payment   : {payment_method}") + b'\n'
    raw += _divider('=')
    raw += BOLD_ON
    raw += _enc(f"{'ITEM':<20} {'QTY':>3}  {'PRICE':>6}  {'TOTAL':>7}") + b'\n'
    raw += BOLD_OFF
    raw += _divider('-')

    subtotal = 0.0
    MAX_NAME = 20
    for item in sale_record["items"]:
        name       = str(item["name"])
        qty        = int(item["quantity"])
        price      = float(item["price"])
        line_total = qty * price
        subtotal  += line_total
        raw += _enc(f"{name[:MAX_NAME]:<20} {qty:>3}  {price:>6.2f}  {line_total:>7.2f}") + b'\n'
        for start in range(MAX_NAME, len(name), MAX_NAME):
            raw += _enc(f"  {name[start:start+MAX_NAME]}") + b'\n'

    raw += _divider('-')
    LW = W - 10
    raw += ALIGN_RIGHT
    raw += _enc(f"{'Subtotal:':>{LW}}  {subtotal:>8.2f} EGP") + b'\n'

    if discount_pct > 0:
        disc_amt = subtotal * (discount_pct / 100.0)
        taxable  = subtotal - disc_amt
        raw += _enc(f"{'Discount (' + str(int(discount_pct)) + '%):':>{LW}} -{disc_amt:>8.2f} EGP") + b'\n'
    else:
        disc_amt = 0.0
        taxable  = subtotal

    if sale_record.get('tax_pct', 0):
        tax_amt = taxable * (float(sale_record.get('tax_pct', 0)) / 100.0)
        raw += _enc(f"{'Tax (' + str(int(float(sale_record.get('tax_pct', 0)))) + '%):':>{LW}} {tax_amt:>8.2f} EGP") + b'\n'
        final = taxable + tax_amt
    else:
        final = taxable

    raw += _divider('=')
    raw += BOLD_ON + DBL_HEIGHT
    raw += _enc(f"{'TOTAL:':>{LW-2}}  {final:>8.2f} EGP") + b'\n'
    raw += NORMAL_SIZE + BOLD_OFF

    if promo_code:
        raw += ALIGN_RIGHT
        raw += _enc(f"{'Promo:':>{LW}}  {promo_code}") + b'\n'

    raw += ALIGN_CENTER
    raw += b'\n'
    raw += _divider('~')
    raw += _enc("Thank you for shopping at JustB!") + b'\n'
    raw += _enc("We hope to see you again  :)") + b'\n'
    raw += _divider('~')
    raw += b'\n'
    # ── Receipt lookup barcode ──────────────────────────────────────────────
    raw += _divider('-')
    raw += ALIGN_CENTER
    raw += _enc("RECEIPT LOOKUP") + b'\n'
    raw += _barcode_escpos(sale_id)
    raw += _enc(f"RCPT-{sale_id:06d}") + b'\n'
    raw += b'\n'
    # ───────────────────────────────────────────────────────────────────────
    raw += _qr_escpos("https://justb-eg.com")
    raw += ALIGN_CENTER
    raw += _enc("Scan to visit our website!") + b'\n'
    raw += _enc("justb-eg.com") + b'\n'
    raw += b'\n'
    raw += FEED_3
    raw += CUT
    return bytes(raw)


# ══════════════════════════════════════════════════════════════════════════════
#  UI Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _btn(parent, text, command, bg, hover, fg="#FFFFFF",
         font=FONT_BTN, padx=18, pady=9, radius=None):
    """Flat button with hover colour swap."""
    b = tk.Label(parent, text=text, font=font,
                 bg=bg, fg=fg, cursor="hand2",
                 relief="flat", padx=padx, pady=pady)
    b.bind("<Button-1>", lambda e: command())
    b.bind("<Enter>",    lambda e: b.config(bg=hover))
    b.bind("<Leave>",    lambda e: b.config(bg=bg))
    return b


def _entry(parent, width=24, font=FONT_ENTRY):
    return tk.Entry(
        parent, font=font, width=width,
        bg=C["bg_input"], fg=C["text_dark"],
        insertbackground=C["purple"],
        relief="flat",
        highlightthickness=2,
        highlightbackground=C["border"],
        highlightcolor=C["purple"],
    )


def _card(parent, bg=None, pad=16, **kw):
    bg = bg or C["bg_card"]
    return tk.Frame(parent, bg=bg, relief="flat",
                    highlightthickness=1,
                    highlightbackground=C["border"],
                    padx=pad, pady=pad, **kw)


def _section_label(parent, text, bg=None):
    bg = bg or C["bg_card"]
    tk.Label(parent, text=text, font=FONT_SECTION,
             bg=bg, fg=C["text_light"],
             anchor="w").pack(fill="x", pady=(0, 6))


def _hsep(parent, bg=None):
    tk.Frame(parent, bg=bg or C["border"], height=1).pack(fill="x", pady=8)


# ══════════════════════════════════════════════════════════════════════════════
#  POSScreen  — JustB Bright Luxury UI
# ══════════════════════════════════════════════════════════════════════════════

class POSScreen:
    def __init__(self, root, data_dir, frame_parent=None, user=None):
        self.root      = root
        self.data_dir  = data_dir
        self.user      = user or {"username": "Unknown"}
        self.user_name = self.user.get("username", "Unknown")

        self.frame = tk.Frame(frame_parent or root, bg=C["bg_root"])
        self.frame.pack(fill="both", expand=True)

        self.cart          = []
        self._discount_pct = 0.0
        self._promo_code   = ""
        self._tax_pct      = self._load_tax_pct()
        self._logo_img     = None   # keep reference to avoid GC
        self._products_cache = None  # cache for speed

        self._build_ui()
        # Restore focus to barcode entry whenever it loses focus to a non-entry widget
        self.barcode_entry.bind("<FocusOut>", self._on_barcode_focus_out)
        # Check for low stock on startup


    def _refocus(self):
        """Snap focus back to the barcode entry."""
        self.barcode_entry.focus_set()

    def _on_barcode_focus_out(self, event):
        """When barcode field loses focus, return it unless focus went to another Entry or popup."""
        def _check():
            focused = self.frame.focus_get()
            # Only steal back if focus went to a non-Entry widget (label, frame, treeview, etc.)
            # or went to nothing — never steal from Entry, Button, Combobox, or Toplevel
            if focused is None or isinstance(focused, (tk.Frame, tk.Canvas, ttk.Treeview)):
                self.barcode_entry.focus_set()
        self.frame.after(150, _check)

    def _settings_path(self):
        return os.path.join(self.data_dir, "system_settings.json")

    def _load_system_settings(self):
        settings = load_json(self._settings_path())
        if isinstance(settings, dict):
            return settings
        return {}

    def _load_tax_pct(self):
        settings = self._load_system_settings()
        try:
            return float(settings.get("tax_pct", 0.0))
        except Exception:
            return 0.0

    # ─────────────────────────────────────────────────────────────────────────
    def _build_ui(self):

        # ╔══════════════════════════════════════════════════════════════╗
        #  HEADER
        # ╚══════════════════════════════════════════════════════════════╝
        hdr = tk.Frame(self.frame, bg=C["bg_header"],
                       highlightthickness=1,
                       highlightbackground=C["border"])
        hdr.pack(fill="x")

        # ── Logo (top-left)
        logo_frame = tk.Frame(hdr, bg=C["bg_header"])
        logo_frame.pack(side="left", padx=(16, 0), pady=8)

        if PIL_AVAILABLE and os.path.exists(UI_LOGO_PATH):
            try:
                raw = Image.open(UI_LOGO_PATH).convert("RGBA")
                # Resize to 54px height keeping ratio
                ratio  = 54 / raw.height
                new_w  = max(1, int(raw.width * ratio))
                raw    = raw.resize((new_w, 54), Image.LANCZOS)
                self._logo_img = ImageTk.PhotoImage(raw)
                tk.Label(logo_frame, image=self._logo_img,
                         bg=C["bg_header"]).pack(side="left")
            except Exception:
                self._fallback_brand(logo_frame)
        else:
            self._fallback_brand(logo_frame)

        # ── "Point of Sale" subtitle
        tk.Label(hdr, text="Point of Sale",
                 font=("Segoe UI", 10), bg=C["bg_header"],
                 fg=C["text_light"]).pack(side="left", padx=(10, 0), pady=8)

        # ── Right side: cashier + clock
        right_hdr = tk.Frame(hdr, bg=C["bg_header"])
        right_hdr.pack(side="right", padx=20, pady=8)

        self.clock_lbl = tk.Label(right_hdr, font=FONT_SMALL,
                                  bg=C["bg_header"], fg=C["text_light"])
        self.clock_lbl.pack(side="right", padx=(12, 0))

        # Switch user button
        sw = tk.Label(right_hdr, text="⇄  Switch User",
                      font=FONT_SMALL, bg=C["bg_header"],
                      fg=C["text_mid"], cursor="hand2",
                      relief="flat",
                      highlightthickness=1,
                      highlightbackground=C["border_acc"],
                      padx=10, pady=5)
        sw.pack(side="right", padx=(0, 8))
        sw.bind("<Button-1>", lambda e: self.switch_user())
        sw.bind("<Enter>",    lambda e: sw.config(bg=C["bg_panel"], fg=C["purple"]))
        sw.bind("<Leave>",    lambda e: sw.config(bg=C["bg_header"], fg=C["text_mid"]))

        # Cashier badge
        badge = tk.Frame(right_hdr, bg=C["purple"], padx=10, pady=4)
        badge.pack(side="right", padx=(0, 8))
        tk.Label(badge, text=f"  {self.user_name}  ",
                 font=FONT_LABEL_B, bg=C["purple"],
                 fg="#FFFFFF").pack()

        self._tick_clock()

        # ╔══════════════════════════════════════════════════════════════╗
        #  BODY  —  left (cart) + right (summary)
        # ╚══════════════════════════════════════════════════════════════╝
        body = tk.Frame(self.frame, bg=C["bg_root"])
        body.pack(fill="both", expand=True, padx=14, pady=12)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=1, minsize=270)
        body.rowconfigure(0, weight=1)

        # ════════════════════════
        #  LEFT COLUMN
        # ════════════════════════
        left = tk.Frame(body, bg=C["bg_root"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        # ── Scan card ─────────────────────────────────────────────────
        scan = _card(left, pad=14)
        scan.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        scan.columnconfigure(1, weight=1)

        # coloured top accent bar
        tk.Frame(scan, bg=C["teal"], height=3).grid(
            row=0, column=0, columnspan=3, sticky="ew",
            padx=0, pady=(0, 10))

        tk.Label(scan, text="SCAN / ENTER BARCODE",
                 font=FONT_SECTION, bg=C["bg_card"],
                 fg=C["text_light"]).grid(
                     row=1, column=0, columnspan=3, sticky="w", pady=(0, 6))

        # barcode icon label
        tk.Label(scan, text="▦", font=("Segoe UI", 16),
                 bg=C["bg_card"], fg=C["teal"]).grid(
                     row=2, column=0, padx=(0, 8))

        self.barcode_entry = _entry(scan, width=30)
        self.barcode_entry.grid(row=2, column=1, sticky="ew", ipady=7)
        self.barcode_entry.bind("<Return>", lambda e: self.add_to_cart())
        self.barcode_entry.focus()

        _btn(scan, "  ADD  ", self.add_to_cart,
             C["teal"], "#159F9F",
             font=FONT_BTN, padx=18, pady=7).grid(
                 row=2, column=2, padx=(10, 0))

        # ── Cart treeview card ────────────────────────────────────────
        tree_card = tk.Frame(left, bg=C["bg_card"],
                             highlightthickness=1,
                             highlightbackground=C["border"])
        tree_card.grid(row=1, column=0, sticky="nsew")
        tree_card.rowconfigure(1, weight=1)
        tree_card.columnconfigure(0, weight=1)

        # Cart sub-header
        ch = tk.Frame(tree_card, bg=C["bg_panel"], padx=14, pady=10)
        ch.grid(row=0, column=0, columnspan=2, sticky="ew")

        # rainbow dot row
        dot_frame = tk.Frame(ch, bg=C["bg_panel"])
        dot_frame.pack(side="left")
        for col in BRAND_COLORS:
            tk.Label(dot_frame, text="●", font=("Segoe UI", 8),
                     bg=C["bg_panel"], fg=col).pack(side="left", padx=1)
        tk.Label(ch, text="  CART",
                 font=FONT_SECTION, bg=C["bg_panel"],
                 fg=C["text_mid"]).pack(side="left")
        self.item_count_lbl = tk.Label(ch, text="0 items",
                                        font=FONT_SMALL,
                                        bg=C["bg_panel"], fg=C["purple"])
        self.item_count_lbl.pack(side="right")

        # Treeview style
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("JB.Treeview",
                         background=C["bg_card"],
                         foreground=C["text_dark"],
                         fieldbackground=C["bg_card"],
                         rowheight=38,
                         font=("Segoe UI", 10),
                         borderwidth=0, relief="flat")
        style.configure("JB.Treeview.Heading",
                         background=C["bg_panel"],
                         foreground=C["text_mid"],
                         font=("Segoe UI", 9, "bold"),
                         relief="flat", borderwidth=0)
        style.map("JB.Treeview",
                  background=[("selected", C["bg_panel"])],
                  foreground=[("selected", C["purple"])])
        style.layout("JB.Treeview",
                     [('Treeview.treearea', {'sticky': 'nswe'})])

        cols = ("Del", "Name", "Qty", "Unit Price", "Total")
        self.tree = ttk.Treeview(tree_card, columns=cols,
                                  show="headings", selectmode="browse",
                                  style="JB.Treeview")
        cw = {"Del": 40, "Name": 240, "Qty": 60, "Unit Price": 110, "Total": 110}
        for col in cols:
            header = "" if col == "Del" else col.upper()
            self.tree.heading(col, text=header)
            self.tree.column(col, anchor="center",
                              width=cw[col], minwidth=cw[col])
        self.tree.tag_configure("even", background=C["bg_card"])
        self.tree.tag_configure("odd",  background=C["bg_row_alt"])

        self.tree.bind("<ButtonRelease-1>", self._on_tree_click)

        vsb = ttk.Scrollbar(tree_card, orient="vertical",
                             command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=1, column=0, sticky="nsew")
        vsb.grid(row=1,  column=1, sticky="ns")

        # ── Remove selected item button (below cart) ──────────────────
        remove_bar = tk.Frame(tree_card, bg=C["bg_card"], padx=14, pady=8)
        remove_bar.grid(row=2, column=0, columnspan=2, sticky="ew")

        remove_btn = tk.Label(
            remove_bar,
            text="✕  REMOVE SELECTED ITEM",
            font=FONT_BTN,
            bg=C["bg_card"], fg=C["danger"],
            cursor="hand2",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#FECACA",
            padx=14, pady=7
        )
        remove_btn.pack(fill="x")
        remove_btn.bind("<Button-1>", lambda e: self.remove_selected_item())
        remove_btn.bind("<Enter>",    lambda e: remove_btn.config(bg="#FEF2F2"))
        remove_btn.bind("<Leave>",    lambda e: remove_btn.config(bg=C["bg_card"]))

        # ════════════════════════
        #  RIGHT COLUMN
        # ════════════════════════
        right = tk.Frame(body, bg=C["bg_root"])
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)

        # ── Promo card ────────────────────────────────────────────────
        promo_card = _card(right, pad=14)
        promo_card.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        promo_card.columnconfigure(0, weight=1)

        # pink accent bar
        tk.Frame(promo_card, bg=C["pink"], height=3).pack(
            fill="x", pady=(0, 10))

        _section_label(promo_card, "PROMO CODE")

        row_p = tk.Frame(promo_card, bg=C["bg_card"])
        row_p.pack(fill="x")
        row_p.columnconfigure(0, weight=1)

        self.promo_entry = _entry(row_p, width=14)
        self.promo_entry.grid(row=0, column=0, sticky="ew", ipady=6)

        _btn(row_p, "APPLY", self.apply_promo,
             C["pink"], "#D0457F",
             font=FONT_BTN, padx=14, pady=6).grid(
                 row=0, column=1, padx=(8, 0))

        self.promo_status = tk.Label(promo_card, text="",
                                      font=FONT_SMALL,
                                      bg=C["bg_card"],
                                      fg=C["success"],
                                      anchor="w")
        self.promo_status.pack(fill="x", pady=(6, 0))

        # ── Totals card ───────────────────────────────────────────────
        tot_card = _card(right, pad=16)
        tot_card.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        tot_card.columnconfigure(1, weight=1)

        # orange accent bar
        tk.Frame(tot_card, bg=C["orange"], height=3).grid(
            row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        tk.Label(tot_card, text="ORDER SUMMARY",
                 font=FONT_SECTION, bg=C["bg_card"],
                 fg=C["text_light"]).grid(
                     row=1, column=0, columnspan=2,
                     sticky="w", pady=(0, 10))

        # Subtotal
        tk.Label(tot_card, text="Subtotal",
                 font=FONT_LABEL, bg=C["bg_card"],
                 fg=C["text_mid"]).grid(row=2, column=0, sticky="w", pady=4)
        self.subtotal_lbl = tk.Label(tot_card, text="EGP 0.00",
                                      font=FONT_LABEL_B,
                                      bg=C["bg_card"], fg=C["text_dark"])
        self.subtotal_lbl.grid(row=2, column=1, sticky="e", pady=4)

        # Discount
        tk.Label(tot_card, text="Discount",
                 font=FONT_LABEL, bg=C["bg_card"],
                 fg=C["text_mid"]).grid(row=3, column=0, sticky="w", pady=4)
        self.discount_lbl = tk.Label(tot_card, text="—",
                                      font=FONT_LABEL_B,
                                      bg=C["bg_card"], fg=C["success"])
        self.discount_lbl.grid(row=3, column=1, sticky="e", pady=4)

        # Tax
        tk.Label(tot_card, text="Tax",
                 font=FONT_LABEL, bg=C["bg_card"],
                 fg=C["text_mid"]).grid(row=4, column=0, sticky="w", pady=4)
        self.tax_lbl = tk.Label(tot_card, text="EGP 0.00",
                                font=FONT_LABEL_B,
                                bg=C["bg_card"], fg=C["text_dark"])
        self.tax_lbl.grid(row=4, column=1, sticky="e", pady=4)

        # Separator
        tk.Frame(tot_card, bg=C["border"], height=1).grid(
            row=5, column=0, columnspan=2, sticky="ew", pady=10)

        # Total
        tk.Label(tot_card, text="TOTAL",
                 font=("Segoe UI", 9, "bold"),
                 bg=C["bg_card"], fg=C["text_mid"]).grid(
                     row=6, column=0, sticky="w")
        self.total_lbl = tk.Label(tot_card, text="EGP 0.00",
                                   font=FONT_TOTAL,
                                   bg=C["bg_card"], fg=C["gold"])
        self.total_lbl.grid(row=6, column=1, sticky="e")

        # ── Spacer ────────────────────────────────────────────────────
        tk.Frame(right, bg=C["bg_root"]).grid(row=2, column=0, sticky="nsew")

        # ── Action buttons ────────────────────────────────────────────
        acts = tk.Frame(right, bg=C["bg_root"])
        acts.grid(row=3, column=0, sticky="ew")
        acts.columnconfigure(0, weight=1)

        # Finalize — green full-width, tall, prominent
        fin = tk.Frame(acts, bg=C["green"],
                       highlightthickness=2,
                       highlightbackground=C["success"])
        fin.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        fin_lbl = tk.Label(fin,
                           text="✦  FINALIZE SALE  ✦",
                           font=FONT_BTN_LG,
                           bg=C["green"], fg="#FFFFFF",
                           cursor="hand2",
                           padx=0, pady=14)
        fin_lbl.pack(fill="x")
        fin_lbl.bind("<Button-1>", lambda e: self.finalize_sale())
        fin_lbl.bind("<Enter>",    lambda e: fin_lbl.config(bg="#16A34A"))
        fin_lbl.bind("<Leave>",    lambda e: fin_lbl.config(bg=C["green"]))

        # Clear cart — subtle outlined
        clr_lbl = tk.Label(acts,
                            text="CLEAR CART",
                            font=FONT_BTN,
                            bg=C["bg_card"], fg=C["text_mid"],
                            cursor="hand2",
                            relief="flat",
                            highlightthickness=1,
                            highlightbackground=C["border_acc"],
                            padx=0, pady=9)
        clr_lbl.grid(row=1, column=0, sticky="ew")
        clr_lbl.bind("<Button-1>", lambda e: self.clear_cart())
        clr_lbl.bind("<Enter>",    lambda e: clr_lbl.config(bg=C["bg_panel"]))
        clr_lbl.bind("<Leave>",    lambda e: clr_lbl.config(bg=C["bg_card"]))

        # ── Footer tagline ────────────────────────────────────────────
        tk.Label(self.frame,
                 text="justb-eg.com  ·  Stationery & Gifts",
                 font=("Segoe UI", 8),
                 bg=C["bg_root"], fg=C["text_light"]).pack(
                     side="bottom", pady=5)

    # ─────────────────────────────────────────────────────────────────────────
    def _fallback_brand(self, parent):
        """Show coloured JUSTB letters if logo file not found."""
        for letter, color in zip("JUSTB", BRAND_COLORS):
            tk.Label(parent, text=letter,
                     font=FONT_BRAND,
                     bg=C["bg_header"], fg=color).pack(side="left")

    def _tick_clock(self):
        now = datetime.now().strftime("%a  %d %b  %H:%M")
        self.clock_lbl.config(text=now)
        self.frame.after(30000, self._tick_clock)

    # ── helpers ───────────────────────────────────────────────────────────────
    def _products_path(self): return os.path.join(self.data_dir, "products.json")
    def _sales_path(self):    return os.path.join(self.data_dir, "sales.json")

    def _load_products(self, force=False):
        """Return products list from cache; reload from disk only when forced."""
        if self._products_cache is None or force:
            self._products_cache = load_json(self._products_path())
        return self._products_cache

    def _invalidate_product_cache(self):
        self._products_cache = None

    def _check_low_stock_alert(self):
        """Show a non-blocking low-stock warning banner if any products are low."""
        LOW = 5
        products = self._load_products(force=True)
        low_items = [p for p in products if int(p.get("quantity", 0)) <= LOW]
        if not low_items:
            return
        names = ", ".join(p["name"] for p in low_items[:5])
        extra = f" (+{len(low_items)-5} more)" if len(low_items) > 5 else ""
        messagebox.showwarning(
            "⚠ Low Stock Alert",
            f"{len(low_items)} product(s) are low or out of stock:\n\n"
            f"{names}{extra}\n\nPlease restock soon."
        )

    # ── cart logic ────────────────────────────────────────────────────────────

    def add_to_cart(self):
        barcode = self.barcode_entry.get().strip()
        if not barcode:
            return
        products = self._load_products()
        product  = next((p for p in products
                         if str(p.get("barcode", "")) == barcode), None)
        if not product:
            messagebox.showerror("Not Found",
                "Product not in inventory.\nAdd it first in the Products tab.")
            self.barcode_entry.delete(0, tk.END)
            self._refocus()
            return

        available = int(product.get("quantity", 0))
        in_cart   = sum(i["quantity"] for i in self.cart
                        if i["barcode"] == barcode)
        remaining = max(0, available - in_cart)
        if remaining <= 0:
            messagebox.showinfo("Out of Stock",
                f"Maximum stock reached ({available} units).")
            self.barcode_entry.delete(0, tk.END)
            self._refocus()
            return

        qty = simpledialog.askinteger(
            "Quantity",
            f"How many units?\n(max {remaining} available)",
            minvalue=1, maxvalue=remaining, parent=self.frame)
        if qty is None:
            self.barcode_entry.delete(0, tk.END)
            self._refocus()
            return

        for item in self.cart:
            if item["barcode"] == barcode:
                item["quantity"] += qty
                self.update_tree()
                self.update_total()
                self.barcode_entry.delete(0, tk.END)
                self._refocus()
                return

        self.cart.append({
            "barcode":  product["barcode"],
            "name":     product["name"],
            "price":    float(product["price"]),
            "quantity": qty,
        })
        self.update_tree()
        self.update_total()
        self.barcode_entry.delete(0, tk.END)
        self._refocus()

    def remove_selected_item(self):
        """Remove the selected cart item and restore its quantity to inventory."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("No Selection", "Please select an item in the cart to remove.")
            self._refocus()
            return

        # Get the index of the selected row
        all_items = self.tree.get_children()
        idx = list(all_items).index(selected[0])

        if idx < 0 or idx >= len(self.cart):
            self._refocus()
            return

        self._remove_cart_item(idx)

    def _remove_cart_item(self, idx, remove_qty=None):
        item = self.cart[idx]
        item_name    = item["name"]
        item_barcode = item["barcode"]
        item_qty     = int(item["quantity"])

        if remove_qty is None:
            remove_qty = item_qty
            if item_qty > 1:
                remove_qty = simpledialog.askinteger(
                    "Remove Quantity",
                    f"How many units of '{item_name}' do you want to remove?",
                    minvalue=1, maxvalue=item_qty,
                    parent=self.frame)
                if remove_qty is None:
                    self._refocus()
                    return

        if remove_qty < 1 or remove_qty > item_qty:
            self._refocus()
            return

        confirm = messagebox.askyesno(
            "Remove Item",
            f"Remove {remove_qty} of '{item_name}' from the cart?\n"
            f"Stock will be restored."
        )
        if not confirm:
            self._refocus()
            return

        # Restore quantity in inventory
        products = load_json(self._products_path())
        for prod in products:
            if str(prod.get("barcode", "")) == str(item_barcode):
                prod["quantity"] = int(prod.get("quantity", 0)) + remove_qty
                break
        save_json(self._products_path(), products)
        self._invalidate_product_cache()

        if remove_qty >= item_qty:
            self.cart.pop(idx)
        else:
            self.cart[idx]["quantity"] = item_qty - remove_qty

        self.update_tree()
        self.update_total()
        self._refocus()

    def _on_tree_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        column = self.tree.identify_column(event.x)
        row_id = self.tree.identify_row(event.y)
        if column != "#1" or not row_id:
            return
        idx = self.tree.index(row_id)
        if 0 <= idx < len(self.cart):
            self._remove_cart_item(idx)

    def update_tree(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for idx, item in enumerate(self.cart):
            t   = float(item["price"]) * int(item["quantity"])
            tag = "even" if idx % 2 == 0 else "odd"
            self.tree.insert("", "end", tags=(tag,), values=(
                "🗑", item["name"], item["quantity"],
                f"EGP {float(item['price']):.2f}",
                f"EGP {t:.2f}"))
        count = len(self.cart)
        self.item_count_lbl.config(
            text=f"{count} item{'s' if count != 1 else ''}")

    def update_total(self, discount=None):
        if discount is not None:
            self._discount_pct = discount
        self._tax_pct = self._load_tax_pct()
        subtotal = sum(float(i["price"]) * int(i["quantity"])
                       for i in self.cart)
        disc_amt = subtotal * (self._discount_pct / 100.0)
        taxable  = subtotal - disc_amt
        tax_amt  = taxable * (self._tax_pct / 100.0)
        final    = taxable + tax_amt

        self.subtotal_lbl.config(text=f"EGP {subtotal:.2f}")
        if disc_amt > 0:
            self.discount_lbl.config(
                text=f"- EGP {disc_amt:.2f}", fg=C["success"])
        else:
            self.discount_lbl.config(text="—", fg=C["text_light"])
        self.tax_lbl.config(text=f"EGP {tax_amt:.2f}")
        self.total_lbl.config(text=f"EGP {final:.2f}")

    def apply_promo(self):
        code   = self.promo_entry.get().strip()
        promos = load_json(os.path.join(self.data_dir, "promo_codes.json"))
        promo  = next((p for p in promos
                       if p.get("code") == code
                       and int(p.get("uses_left", 0)) > 0), None)
        if not promo:
            self.promo_status.config(
                text="✗  Invalid or expired code", fg=C["danger"])
            return
        pct = float(promo.get("discount_percentage", 0))
        self._promo_code = code
        self.update_total(discount=pct)
        self.promo_status.config(
            text=f"✓  {int(pct)}% discount applied!", fg=C["success"])

    def _ask_payment_method(self):
        """Popup — returns 'Cash', 'Visa', 'Split: EGP X cash / EGP Y visa', or None if cancelled."""
        result = [None]

        popup = tk.Toplevel(self.root)
        popup.title("Payment Method")
        popup.resizable(False, False)
        popup.grab_set()
        popup.configure(bg=C["bg_card"])

        popup.update_idletasks()
        pw, ph = 340, 260
        sx = popup.winfo_screenwidth()
        sy = popup.winfo_screenheight()
        popup.geometry(f"{pw}x{ph}+{(sx-pw)//2}+{(sy-ph)//2}")

        tk.Frame(popup, bg=C["purple"], height=3).pack(fill="x")

        tk.Label(popup, text="How is the customer paying?",
                 font=FONT_LABEL_B, bg=C["bg_card"],
                 fg=C["text_dark"]).pack(pady=(16, 12))

        # ── Cash / Visa row ───────────────────────────────────────────
        btn_row = tk.Frame(popup, bg=C["bg_card"])
        btn_row.pack()

        def pick(method):
            result[0] = method
            popup.destroy()

        cash_btn = tk.Label(btn_row, text="  CASH  ", font=FONT_BTN_LG,
                            bg=C["green"], fg="#FFFFFF", cursor="hand2",
                            relief="flat", padx=18, pady=10)
        cash_btn.pack(side="left", padx=(0, 14))
        cash_btn.bind("<Button-1>", lambda e: pick("Cash"))
        cash_btn.bind("<Enter>",    lambda e: cash_btn.config(bg=C["success"]))
        cash_btn.bind("<Leave>",    lambda e: cash_btn.config(bg=C["green"]))

        visa_btn = tk.Label(btn_row, text="  VISA  ", font=FONT_BTN_LG,
                            bg=C["purple"], fg="#FFFFFF", cursor="hand2",
                            relief="flat", padx=18, pady=10)
        visa_btn.pack(side="left")
        visa_btn.bind("<Button-1>", lambda e: pick("Visa"))
        visa_btn.bind("<Enter>",    lambda e: visa_btn.config(bg="#7C3AED"))
        visa_btn.bind("<Leave>",    lambda e: visa_btn.config(bg=C["purple"]))

        # ── Divider ───────────────────────────────────────────────────
        tk.Frame(popup, bg=C["border"], height=1).pack(fill="x", padx=20, pady=(14, 10))

        # ── Split row ─────────────────────────────────────────────────
        split_frame = tk.Frame(popup, bg=C["bg_card"])
        split_frame.pack()

        tk.Label(split_frame, text="Cash", font=FONT_LABEL_B,
                 bg=C["bg_card"], fg=C["text_mid"]).pack(side="left", padx=(0, 6))

        cash_entry = tk.Entry(split_frame, font=FONT_ENTRY, width=8,
                              bg=C["bg_input"], fg=C["text_dark"],
                              relief="flat", highlightthickness=2,
                              highlightbackground=C["border"],
                              highlightcolor=C["orange"])
        cash_entry.pack(side="left", ipady=5)
        cash_entry.insert(0, "0")

        tk.Label(split_frame, text="  +  Visa", font=FONT_LABEL_B,
                 bg=C["bg_card"], fg=C["text_mid"]).pack(side="left", padx=(8, 6))

        visa_entry = tk.Entry(split_frame, font=FONT_ENTRY, width=8,
                              bg=C["bg_input"], fg=C["text_dark"],
                              relief="flat", highlightthickness=2,
                              highlightbackground=C["border"],
                              highlightcolor=C["purple"])
        visa_entry.pack(side="left", ipady=5)
        visa_entry.insert(0, "0")

        def pick_split():
            try:
                c = float(cash_entry.get().strip() or 0)
                v = float(visa_entry.get().strip() or 0)
            except ValueError:
                cash_entry.config(highlightbackground=C["danger"])
                return
            if c <= 0 and v <= 0:
                cash_entry.config(highlightbackground=C["danger"])
                return
            result[0] = f"Split: EGP {c:.2f} cash + EGP {v:.2f} visa"
            popup.destroy()

        split_btn = tk.Label(popup, text="  SPLIT  ", font=FONT_BTN,
                             bg=C["orange"], fg="#FFFFFF", cursor="hand2",
                             relief="flat", padx=16, pady=8)
        split_btn.pack(pady=(10, 0))
        split_btn.bind("<Button-1>", lambda e: pick_split())
        split_btn.bind("<Enter>",    lambda e: split_btn.config(bg="#D97706"))
        split_btn.bind("<Leave>",    lambda e: split_btn.config(bg=C["orange"]))

        # Keyboard shortcuts
        popup.bind("c", lambda e: pick("Cash"))
        popup.bind("C", lambda e: pick("Cash"))
        popup.bind("v", lambda e: pick("Visa"))
        popup.bind("V", lambda e: pick("Visa"))
        popup.bind("<Escape>", lambda e: popup.destroy())
        cash_entry.bind("<Return>", lambda e: visa_entry.focus())
        visa_entry.bind("<Return>", lambda e: pick_split())

        cash_entry.focus()
        popup.wait_window()
        return result[0]

    def finalize_sale(self):
        if not self.cart:
            messagebox.showinfo("Empty Cart", "Add items to the cart first.")
            return

        # ── Payment method popup ───────────────────────────────────────────
        payment_method = self._ask_payment_method()
        if payment_method is None:
            return  # user cancelled

        products = load_json(self._products_path())
        for item in self.cart:
            prod = next((p for p in products
                         if str(p.get("barcode", "")) == str(item["barcode"])),
                        None)
            if prod:
                prod["quantity"] = max(
                    0, int(prod.get("quantity", 0)) - int(item["quantity"]))
        save_json(self._products_path(), products)
        self._invalidate_product_cache()

        sales    = load_json(self._sales_path())

        # Generate unique receipt ID - skip if already exists
        sale_id  = len(sales) + 1
        existing_ids = {s.get("id", 0) for s in sales}
        while sale_id in existing_ids:
            sale_id += 1

        subtotal = sum(float(i["price"]) * int(i["quantity"]) for i in self.cart)
        disc_amt = subtotal * (self._discount_pct / 100.0)
        taxable  = subtotal - disc_amt
        # ensure tax pct is current and compute tax amount
        self._tax_pct = self._load_tax_pct()
        tax_amt  = taxable * (self._tax_pct / 100.0)
        final    = taxable + tax_amt

        sale_record = {
            "id":             sale_id,
            "user":           self.user_name,
            "items":          list(self.cart),
            "subtotal":       round(subtotal, 2),
            "discount_pct":   self._discount_pct,
            "discount_amt":   round(disc_amt, 2),
            "tax_pct":        round(self._tax_pct, 2),
            "tax_amt":        round(tax_amt, 2),
            "total":          round(final, 2),
            "promo_code":     self._promo_code,
            "payment_method": payment_method,
            "date":           get_today_date(),
            "time":           datetime.now().strftime("%H:%M:%S"),
        }
        sales.append(sale_record)
        save_json(self._sales_path(), sales)

        # ── Decrement promo uses_left ──────────────────────────────────────
        if self._promo_code:
            promo_path = os.path.join(self.data_dir, "promo_codes.json")
            promos = load_json(promo_path)
            for p in promos:
                if p.get("code") == self._promo_code:
                    p["uses_left"] = max(0, int(p.get("uses_left", 0)) - 1)
                    break
            save_json(promo_path, promos)

        receipt_bytes = build_receipt(
            sale_id, sale_record,
            cashier         = self.user_name,
            discount_pct    = self._discount_pct,
            promo_code      = self._promo_code,
            payment_method  = payment_method,
        )
        self._send_to_printer(sale_id, receipt_bytes)

        self.cart          = []
        self._discount_pct = 0.0
        self._promo_code   = ""
        self.promo_entry.delete(0, tk.END)
        self.promo_status.config(text="")
        self.update_tree()
        self.update_total()
        self._refocus()

    def clear_cart(self):
        self.cart          = []
        self._discount_pct = 0.0
        self._promo_code   = ""
        self.promo_entry.delete(0, tk.END)
        self.promo_status.config(text="")
        self.update_tree()
        self.update_total()
        self._refocus()

    # ── switch user ───────────────────────────────────────────────────────────────

    def switch_user(self):
        if self.cart:
            if not messagebox.askyesno(
                "Switch User",
                "You have items in the cart.\nAre you sure you want to switch users?\nThe current cart will be cleared."):
                return
        # Destroy everything in root and relaunch login
        for widget in self.root.winfo_children():
            widget.destroy()
        # Re-import and launch login screen
        from gui.login_screen import LoginScreen
        LoginScreen(self.root, self.data_dir)

    # ── printing ──────────────────────────────────────────────────────────────

    def _send_to_printer(self, sale_id, raw_bytes):
        printer_name = None
        if WIN32_AVAILABLE:
            try:
                printer_name = win32print.GetDefaultPrinter()
            except Exception:
                pass

        if printer_name and WIN32_AVAILABLE:
            try:
                h = win32print.OpenPrinter(printer_name)
                try:
                    win32print.StartDocPrinter(h, 1, ("JustB Receipt", None, "RAW"))
                    win32print.StartPagePrinter(h)
                    win32print.WritePrinter(h, raw_bytes)
                    win32print.EndPagePrinter(h)
                    win32print.EndDocPrinter(h)
                finally:
                    win32print.ClosePrinter(h)
                messagebox.showinfo("Sale Complete",
                    "Sale saved & receipt printed!")
                return
            except Exception as e:
                messagebox.showwarning("Sale Complete",
                    f"Sale saved!\n\nPrinter could not print.\nError: {e}")
                return

        messagebox.showinfo("Sale Complete",
            "Sale saved successfully!\n\nNo printer detected.\n"
            "Connect your printer to print receipts.")

    def _save_fallback(self, sale_id, raw_bytes):
        try:
            folder = os.path.join(self.data_dir, "receipts")
            os.makedirs(folder, exist_ok=True)
            fname = f"receipt_{sale_id:06d}_{get_today_date()}.bin"
            with open(os.path.join(folder, fname), 'wb') as f:
                f.write(raw_bytes)
        except Exception:
            pass