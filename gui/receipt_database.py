# gui/receipt_database.py
"""
Receipt Database Screen
- Search receipts by number, date, cashier
- Barcode scanner support: scanning a receipt barcode jumps to that receipt
- Admin can add or delete receipts
- Click any receipt to view full detail
"""

import tkinter as tk
from tkinter import ttk, messagebox
from utils.helpers import load_json, save_json, get_today_date
import os

# ── Design tokens (mirrors pos_screen.py) ─────────────────────────────────────
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
    "green":      "#22C55E",
    "text_dark":  "#1A1035",
    "text_mid":   "#6B6B8A",
    "text_light": "#A8A8C0",
    "gold":       "#D97706",
    "border":     "#E8E4F8",
    "border_acc": "#C4B8F5",
    "success":    "#16A34A",
    "danger":     "#DC2626",
}
BRAND_COLORS = ["#1BBFBF", "#F0569A", "#F97316", "#8B5CF6", "#22C55E"]

FONT_HEAD    = ("Georgia",  13, "bold")
FONT_LABEL   = ("Segoe UI", 10)
FONT_LABEL_B = ("Segoe UI", 10, "bold")
FONT_ENTRY   = ("Segoe UI", 11)
FONT_BTN     = ("Segoe UI", 10, "bold")
FONT_SMALL   = ("Segoe UI",  9)
FONT_SECTION = ("Segoe UI",  8, "bold")
FONT_TOTAL   = ("Georgia",  16, "bold")


def _btn(parent, text, command, bg, hover, fg="#FFFFFF",
         font=FONT_BTN, padx=16, pady=8):
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


# ──────────────────────────────────────────────────────────────────────────────

class ReceiptDetailWindow(tk.Toplevel):
    """Popup showing the full details of a single receipt."""

    def __init__(self, master, receipt, admin=False, on_delete=None):
        super().__init__(master)
        self.receipt   = receipt
        self.admin     = admin
        self.on_delete = on_delete

        rid = receipt.get("id", "?")
        self.title(f"Receipt #{rid:06d}" if isinstance(rid, int) else f"Receipt #{rid}")
        self.geometry("480x560")
        self.resizable(False, False)
        self.configure(bg=C["bg_root"])
        self.grab_set()

        self._build()

    def _build(self):
        r = self.receipt

        # Header bar
        hdr = tk.Frame(self, bg=C["purple"], padx=20, pady=14)
        hdr.pack(fill="x")
        rid = r.get("id", "?")
        rid_str = f"{rid:06d}" if isinstance(rid, int) else str(rid)
        tk.Label(hdr, text=f"Receipt  #  {rid_str}",
                 font=FONT_HEAD, bg=C["purple"], fg="#FFFFFF").pack(side="left")

        # Meta info
        meta = tk.Frame(self, bg=C["bg_card"],
                        highlightthickness=1,
                        highlightbackground=C["border"],
                        padx=20, pady=14)
        meta.pack(fill="x", padx=14, pady=(14, 0))

        fields = [
            ("Date",    r.get("date", "—")),
            ("Cashier", r.get("user", "—")),
            ("Promo",   r.get("promo_code", "—") or "—"),
        ]
        for i, (label, val) in enumerate(fields):
            tk.Label(meta, text=label + ":",
                     font=FONT_LABEL_B, bg=C["bg_card"],
                     fg=C["text_mid"]).grid(row=i, column=0, sticky="w", pady=3)
            tk.Label(meta, text=val,
                     font=FONT_LABEL, bg=C["bg_card"],
                     fg=C["text_dark"]).grid(row=i, column=1, sticky="w", pady=3, padx=(16, 0))

        # Items table
        items_frame = tk.Frame(self, bg=C["bg_card"],
                               highlightthickness=1,
                               highlightbackground=C["border"])
        items_frame.pack(fill="both", expand=True, padx=14, pady=10)

        # Sub-header
        sh = tk.Frame(items_frame, bg=C["bg_panel"], padx=14, pady=8)
        sh.pack(fill="x")
        tk.Label(sh, text="ITEMS", font=FONT_SECTION,
                 bg=C["bg_panel"], fg=C["text_mid"]).pack(side="left")

        cols = ("Item", "Qty", "Unit Price", "Total")
        tree = ttk.Treeview(items_frame, columns=cols, show="headings",
                             height=8)
        cw = {"Item": 180, "Qty": 50, "Unit Price": 90, "Total": 90}
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, anchor="center", width=cw[col])
        tree.pack(fill="both", expand=True, padx=8, pady=8)

        for item in r.get("items", []):
            qty   = int(item.get("quantity", 1))
            price = float(item.get("price", 0))
            tree.insert("", "end", values=(
                item.get("name", "?"),
                qty,
                f"EGP {price:.2f}",
                f"EGP {qty * price:.2f}",
            ))

        # Totals footer
        tot = tk.Frame(self, bg=C["bg_card"],
                       highlightthickness=1,
                       highlightbackground=C["border"],
                       padx=20, pady=12)
        tot.pack(fill="x", padx=14)
        tot.columnconfigure(1, weight=1)

        tk.Label(tot, text="Subtotal:", font=FONT_LABEL,
                 bg=C["bg_card"], fg=C["text_mid"]).grid(row=0, column=0, sticky="w")
        tk.Label(tot, text=f"EGP {r.get('subtotal', r.get('total', 0)):.2f}",
                 font=FONT_LABEL_B, bg=C["bg_card"],
                 fg=C["text_dark"]).grid(row=0, column=1, sticky="e")

        disc = r.get("discount_amt", 0)
        if disc:
            tk.Label(tot, text=f"Discount ({r.get('discount_pct', 0)}%):",
                     font=FONT_LABEL, bg=C["bg_card"],
                     fg=C["text_mid"]).grid(row=1, column=0, sticky="w")
            tk.Label(tot, text=f"- EGP {disc:.2f}",
                     font=FONT_LABEL_B, bg=C["bg_card"],
                     fg=C["success"]).grid(row=1, column=1, sticky="e")

        tk.Frame(tot, bg=C["border"], height=1).grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=8)
        tk.Label(tot, text="TOTAL:", font=FONT_LABEL_B,
                 bg=C["bg_card"], fg=C["text_mid"]).grid(row=3, column=0, sticky="w")
        tk.Label(tot, text=f"EGP {r.get('total', 0):.2f}",
                 font=FONT_TOTAL, bg=C["bg_card"],
                 fg=C["gold"]).grid(row=3, column=1, sticky="e")

        # Buttons
        btn_row = tk.Frame(self, bg=C["bg_root"])
        btn_row.pack(fill="x", padx=14, pady=12)

        if self.admin and self.on_delete:
            _btn(btn_row, "🗑  Delete Receipt",
                 self._delete, C["danger"], "#B91C1C",
                 padx=14, pady=8).pack(side="left")

        _btn(btn_row, "Close", self.destroy,
             C["purple"], "#7C3AED",
             padx=14, pady=8).pack(side="right")

    def _delete(self):
        if messagebox.askyesno("Delete Receipt",
                               f"Permanently delete Receipt #{self.receipt.get('id')}?\nThis cannot be undone.",
                               parent=self):
            if self.on_delete:
                self.on_delete(self.receipt.get("id"))
            self.destroy()


# ──────────────────────────────────────────────────────────────────────────────

class ReceiptDatabaseScreen:
    """
    Main receipt database UI.
    admin=True  → full CRUD (delete, manual add)
    admin=False → read-only search & view
    """

    def __init__(self, root, data_dir, frame_parent=None, admin=False):
        self.root      = root
        self.data_dir  = data_dir
        self.admin     = admin
        self._all      = []          # all loaded receipts
        self._filtered = []          # currently shown

        self.frame = tk.Frame(frame_parent or root, bg=C["bg_root"])
        self.frame.pack(fill="both", expand=True)

        self._build_ui()
        self.load_receipts()

    # ─────────────────────────────────────────────────────────────────────────
    def _sales_path(self):
        return os.path.join(self.data_dir, "sales.json")

    def load_receipts(self):
        self._all = load_json(self._sales_path())
        self._filtered = list(self._all)
        self._refresh_tree()

    # ─────────────────────────────────────────────────────────────────────────
    def _build_ui(self):

        # ── Top bar ──────────────────────────────────────────────────────────
        top = tk.Frame(self.frame, bg=C["bg_header"],
                       highlightthickness=1,
                       highlightbackground=C["border"])
        top.pack(fill="x")

        # Brand dots
        dots = tk.Frame(top, bg=C["bg_header"])
        dots.pack(side="left", padx=(16, 4), pady=10)
        for col in BRAND_COLORS:
            tk.Label(dots, text="●", font=("Segoe UI", 9),
                     bg=C["bg_header"], fg=col).pack(side="left", padx=1)

        tk.Label(top, text="Receipt Database",
                 font=FONT_HEAD, bg=C["bg_header"],
                 fg=C["text_dark"]).pack(side="left", padx=(6, 0), pady=10)

        self.count_lbl = tk.Label(top, text="",
                                   font=FONT_SMALL,
                                   bg=C["bg_header"], fg=C["purple"])
        self.count_lbl.pack(side="right", padx=20, pady=10)

        # ── Search / scanner bar ─────────────────────────────────────────────
        search_card = tk.Frame(self.frame, bg=C["bg_card"],
                               highlightthickness=1,
                               highlightbackground=C["border"],
                               padx=16, pady=12)
        search_card.pack(fill="x", padx=14, pady=(12, 0))

        # coloured accent
        tk.Frame(search_card, bg=C["teal"], height=3).grid(
            row=0, column=0, columnspan=6, sticky="ew", pady=(0, 10))

        tk.Label(search_card, text="🔍  SEARCH  /  SCAN RECEIPT BARCODE",
                 font=FONT_SECTION, bg=C["bg_card"],
                 fg=C["text_light"]).grid(row=1, column=0, columnspan=6,
                                           sticky="w", pady=(0, 6))

        # Receipt # search
        tk.Label(search_card, text="Receipt #",
                 font=FONT_LABEL_B, bg=C["bg_card"],
                 fg=C["text_mid"]).grid(row=2, column=0, sticky="w", padx=(0, 6))
        self.num_entry = _entry(search_card, width=12)
        self.num_entry.grid(row=2, column=1, ipady=5, padx=(0, 16))
        # Bind Enter so scanner "sends Enter" after barcode → auto-search
        self.num_entry.bind("<Return>", lambda e: self._scanner_lookup())

        # Date search
        tk.Label(search_card, text="Date (YYYY-MM-DD)",
                 font=FONT_LABEL_B, bg=C["bg_card"],
                 fg=C["text_mid"]).grid(row=2, column=2, sticky="w", padx=(0, 6))
        self.date_entry = _entry(search_card, width=14)
        self.date_entry.grid(row=2, column=3, ipady=5, padx=(0, 16))
        self.date_entry.bind("<Return>", lambda e: self.search())

        # Cashier search
        tk.Label(search_card, text="Cashier",
                 font=FONT_LABEL_B, bg=C["bg_card"],
                 fg=C["text_mid"]).grid(row=2, column=4, sticky="w", padx=(0, 6))
        self.cashier_entry = _entry(search_card, width=12)
        self.cashier_entry.grid(row=2, column=5, ipady=5, padx=(0, 16))
        self.cashier_entry.bind("<Return>", lambda e: self.search())

        # Buttons row
        btn_row = tk.Frame(self.frame, bg=C["bg_root"])
        btn_row.pack(fill="x", padx=14, pady=8)

        _btn(btn_row, "🔍  Search", self.search,
             C["purple"], "#7C3AED").pack(side="left", padx=(0, 8))
        _btn(btn_row, "↺  Reset", self.reset_search,
             C["text_mid"], "#4B4B6A").pack(side="left", padx=(0, 8))
        _btn(btn_row, "⟳  Refresh", self.load_receipts,
             C["teal"], "#159F9F").pack(side="left")

        if self.admin:
            _btn(btn_row, "🗑  Delete Selected", self._delete_selected,
                 C["danger"], "#B91C1C").pack(side="right")

        # ── Receipts treeview ────────────────────────────────────────────────
        tree_frame = tk.Frame(self.frame, bg=C["bg_card"],
                              highlightthickness=1,
                              highlightbackground=C["border"])
        tree_frame.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        tree_frame.rowconfigure(1, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        # Sub-header
        sh = tk.Frame(tree_frame, bg=C["bg_panel"], padx=14, pady=10)
        sh.grid(row=0, column=0, columnspan=2, sticky="ew")
        tk.Label(sh, text="ALL RECEIPTS — double-click to view detail",
                 font=FONT_SECTION, bg=C["bg_panel"],
                 fg=C["text_mid"]).pack(side="left")

        # Style
        style = ttk.Style()
        style.configure("RDB.Treeview",
                         background=C["bg_card"],
                         foreground=C["text_dark"],
                         fieldbackground=C["bg_card"],
                         rowheight=36,
                         font=("Segoe UI", 10),
                         borderwidth=0, relief="flat")
        style.configure("RDB.Treeview.Heading",
                         background=C["bg_panel"],
                         foreground=C["text_mid"],
                         font=("Segoe UI", 9, "bold"),
                         relief="flat", borderwidth=0)
        style.map("RDB.Treeview",
                  background=[("selected", C["bg_panel"])],
                  foreground=[("selected", C["purple"])])
        style.layout("RDB.Treeview",
                     [('Treeview.treearea', {'sticky': 'nswe'})])

        cols = ("Receipt #", "Date", "Cashier", "Items", "Subtotal", "Discount", "Total", "Promo")
        self.tree = ttk.Treeview(tree_frame, columns=cols,
                                  show="headings", selectmode="browse",
                                  style="RDB.Treeview")
        cw = {"Receipt #": 90, "Date": 110, "Cashier": 110,
              "Items": 50, "Subtotal": 100, "Discount": 90, "Total": 100, "Promo": 100}
        for col in cols:
            self.tree.heading(col, text=col,
                              command=lambda c=col: self._sort_by(c))
            self.tree.column(col, anchor="center",
                              width=cw[col], minwidth=60)

        self.tree.tag_configure("even", background=C["bg_card"])
        self.tree.tag_configure("odd",  background=C["bg_row_alt"])

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",
                             command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=1, column=0, sticky="nsew")
        vsb.grid(row=1, column=1, sticky="ns")

        self.tree.bind("<Double-1>", lambda e: self._open_detail())
        self.tree.bind("<Return>",   lambda e: self._open_detail())

        # ── Status bar ───────────────────────────────────────────────────────
        self.status_lbl = tk.Label(self.frame, text="",
                                    font=FONT_SMALL,
                                    bg=C["bg_root"], fg=C["text_light"],
                                    anchor="w")
        self.status_lbl.pack(fill="x", padx=16, pady=(0, 6))

    # ─────────────────────────────────────────────────────────────────────────
    def _refresh_tree(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        for idx, r in enumerate(self._filtered):
            rid  = r.get("id", "?")
            rid_str = f"{rid:06d}" if isinstance(rid, int) else str(rid)
            tag  = "even" if idx % 2 == 0 else "odd"
            disc = r.get("discount_amt", 0)
            self.tree.insert("", "end", iid=str(idx), tags=(tag,), values=(
                rid_str,
                r.get("date", "—"),
                r.get("user", "—"),
                len(r.get("items", [])),
                f"EGP {r.get('subtotal', r.get('total', 0)):.2f}",
                f"- EGP {disc:.2f}" if disc else "—",
                f"EGP {r.get('total', 0):.2f}",
                r.get("promo_code", "—") or "—",
            ))

        n = len(self._filtered)
        total_n = len(self._all)
        self.count_lbl.config(
            text=f"{n} of {total_n} receipt{'s' if total_n != 1 else ''}")
        self.status_lbl.config(text="")

    # ─────────────────────────────────────────────────────────────────────────
    def search(self):
        num     = self.num_entry.get().strip()
        date    = self.date_entry.get().strip()
        cashier = self.cashier_entry.get().strip().lower()

        results = self._all
        if num:
            try:
                n = int(num)
                results = [r for r in results if r.get("id") == n]
            except ValueError:
                pass
        if date:
            results = [r for r in results if r.get("date", "") == date]
        if cashier:
            results = [r for r in results
                       if cashier in r.get("user", "").lower()]

        self._filtered = results
        self._refresh_tree()
        self.status_lbl.config(
            text=f"Found {len(results)} result(s).",
            fg=C["purple"] if results else C["danger"])

    def reset_search(self):
        self.num_entry.delete(0, tk.END)
        self.date_entry.delete(0, tk.END)
        self.cashier_entry.delete(0, tk.END)
        self._filtered = list(self._all)
        self._refresh_tree()

    # ── Barcode scanner lookup ─────────────────────────────────────────────
    def _scanner_lookup(self):
        """
        Called when Enter is pressed in the Receipt # field.
        If the field contains a scan of the format RCPT-XXXXXX, extract the number.
        Then search and auto-open if exactly one result found.
        """
        raw = self.num_entry.get().strip()
        # Support both plain number and "RCPT-000001" format printed on receipts
        if raw.upper().startswith("RCPT-"):
            raw = raw[5:]
        self.num_entry.delete(0, tk.END)
        self.num_entry.insert(0, raw)
        self.search()

        if len(self._filtered) == 1:
            # Jump directly to that receipt
            self.tree.selection_set("0")
            self._open_detail()
        elif len(self._filtered) == 0:
            self.status_lbl.config(
                text=f"Receipt #{raw} not found.", fg=C["danger"])

    # ── Detail window ──────────────────────────────────────────────────────
    def _open_detail(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        receipt = self._filtered[idx]
        ReceiptDetailWindow(
            self.frame, receipt,
            admin=self.admin,
            on_delete=self._on_delete_from_detail,
        )

    # ── Delete ─────────────────────────────────────────────────────────────
    def _delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select Receipt",
                                "Please select a receipt first.")
            return
        idx     = int(sel[0])
        receipt = self._filtered[idx]
        rid     = receipt.get("id")
        if messagebox.askyesno("Delete Receipt",
                               f"Permanently delete Receipt #{rid}?\nThis cannot be undone."):
            self._on_delete_from_detail(rid)

    def _on_delete_from_detail(self, rid):
        sales = load_json(self._sales_path())
        sales = [s for s in sales if s.get("id") != rid]
        save_json(self._sales_path(), sales)
        self.load_receipts()
        messagebox.showinfo("Deleted", f"Receipt #{rid} has been deleted.")

    # ── Sorting ────────────────────────────────────────────────────────────
    _sort_state = {}

    def _sort_by(self, col):
        reverse = self._sort_state.get(col, False)
        key_map = {
            "Receipt #": lambda r: r.get("id", 0),
            "Date":      lambda r: r.get("date", ""),
            "Cashier":   lambda r: r.get("user", "").lower(),
            "Items":     lambda r: len(r.get("items", [])),
            "Total":     lambda r: r.get("total", 0),
        }
        key = key_map.get(col, lambda r: "")
        self._filtered.sort(key=key, reverse=reverse)
        self._sort_state[col] = not reverse
        self._refresh_tree()