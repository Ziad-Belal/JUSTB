"""
product_management.py  —  JustB Retail Management System
=========================================================
Redesigned to match the JustB bright luxury design system.
Dynamic features:
  • Animated stat counters in header (total products, total stock, total value)
  • Staggered row reveal when table loads
  • Low-stock pulsing badge (qty ≤ 5 highlighted in orange)
  • Live search with result count animation
  • Polished Add / Edit popups matching system palette
"""

import tkinter as tk
from tkinter import ttk, messagebox
from utils.helpers import load_json, save_json
import os
import tempfile
import subprocess

try:
    import win32api
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

# ══════════════════════════════════════════════════════════════════════════════
#  Design tokens  — identical to pos_screen.py
# ══════════════════════════════════════════════════════════════════════════════
C = {
    "bg_root":    "#F7F5FF",
    "bg_card":    "#FFFFFF",
    "bg_header":  "#FFFFFF",
    "bg_panel":   "#F0EDFF",
    "bg_row_alt": "#FAF8FF",
    "bg_input":   "#FFFFFF",
    "teal":       "#1BBFBF",
    "pink":       "#F0569A",
    "orange":     "#F97316",
    "purple":     "#8B5CF6",
    "purple_dk":  "#7C3AED",
    "green":      "#22C55E",
    "text_dark":  "#1A1035",
    "text_mid":   "#6B6B8A",
    "text_light": "#A8A8C0",
    "gold":       "#D97706",
    "border":     "#E8E4F8",
    "border_acc": "#C4B8F5",
    "success":    "#16A34A",
    "danger":     "#DC2626",
    "warning":    "#F97316",
}
BRAND_COLORS  = ["#1BBFBF", "#F0569A", "#F97316", "#8B5CF6", "#22C55E"]
LOW_STOCK_QTY = 5   # highlight threshold

FONT_BRAND   = ("Georgia",   18, "bold")
FONT_HEAD    = ("Georgia",   13, "bold")
FONT_LABEL   = ("Segoe UI",  10)
FONT_LABEL_B = ("Segoe UI",  10, "bold")
FONT_ENTRY   = ("Segoe UI",  11)
FONT_TOTAL   = ("Georgia",   20, "bold")
FONT_SMALL   = ("Segoe UI",   9)
FONT_BTN     = ("Segoe UI",  10, "bold")
FONT_SECTION = ("Segoe UI",   8, "bold")
FONT_STAT    = ("Georgia",   22, "bold")
FONT_STAT_LB = ("Segoe UI",   9)


# ── Shared UI helpers ─────────────────────────────────────────────────────────

def _btn(parent, text, command, bg, hover, fg="#FFFFFF",
         font=FONT_BTN, padx=16, pady=8):
    b = tk.Label(parent, text=text, font=font,
                 bg=bg, fg=fg, cursor="hand2",
                 relief="flat", padx=padx, pady=pady)
    b.bind("<Button-1>", lambda e: command())
    b.bind("<Enter>",    lambda e: b.config(bg=hover))
    b.bind("<Leave>",    lambda e: b.config(bg=bg))
    return b


def _entry(parent, width=24, font=FONT_ENTRY, show=""):
    return tk.Entry(
        parent, font=font, width=width, show=show,
        bg=C["bg_input"], fg=C["text_dark"],
        insertbackground=C["purple"],
        relief="flat",
        highlightthickness=2,
        highlightbackground=C["border"],
        highlightcolor=C["purple"],
    )


def _field_row(parent, row, label, widget, col_offset=0):
    tk.Label(parent, text=label, font=FONT_LABEL_B,
             bg=C["bg_card"], fg=C["text_mid"]).grid(
                 row=row, column=col_offset, sticky="w",
                 pady=6, padx=(0, 16))
    widget.grid(row=row, column=col_offset + 1,
                sticky="ew", pady=6, ipady=7)


# ══════════════════════════════════════════════════════════════════════════════
#  Add / Edit popup  — shared between add_product and edit_product
# ══════════════════════════════════════════════════════════════════════════════

class _ProductPopup(tk.Toplevel):
    def __init__(self, master, title, on_save,
                 barcode="", name="", price="", qty="",
                 lock_barcode=False):
        super().__init__(master)
        self.on_save = on_save
        self.title(title)
        self.resizable(False, False)
        self.configure(bg=C["bg_root"])
        self.grab_set()

        pw, ph = 400, 340
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{pw}x{ph}+{(sw-pw)//2}+{(sh-ph)//2}")

        # Accent bar
        accent_col = C["teal"] if not lock_barcode else C["orange"]
        tk.Frame(self, bg=accent_col, height=4).pack(fill="x")

        # Title row
        hdr = tk.Frame(self, bg=C["bg_header"],
                       highlightthickness=1,
                       highlightbackground=C["border"],
                       padx=20, pady=14)
        hdr.pack(fill="x")
        dots = tk.Frame(hdr, bg=C["bg_header"])
        dots.pack(side="left")
        for col in BRAND_COLORS:
            tk.Label(dots, text="●", font=("Segoe UI", 7),
                     bg=C["bg_header"], fg=col).pack(side="left", padx=1)
        tk.Label(hdr, text=f"  {title}",
                 font=FONT_HEAD, bg=C["bg_header"],
                 fg=C["text_dark"]).pack(side="left")

        # Form card
        card = tk.Frame(self, bg=C["bg_card"],
                        highlightthickness=1,
                        highlightbackground=C["border"],
                        padx=28, pady=20)
        card.pack(fill="both", expand=True, padx=16, pady=14)
        card.columnconfigure(1, weight=1)

        self.barcode_e = _entry(card, width=28)
        self.name_e    = _entry(card, width=28)
        self.price_e   = _entry(card, width=28)
        self.qty_e     = _entry(card, width=28)

        _field_row(card, 0, "Barcode",  self.barcode_e)
        _field_row(card, 1, "Name",     self.name_e)
        _field_row(card, 2, "Price",    self.price_e)
        _field_row(card, 3, "Quantity", self.qty_e)

        self.barcode_e.insert(0, barcode)
        self.name_e.insert(0, name)
        self.price_e.insert(0, price)
        self.qty_e.insert(0, qty)

        if lock_barcode:
            self.barcode_e.config(state="disabled",
                                  disabledbackground=C["bg_panel"],
                                  disabledforeground=C["text_mid"])

        # Status
        self.status = tk.Label(card, text="", font=FONT_SMALL,
                               fg=C["danger"], bg=C["bg_card"])
        self.status.grid(row=4, column=0, columnspan=2,
                         sticky="w", pady=(4, 0))

        # Buttons
        btn_row = tk.Frame(self, bg=C["bg_root"])
        btn_row.pack(fill="x", padx=16, pady=(0, 14))

        btn_col = accent_col
        btn_hov = C["purple_dk"] if accent_col == C["teal"] else "#E05F00"
        _btn(btn_row, "Save", self._save,
             accent_col, btn_hov, padx=24, pady=10).pack(side="right", padx=(8, 0))
        _btn(btn_row, "Cancel", self.destroy,
             C["text_light"], C["text_mid"],
             fg=C["text_dark"], padx=16, pady=10).pack(side="right")

        # Focus
        (self.name_e if lock_barcode else self.barcode_e).focus()
        self.bind("<Return>", lambda e: self._save())
        self.bind("<Escape>", lambda e: self.destroy())

    def _save(self):
        barcode  = self.barcode_e.get().strip()
        name     = self.name_e.get().strip()
        price_s  = self.price_e.get().strip()
        qty_s    = self.qty_e.get().strip()

        if not barcode:
            self.status.config(text="Barcode is required."); return
        if not name:
            self.status.config(text="Name is required."); return
        try:
            price = float(price_s)
            assert price >= 0
        except Exception:
            self.status.config(text="Price must be a non-negative number."); return
        try:
            qty = int(qty_s)
            assert qty >= 0
        except Exception:
            self.status.config(text="Quantity must be a non-negative integer."); return

        self.on_save(barcode, name, price, qty)
        self.destroy()


# ══════════════════════════════════════════════════════════════════════════════
#  ProductManagementScreen
# ══════════════════════════════════════════════════════════════════════════════

class ProductManagementScreen:
    def __init__(self, root, data_dir, frame_parent=None, cashier_mode=False):
        self.root         = root
        self.data_dir     = data_dir
        self.cashier_mode = cashier_mode
        self.all_products = []
        self._pulse_jobs  = {}   # iid → after-job id for low-stock pulse

        self.frame = tk.Frame(frame_parent or root, bg=C["bg_root"])
        self.frame.pack(fill="both", expand=True)

        self._build_ui()
        self.load_products()

    # ── path helper ───────────────────────────────────────────────────────────
    def _products_path(self):
        return os.path.join(self.data_dir, "products.json")

    # ══════════════════════════════════════════════════════════════════════════
    #  UI build
    # ══════════════════════════════════════════════════════════════════════════

    def _build_ui(self):

        # ── Header bar ────────────────────────────────────────────────────────
        hdr = tk.Frame(self.frame, bg=C["bg_header"],
                       highlightthickness=1,
                       highlightbackground=C["border"])
        hdr.pack(fill="x")

        dots = tk.Frame(hdr, bg=C["bg_header"])
        dots.pack(side="left", padx=(16, 4), pady=10)
        for col in BRAND_COLORS:
            tk.Label(dots, text="●", font=("Segoe UI", 9),
                     bg=C["bg_header"], fg=col).pack(side="left", padx=1)
        tk.Label(hdr, text="Product Management",
                 font=FONT_HEAD, bg=C["bg_header"],
                 fg=C["text_dark"]).pack(side="left", padx=(6, 0), pady=10)

        # ── Animated stat cards ───────────────────────────────────────────────
        stats_bar = tk.Frame(self.frame, bg=C["bg_root"])
        stats_bar.pack(fill="x", padx=14, pady=(10, 0))

        self._stat_total   = self._stat_card(stats_bar, "TOTAL PRODUCTS", "0", C["purple"],  0)
        self._stat_stock   = self._stat_card(stats_bar, "TOTAL STOCK",    "0", C["teal"],    1)
        self._stat_value   = self._stat_card(stats_bar, "INVENTORY VALUE", "EGP 0", C["orange"], 2)
        self._stat_lowstock= self._stat_card(stats_bar, "LOW STOCK (≤5)",  "0", C["pink"],   3)

        for i in range(4):
            stats_bar.columnconfigure(i, weight=1)

        # ── Search bar card ───────────────────────────────────────────────────
        sc = tk.Frame(self.frame, bg=C["bg_card"],
                      highlightthickness=1,
                      highlightbackground=C["border"],
                      padx=16, pady=12)
        sc.pack(fill="x", padx=14, pady=(10, 0))

        tk.Frame(sc, bg=C["teal"], height=3).pack(fill="x", pady=(0, 10))

        row = tk.Frame(sc, bg=C["bg_card"])
        row.pack(fill="x")
        row.columnconfigure(1, weight=1)

        tk.Label(row, text="🔍", font=("Segoe UI", 14),
                 bg=C["bg_card"], fg=C["teal"]).grid(row=0, column=0, padx=(0, 8))

        self.search_entry = _entry(row, width=36)
        self.search_entry.grid(row=0, column=1, sticky="ew", ipady=7)
        self.search_entry.bind("<KeyRelease>", lambda e: self.search_products())

        # Filter dropdown
        tk.Label(row, text="by", font=FONT_SMALL,
                 bg=C["bg_card"], fg=C["text_light"]).grid(
                     row=0, column=2, padx=(10, 6))

        style = ttk.Style()
        style.configure("JB.TCombobox", fieldbackground=C["bg_input"],
                        background=C["bg_panel"])
        self.search_filter = ttk.Combobox(
            row,
            values=["All", "Barcode", "Name", "Price", "Quantity"],
            state="readonly", width=11,
            font=FONT_LABEL,
        )
        self.search_filter.set("All")
        self.search_filter.grid(row=0, column=3, padx=(0, 10), ipady=5)
        self.search_filter.bind("<<ComboboxSelected>>", lambda e: self.search_products())

        _btn(row, "Clear", self.clear_search,
             C["text_light"], C["text_mid"],
             fg=C["text_dark"], padx=14, pady=6).grid(row=0, column=4)

        self.results_lbl = tk.Label(sc, text="",
                                     font=FONT_SMALL, bg=C["bg_card"],
                                     fg=C["purple"], anchor="w")
        self.results_lbl.pack(fill="x", pady=(8, 0))

        # ── Action buttons ────────────────────────────────────────────────────
        acts = tk.Frame(self.frame, bg=C["bg_root"])
        acts.pack(fill="x", padx=14, pady=8)

        _btn(acts, "＋  Add Product",
             self.add_product_popup,
             C["teal"], "#159F9F").pack(side="left", padx=(0, 8))

        if not self.cashier_mode:
            _btn(acts, "✎  Edit",
                 self.edit_product_popup,
                 C["orange"], "#E05F00").pack(side="left", padx=(0, 8))
            _btn(acts, "🗑  Delete",
                 self.delete_product,
                 C["danger"], "#B91C1C").pack(side="left", padx=(0, 8))

        _btn(acts, "🖨  Print",
             self.print_product,
             C["purple"], C["purple_dk"]).pack(side="left", padx=(0, 8))

        _btn(acts, "⟳  Refresh",
             self.load_products,
             C["bg_panel"], C["border_acc"],
             fg=C["text_mid"]).pack(side="left")

        # Low-stock legend
        legend = tk.Frame(acts, bg=C["bg_root"])
        legend.pack(side="right")
        tk.Label(legend, text="●", font=("Segoe UI", 10),
                 bg=C["bg_root"], fg=C["warning"]).pack(side="left")
        tk.Label(legend, text=" Low stock (qty ≤ 5)",
                 font=FONT_SMALL, bg=C["bg_root"],
                 fg=C["text_mid"]).pack(side="left")

        # ── Treeview card ─────────────────────────────────────────────────────
        tree_card = tk.Frame(self.frame, bg=C["bg_card"],
                             highlightthickness=1,
                             highlightbackground=C["border"])
        tree_card.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        tree_card.rowconfigure(1, weight=1)
        tree_card.columnconfigure(0, weight=1)

        # Card sub-header
        ch = tk.Frame(tree_card, bg=C["bg_panel"], padx=14, pady=10)
        ch.grid(row=0, column=0, columnspan=2, sticky="ew")

        dot_f = tk.Frame(ch, bg=C["bg_panel"])
        dot_f.pack(side="left")
        for col in BRAND_COLORS:
            tk.Label(dot_f, text="●", font=("Segoe UI", 8),
                     bg=C["bg_panel"], fg=col).pack(side="left", padx=1)
        tk.Label(ch, text="  INVENTORY",
                 font=FONT_SECTION, bg=C["bg_panel"],
                 fg=C["text_mid"]).pack(side="left")
        self._item_count_lbl = tk.Label(ch, text="0 items",
                                         font=FONT_SMALL,
                                         bg=C["bg_panel"], fg=C["purple"])
        self._item_count_lbl.pack(side="right")

        # Treeview style
        ts = ttk.Style()
        ts.configure("PM.Treeview",
                     background=C["bg_card"],
                     foreground=C["text_dark"],
                     fieldbackground=C["bg_card"],
                     rowheight=38,
                     font=("Segoe UI", 10),
                     borderwidth=0, relief="flat")
        ts.configure("PM.Treeview.Heading",
                     background=C["bg_panel"],
                     foreground=C["text_mid"],
                     font=("Segoe UI", 9, "bold"),
                     relief="flat", borderwidth=0)
        ts.map("PM.Treeview",
               background=[("selected", C["bg_panel"])],
               foreground=[("selected", C["purple"])])
        ts.layout("PM.Treeview",
                  [('Treeview.treearea', {'sticky': 'nswe'})])

        cols = ("Barcode", "Name", "Price", "Qty", "Status")
        self.tree = ttk.Treeview(tree_card, columns=cols,
                                  show="headings", selectmode="extended",
                                  style="PM.Treeview")
        cw = {"Barcode": 120, "Name": 300, "Price": 100, "Qty": 80, "Status": 100}
        for col in cols:
            self.tree.heading(col, text=col,
                              command=lambda c=col: self._sort_by(c))
            self.tree.column(col, anchor="center",
                              width=cw[col], minwidth=60)

        self.tree.tag_configure("even",     background=C["bg_card"])
        self.tree.tag_configure("odd",      background=C["bg_row_alt"])
        self.tree.tag_configure("low",      foreground=C["warning"])
        self.tree.tag_configure("low_odd",  background=C["bg_row_alt"], foreground=C["warning"])

        vsb = ttk.Scrollbar(tree_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=1, column=0, sticky="nsew")
        vsb.grid(row=1, column=1, sticky="ns")

        self.tree.bind("<Double-1>",          lambda e: self.edit_product_popup())
        self.tree.bind("<<TreeviewSelect>>",  lambda e: None)

        # Footer
        tk.Label(self.frame,
                 text="justb-eg.com  ·  Stationery & Gifts",
                 font=("Segoe UI", 8),
                 bg=C["bg_root"], fg=C["text_light"]).pack(side="bottom", pady=4)

    # ── Stat card builder ─────────────────────────────────────────────────────

    def _stat_card(self, parent, label, value, accent, col):
        card = tk.Frame(parent, bg=C["bg_card"],
                        highlightthickness=1,
                        highlightbackground=C["border"],
                        padx=16, pady=14)
        card.grid(row=0, column=col, sticky="ew",
                  padx=(0 if col == 0 else 8, 0), pady=0)

        tk.Frame(card, bg=accent, height=3).pack(fill="x", pady=(0, 8))
        tk.Label(card, text=label, font=FONT_STAT_LB,
                 bg=C["bg_card"], fg=C["text_light"]).pack(anchor="w")
        val_lbl = tk.Label(card, text=value, font=FONT_STAT,
                           bg=C["bg_card"], fg=accent)
        val_lbl.pack(anchor="w")
        return val_lbl

    # ── Animated stat counter ─────────────────────────────────────────────────

    def _animate_counter(self, label, target, prefix="", steps=20):
        try:
            current = int(float(label.cget("text").replace(prefix, "").replace(",", "").strip() or 0))
        except Exception:
            current = 0
        delta = target - current
        if delta == 0:
            return

        def _step(i=0):
            if i > steps:
                label.config(text=f"{prefix}{target:,}")
                return
            val = int(current + delta * (i / steps))
            label.config(text=f"{prefix}{val:,}")
            label.after(16, lambda: _step(i + 1))

        _step()

    def _animate_float(self, label, target, prefix="EGP ", steps=20):
        try:
            raw = label.cget("text").replace(prefix, "").replace(",", "").strip() or "0"
            current = float(raw)
        except Exception:
            current = 0.0
        delta = target - current

        def _step(i=0):
            if i > steps:
                label.config(text=f"{prefix}{target:,.2f}")
                return
            val = current + delta * (i / steps)
            label.config(text=f"{prefix}{val:,.2f}")
            label.after(16, lambda: _step(i + 1))

        _step()

    # ── Treeview sort ─────────────────────────────────────────────────────────

    _sort_state = {}

    def _sort_by(self, col):
        reverse = self._sort_state.get(col, False)
        key_map = {
            "Barcode": lambda p: str(p.get("barcode", "")),
            "Name":    lambda p: p.get("name", "").lower(),
            "Price":   lambda p: float(p.get("price", 0)),
            "Qty":     lambda p: int(p.get("quantity", 0)),
        }
        key = key_map.get(col, lambda p: "")
        self.all_products.sort(key=key, reverse=reverse)
        self._sort_state[col] = not reverse
        self.display_products(self.all_products)

    # ══════════════════════════════════════════════════════════════════════════
    #  Data
    # ══════════════════════════════════════════════════════════════════════════

    def load_products(self):
        self.all_products = load_json(self._products_path())
        self.display_products(self.all_products)

    def display_products(self, products):
        for i in self.tree.get_children():
            self.tree.delete(i)

        low_count = 0
        for idx, p in enumerate(products):
            barcode_str = str(p["barcode"])
            qty = int(p.get("quantity", 0))
            is_low = qty <= LOW_STOCK_QTY
            if is_low:
                low_count += 1

            status = "⚠ Low Stock" if is_low else "✓ OK"
            tag_base = "odd" if idx % 2 else "even"
            tag = ("low_odd" if (is_low and idx % 2) else
                   "low"     if is_low else tag_base)

            iid = "bc_" + barcode_str
            self.tree.insert("", "end", iid=iid, tags=(tag,),
                             values=(barcode_str, p["name"],
                                     f"EGP {float(p['price']):.2f}",
                                     qty, status))

        total   = len(self.all_products)
        shown   = len(products)
        stock   = sum(int(p.get("quantity", 0)) for p in self.all_products)
        value   = sum(float(p.get("price", 0)) * int(p.get("quantity", 0))
                      for p in self.all_products)
        low_all = sum(1 for p in self.all_products
                      if int(p.get("quantity", 0)) <= LOW_STOCK_QTY)

        # Animate stat counters
        self._animate_counter(self._stat_total,    total)
        self._animate_counter(self._stat_stock,    stock)
        self._animate_float  (self._stat_value,    value)
        self._animate_counter(self._stat_lowstock, low_all)

        # Results label
        if shown == total:
            self.results_lbl.config(text=f"Showing all {total} product(s)")
        else:
            self.results_lbl.config(
                text=f"Showing {shown} of {total} product(s)")

        self._item_count_lbl.config(
            text=f"{shown} item{'s' if shown != 1 else ''}")

    # ── Search ────────────────────────────────────────────────────────────────

    def search_products(self):
        query    = self.search_entry.get().strip().lower()
        field    = self.search_filter.get()
        if not query:
            self.display_products(self.all_products)
            return

        filtered = []
        for p in self.all_products:
            bc    = str(p.get("barcode", "")).lower()
            name  = str(p.get("name",    "")).lower()
            price = str(p.get("price",   "")).lower()
            qty   = str(p.get("quantity", 0)).lower()
            if (field == "All"      and (query in bc or query in name or query in price or query in qty) or
                field == "Barcode"  and query in bc   or
                field == "Name"     and query in name or
                field == "Price"    and query in price or
                field == "Quantity" and query in qty):
                filtered.append(p)

        self.display_products(filtered)

    def clear_search(self):
        self.search_entry.delete(0, tk.END)
        self.search_filter.set("All")
        self.display_products(self.all_products)

    # ══════════════════════════════════════════════════════════════════════════
    #  CRUD
    # ══════════════════════════════════════════════════════════════════════════

    def add_product_popup(self):
        def _save(barcode, name, price, qty):
            products = load_json(self._products_path())
            if any(str(p["barcode"]) == str(barcode) for p in products):
                messagebox.showerror("Duplicate",
                    "A product with this barcode already exists.\nUse Edit to modify it.")
                return
            products.append({"barcode": barcode, "name": name,
                              "price": price, "quantity": qty})
            save_json(self._products_path(), products)
            self.load_products()

        _ProductPopup(self.root, "Add Product", _save)

    def edit_product_popup(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Select Product", "Please select a product to edit.")
            return
        if len(selected) > 1:
            messagebox.showinfo("Select Product", "Please select only one product to edit.")
            return

        iid = selected[0]
        old_barcode = iid[3:] if iid.startswith("bc_") else iid
        vals = self.tree.item(iid)["values"]
        old_name  = vals[1]
        old_price = str(vals[2]).replace("EGP ", "")
        old_qty   = vals[3]

        def _save(barcode, name, price, qty):
            products = load_json(self._products_path())
            if str(barcode) != str(old_barcode):
                if any(str(p["barcode"]) == str(barcode) for p in products):
                    messagebox.showerror("Duplicate", "Another product already has this barcode.")
                    return
            for p in products:
                if str(p["barcode"]) == str(old_barcode):
                    p.update({"barcode": barcode, "name": name,
                               "price": price, "quantity": qty})
                    break
            save_json(self._products_path(), products)
            self.load_products()

        _ProductPopup(self.root, "Edit Product", _save,
                      barcode=old_barcode, name=old_name,
                      price=old_price, qty=str(old_qty),
                      lock_barcode=True)

    def delete_product(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Select Product", "Select product(s) to delete.")
            return
        n = len(selected)
        if not messagebox.askyesno("Confirm Delete",
                                   f"Delete {n} product{'s' if n > 1 else ''}? This cannot be undone."):
            return
        products = load_json(self._products_path())
        to_remove = {(iid[3:] if iid.startswith("bc_") else iid) for iid in selected}
        products = [p for p in products if str(p.get("barcode", "")) not in to_remove]
        save_json(self._products_path(), products)
        self.load_products()

    def print_product(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Select Product", "Select a product to print.")
            return
        try:
            for sel in selected:
                iid = sel
                barcode = iid[3:] if iid.startswith("bc_") else iid
                vals = self.tree.item(sel)["values"]
                if not vals:
                    continue
                text = (f"Product\n-------\n"
                        f"Name:     {vals[1]}\n"
                        f"Barcode:  {barcode}\n"
                        f"Price:    {vals[2]}\n"
                        f"Quantity: {vals[3]}\n")
                tmp = tempfile.NamedTemporaryFile(
                    delete=False, suffix=".txt", mode="w", encoding="utf-8")
                tmp.write(text)
                tmp.close()
                if WIN32_AVAILABLE:
                    import win32api
                    win32api.ShellExecute(0, "print", tmp.name, None, ".", 0)
                else:
                    try:
                        subprocess.run(["notepad", "/p", tmp.name], check=False)
                    except Exception:
                        messagebox.showerror("Print Error",
                            "Could not print. Install pywin32 for automatic printing.")
                        return
            messagebox.showinfo("Printed", "Product info sent to printer.")
        except Exception as e:
            messagebox.showerror("Print Error", str(e))