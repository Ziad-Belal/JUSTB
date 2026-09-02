"""
daily_feedback.py  —  JustB Retail Management System
=====================================================
Redesigned with JustB bright luxury theme.
Dynamic features:
  • Animated revenue counter on load
  • Mini bar chart drawn on a Canvas (top 5 products by revenue)
  • Colour-coded rank badges in the table (gold / silver / bronze / …)
  • Live date picker with refresh pulse
  • Best Selling Products section with time range selector
    (Last Day / Last Month / Last Year / All Time)
  • Print report includes best sellers for the selected range
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.simpledialog import askstring
from utils.helpers import load_json, get_today_date
from datetime import date, timedelta, datetime
import os
from gui.theme import C

# ══════════════════════════════════════════════════════════════════════════════
BRAND_COLORS = ["#1BBFBF", "#F0569A", "#F97316", "#8B5CF6", "#22C55E"]
RANK_COLORS  = ["#D97706", "#9CA3AF", "#C2703A", "#8B5CF6", "#1BBFBF"]

FONT_HEAD    = ("Georgia",   13, "bold")
FONT_LABEL   = ("Segoe UI",  10)
FONT_LABEL_B = ("Segoe UI",  10, "bold")
FONT_ENTRY   = ("Segoe UI",  11)
FONT_BTN     = ("Segoe UI",  10, "bold")
FONT_SMALL   = ("Segoe UI",   9)
FONT_SECTION = ("Segoe UI",   8, "bold")
FONT_STAT    = ("Georgia",   22, "bold")
FONT_STAT_LB = ("Segoe UI",   9)
FONT_TOTAL   = ("Georgia",   28, "bold")

# Time range options
TIME_RANGES = [
    ("Last Day",   "day"),
    ("Last Month", "month"),
    ("Last Year",  "year"),
    ("All Time",   "all"),
]

FEEDBACK_CATEGORIES = [
    ("Makeup & Cosmetics", "Makeup & Cosmetics"),
    ("Stationary",          "Stationary"),
    ("Both",                "both"),
]


def _btn(parent, text, command, bg, hover, fg="#FFFFFF",
         font=FONT_BTN, padx=16, pady=8):
    b = tk.Label(parent, text=text, font=font,
                 bg=bg, fg=fg, cursor="hand2",
                 relief="flat", padx=padx, pady=pady)
    b.bind("<Button-1>", lambda e: command())
    b.bind("<Enter>",    lambda e: b.config(bg=hover))
    b.bind("<Leave>",    lambda e: b.config(bg=bg))
    return b


def _date_range_for(range_key):
    """Return (start_date_str, end_date_str) for the given range key."""
    today = date.today()
    end   = today.isoformat()
    if range_key == "day":
        start = today.isoformat()
    elif range_key == "month":
        start = (today - timedelta(days=30)).isoformat()
    elif range_key == "year":
        start = (today - timedelta(days=365)).isoformat()
    else:  # "all"
        start = "0000-01-01"
    return start, end


# ══════════════════════════════════════════════════════════════════════════════

class DailyFeedbackScreen:
    def __init__(self, root, data_dir=None, frame_parent=None, admin=False):
        self.root      = root
        self.data_dir  = data_dir
        self.admin     = admin
        self.feedback_date = get_today_date()

        # Currently selected best-sellers time range and filters
        self._bs_range          = tk.StringVar(value="day")
        self._feedback_category = tk.StringVar(value="Both")
        self._custom_bs_start   = tk.StringVar(value=self.feedback_date)
        self._custom_bs_end     = tk.StringVar(value=self.feedback_date)
        self._custom_range      = False

        self.frame = tk.Frame(frame_parent or root, bg=C["bg_root"])
        self.frame.pack(fill="both", expand=True)

        self._build_ui()
        self.load_data()

    def _sales_path(self):
        return os.path.join(self.data_dir, "sales.json")

    # ══════════════════════════════════════════════════════════════════════════
    def _build_ui(self):

        # ── Header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(self.frame, bg=C["bg_header"],
                       highlightthickness=1,
                       highlightbackground=C["border"])
        hdr.pack(fill="x")

        dots = tk.Frame(hdr, bg=C["bg_header"])
        dots.pack(side="left", padx=(16, 4), pady=10)
        for col in BRAND_COLORS:
            tk.Label(dots, text="●", font=("Segoe UI", 9),
                     bg=C["bg_header"], fg=col).pack(side="left", padx=1)
        tk.Label(hdr, text="Feedback",
                 font=FONT_HEAD, bg=C["bg_header"],
                 fg=C["text_dark"]).pack(side="left", padx=(6, 0), pady=10)

        # Date picker on right of header
        date_frame = tk.Frame(hdr, bg=C["bg_header"])
        date_frame.pack(side="right", padx=16, pady=8)

        tk.Label(date_frame, text="Viewing date:",
                 font=FONT_SMALL, bg=C["bg_header"],
                 fg=C["text_light"]).pack(side="left", padx=(0, 8))

        self.date_lbl = tk.Label(date_frame,
                                  text=self.feedback_date,
                                  font=FONT_LABEL_B,
                                  bg=C["purple"], fg="#FFFFFF",
                                  padx=12, pady=5, cursor="hand2")
        self.date_lbl.pack(side="left")
        self.date_lbl.bind("<Button-1>", lambda e: self._pick_date())
        self.date_lbl.bind("<Enter>",    lambda e: self.date_lbl.config(bg=C["purple_dk"]))
        self.date_lbl.bind("<Leave>",    lambda e: self.date_lbl.config(bg=C["purple"]))

        if self.admin:
            _btn(date_frame, "⟳  Refresh",
                 self.load_data,
                 C["teal"], "#159F9F",
                 padx=12, pady=5).pack(side="left", padx=(8, 0))

        # ── Feedback filter row ─────────────────────────────────────────────────
        filter_row = tk.Frame(self.frame, bg=C["bg_root"])
        filter_row.pack(fill="x", padx=14, pady=(10, 0))
        tk.Label(filter_row, text="Feedback category:",
                 font=FONT_LABEL_B, bg=C["bg_root"],
                 fg=C["text_mid"]).pack(side="left")
        self.feedback_category_cb = ttk.Combobox(
            filter_row,
            textvariable=self._feedback_category,
            values=[label for label, _ in FEEDBACK_CATEGORIES],
            state="readonly",
            width=20,
            font=FONT_ENTRY)
        self.feedback_category_cb.pack(side="left", padx=(8, 0))
        self.feedback_category_cb.bind(
            "<<ComboboxSelected>>", lambda e: self.load_data())

        # ── Top KPI cards row ─────────────────────────────────────────────────
        kpi_row = tk.Frame(self.frame, bg=C["bg_root"])
        kpi_row.pack(fill="x", padx=14, pady=(10, 0))
        for i in range(4):
            kpi_row.columnconfigure(i, weight=1)

        self._kpi_revenue = self._kpi_card(kpi_row, "REVENUE TODAY",    "EGP 0.00", C["green"],  0)
        self._kpi_sales   = self._kpi_card(kpi_row, "SALES COUNT",       "0",        C["purple"], 1)
        self._kpi_items   = self._kpi_card(kpi_row, "ITEMS SOLD",         "0",        C["teal"],   2)
        self._kpi_avg     = self._kpi_card(kpi_row, "AVG SALE VALUE",     "EGP 0.00", C["orange"], 3)

        # ── Body: left (table) + right (mini bar chart) ───────────────────────
        body = tk.Frame(self.frame, bg=C["bg_root"])
        body.pack(fill="both", expand=True, padx=14, pady=10)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2, minsize=260)
        body.rowconfigure(0, weight=1)

        # ── LEFT: Product sales table ─────────────────────────────────────────
        tree_card = tk.Frame(body, bg=C["bg_card"],
                             highlightthickness=1,
                             highlightbackground=C["border"])
        tree_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        tree_card.rowconfigure(1, weight=1)
        tree_card.columnconfigure(0, weight=1)

        ch = tk.Frame(tree_card, bg=C["bg_panel"], padx=14, pady=10)
        ch.grid(row=0, column=0, columnspan=2, sticky="ew")
        dot_f = tk.Frame(ch, bg=C["bg_panel"])
        dot_f.pack(side="left")
        for col in BRAND_COLORS:
            tk.Label(dot_f, text="●", font=("Segoe UI", 8),
                     bg=C["bg_panel"], fg=col).pack(side="left", padx=1)
        tk.Label(ch, text="  PRODUCT PERFORMANCE (TODAY)",
                 font=FONT_SECTION, bg=C["bg_panel"],
                 fg=C["text_mid"]).pack(side="left")

        ts = ttk.Style()
        ts.configure("DF.Treeview",
                     background=C["bg_card"],
                     foreground=C["text_dark"],
                     fieldbackground=C["bg_card"],
                     rowheight=38,
                     font=("Segoe UI", 10),
                     borderwidth=0, relief="flat")
        ts.configure("DF.Treeview.Heading",
                     background=C["bg_panel"],
                     foreground=C["text_mid"],
                     font=("Segoe UI", 9, "bold"),
                     relief="flat", borderwidth=0)
        ts.map("DF.Treeview",
               background=[("selected", C["bg_panel"])],
               foreground=[("selected", C["purple"])])
        ts.layout("DF.Treeview",
                  [('Treeview.treearea', {'sticky': 'nswe'})])

        cols = ("#", "Product", "Qty Sold", "Revenue")
        self.tree = ttk.Treeview(tree_card, columns=cols,
                                  show="headings", selectmode="browse",
                                  style="DF.Treeview")
        cw = {"#": 40, "Product": 220, "Qty Sold": 80, "Revenue": 110}
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center",
                              width=cw[col], minwidth=40)

        # Rank tag colours
        for i, col in enumerate(RANK_COLORS):
            self.tree.tag_configure(f"rank{i}", foreground=col)
            self.tree.tag_configure(f"rank{i}_odd",
                                    background=C["bg_row_alt"], foreground=col)

        vsb = ttk.Scrollbar(tree_card, orient="vertical",
                             command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=1, column=0, sticky="nsew")
        vsb.grid(row=1, column=1, sticky="ns")

        # ── RIGHT: Totals + mini bar chart + best sellers ─────────────────────
        right = tk.Frame(body, bg=C["bg_root"])
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        right.rowconfigure(2, weight=2)

        # Big total card
        tot_card = tk.Frame(right, bg=C["bg_card"],
                            highlightthickness=1,
                            highlightbackground=C["border"],
                            padx=20, pady=18)
        tot_card.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        tk.Frame(tot_card, bg=C["green"], height=4).pack(fill="x", pady=(0, 12))
        tk.Label(tot_card, text="TOTAL REVENUE",
                 font=FONT_SECTION, bg=C["bg_card"],
                 fg=C["text_light"]).pack(anchor="w")
        self.total_lbl = tk.Label(tot_card, text="EGP 0.00",
                                   font=FONT_TOTAL,
                                   bg=C["bg_card"], fg=C["green"])
        self.total_lbl.pack(anchor="w")
        self.sales_count_lbl = tk.Label(tot_card, text="0 transactions",
                                         font=FONT_LABEL,
                                         bg=C["bg_card"], fg=C["text_light"])
        self.sales_count_lbl.pack(anchor="w", pady=(4, 0))

        # Mini bar chart canvas
        chart_card = tk.Frame(right, bg=C["bg_card"],
                              highlightthickness=1,
                              highlightbackground=C["border"])
        chart_card.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        chart_card.rowconfigure(1, weight=1)
        chart_card.columnconfigure(0, weight=1)

        ch2 = tk.Frame(chart_card, bg=C["bg_panel"], padx=14, pady=10)
        ch2.grid(row=0, column=0, sticky="ew")
        tk.Label(ch2, text="BEST SELLERS CHART",
             font=FONT_SECTION, bg=C["bg_panel"],
             fg=C["text_mid"]).pack(side="left")
        # View larger button
        view_btn = tk.Label(ch2, text="⤢ View Larger",
                    font=("Segoe UI", 9, "bold"), bg=C["bg_panel"],
                    fg=C["text_mid"], cursor="hand2", padx=8)
        view_btn.pack(side="right")
        view_btn.bind("<Button-1>", lambda e: self._open_chart_popup(self._get_best_sellers_data()))

        # Make chart canvas larger and more readable
        # Make the embedded chart canvas flexible (no fixed height)
        self.chart_canvas = tk.Canvas(chart_card, bg=C["bg_card"],
                           highlightthickness=0)
        self.chart_canvas.grid(row=1, column=0, sticky="nsew",
                       padx=12, pady=12)
        chart_card.rowconfigure(1, weight=1)

        # ── Best Sellers card ─────────────────────────────────────────────────
        bs_card = tk.Frame(right, bg=C["bg_card"],
                           highlightthickness=1,
                           highlightbackground=C["border"])
        bs_card.grid(row=2, column=0, sticky="nsew")
        bs_card.rowconfigure(3, weight=1)
        bs_card.columnconfigure(0, weight=1)

        # Best sellers header
        bs_hdr = tk.Frame(bs_card, bg=C["bg_panel"], padx=14, pady=10)
        bs_hdr.grid(row=0, column=0, sticky="ew")
        tk.Frame(bs_hdr, bg=C["pink"], height=3).pack(fill="x", pady=(0, 6))
        tk.Label(bs_hdr, text="🏆  BEST SELLING PRODUCTS",
                 font=FONT_SECTION, bg=C["bg_panel"],
                 fg=C["text_mid"]).pack(anchor="w")

        # Time range selector buttons
        range_row = tk.Frame(bs_card, bg=C["bg_card"], padx=12, pady=8)
        range_row.grid(row=1, column=0, sticky="ew")

        self._range_btns = {}
        for label, key in TIME_RANGES:
            btn = tk.Label(
                range_row, text=label,
                font=("Segoe UI", 8, "bold"),
                bg=C["bg_panel"], fg=C["text_mid"],
                cursor="hand2", relief="flat",
                padx=8, pady=4,
                highlightthickness=1,
                highlightbackground=C["border_acc"]
            )
            btn.pack(side="left", padx=(0, 6))
            btn.bind("<Button-1>", lambda e, k=key: self._select_bs_range(k))
            self._range_btns[key] = btn

        custom_row = tk.Frame(bs_card, bg=C["bg_card"], padx=12, pady=4)
        custom_row.grid(row=2, column=0, sticky="ew")

        tk.Label(custom_row, text="Custom range:",
                 font=FONT_LABEL_B, bg=C["bg_card"],
                 fg=C["text_mid"]).pack(side="left")
        self.bs_custom_start = tk.Entry(custom_row, textvariable=self._custom_bs_start,
                                        font=FONT_ENTRY, width=10,
                                        bg=C["bg_input"], relief="flat",
                                        highlightthickness=1,
                                        highlightbackground=C["border"])
        self.bs_custom_start.pack(side="left", padx=(8, 4))
        tk.Label(custom_row, text="to", font=FONT_LABEL,
                 bg=C["bg_card"], fg=C["text_mid"]).pack(side="left")
        self.bs_custom_end = tk.Entry(custom_row, textvariable=self._custom_bs_end,
                                      font=FONT_ENTRY, width=10,
                                      bg=C["bg_input"], relief="flat",
                                      highlightthickness=1,
                                      highlightbackground=C["border"])
        self.bs_custom_end.pack(side="left", padx=(4, 8))
        _btn(custom_row, "Apply", self._apply_custom_bs_range,
             C["purple"], C["purple_dk"], padx=10, pady=6).pack(side="left")

        # Best sellers treeview
        bs_style = ttk.Style()
        bs_style.configure("BS.Treeview",
                           background=C["bg_card"],
                           foreground=C["text_dark"],
                           fieldbackground=C["bg_card"],
                           rowheight=30,
                           font=("Segoe UI", 9),
                           borderwidth=0, relief="flat")
        bs_style.configure("BS.Treeview.Heading",
                           background=C["bg_panel"],
                           foreground=C["text_mid"],
                           font=("Segoe UI", 8, "bold"),
                           relief="flat", borderwidth=0)
        bs_style.map("BS.Treeview",
                     background=[("selected", C["bg_panel"])],
                     foreground=[("selected", C["pink"])])
        bs_style.layout("BS.Treeview",
                        [('Treeview.treearea', {'sticky': 'nswe'})])

        bs_cols = ("#", "Product", "Qty", "Revenue")
        self.bs_tree = ttk.Treeview(bs_card, columns=bs_cols,
                                     show="headings", selectmode="none",
                                     style="BS.Treeview")
        bs_cw = {"#": 32, "Product": 130, "Qty": 40, "Revenue": 90}
        for col in bs_cols:
            self.bs_tree.heading(col, text=col)
            self.bs_tree.column(col, anchor="center",
                                 width=bs_cw[col], minwidth=30)

        for i, col in enumerate(RANK_COLORS):
            self.bs_tree.tag_configure(f"bs_rank{i}", foreground=col)

        bs_vsb = ttk.Scrollbar(bs_card, orient="vertical",
                                command=self.bs_tree.yview)
        self.bs_tree.configure(yscrollcommand=bs_vsb.set)
        self.bs_tree.grid(row=3, column=0, sticky="nsew")
        bs_vsb.grid(row=3, column=1, sticky="ns")

        # Highlight default range button
        self._select_bs_range("day")

        # Print button
        if self.admin:
            _btn(right, "🖨  Print Report",
                 self.print_report,
                 C["orange"], "#E05F00",
                 padx=0, pady=10).grid(
                     row=3, column=0, sticky="ew", pady=(8, 0))

        # Footer
        tk.Label(self.frame,
                 text="justb-eg.com  ·  Stationery & Gifts",
                 font=("Segoe UI", 8),
                 bg=C["bg_root"], fg=C["text_light"]).pack(side="bottom", pady=4)

    # ── KPI card ──────────────────────────────────────────────────────────────

    def _kpi_card(self, parent, label, value, accent, col):
        card = tk.Frame(parent, bg=C["bg_card"],
                        highlightthickness=1,
                        highlightbackground=C["border"],
                        padx=16, pady=14)
        card.grid(row=0, column=col, sticky="ew",
                  padx=(0 if col == 0 else 8, 0))
        tk.Frame(card, bg=accent, height=3).pack(fill="x", pady=(0, 8))
        tk.Label(card, text=label, font=FONT_STAT_LB,
                 bg=C["bg_card"], fg=C["text_light"]).pack(anchor="w")
        val = tk.Label(card, text=value, font=FONT_STAT,
                       bg=C["bg_card"], fg=accent)
        val.pack(anchor="w")
        return val

    # ── Animated counter ──────────────────────────────────────────────────────

    def _animate_float(self, label, target, prefix="EGP ", steps=24):
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

    def _animate_int(self, label, target, prefix="", suffix="", steps=20):
        try:
            raw = label.cget("text").replace(prefix, "").replace(suffix, "").replace(",", "").strip() or "0"
            current = int(float(raw))
        except Exception:
            current = 0
        delta = target - current

        def _step(i=0):
            if i > steps:
                label.config(text=f"{prefix}{target:,}{suffix}")
                return
            label.config(text=f"{prefix}{int(current + delta * i/steps):,}{suffix}")
            label.after(16, lambda: _step(i + 1))

        _step()

    # ── Mini bar chart ────────────────────────────────────────────────────────

    def _draw_chart(self, items):
        """Draw a horizontal bar chart for top-5 products."""
        canvas = self.chart_canvas
        canvas.delete("all")
        canvas.update_idletasks()
        W = canvas.winfo_width()
        H = canvas.winfo_height()
        if W < 10 or H < 10:
            return

        top5 = sorted(items, key=lambda x: x["revenue"], reverse=True)[:5]
        if not top5:
            canvas.create_text(W // 2, H // 2,
                               text="No sales data for the selected range",
                               font=FONT_SMALL, fill=C["text_light"])
            return

        max_rev = max(x["revenue"] for x in top5)
        if max_rev == 0:
            return

        # Layout: names on left column, bars on the right for clarity
        pad_name = 8
        pad_l = 140   # left edge of bars (reserve space for names)
        pad_r = 20
        pad_t = 12
        pad_b = 12
        gap   = 12
        bar_h = max(18, (H - pad_t - pad_b - (len(top5) - 1) * gap) // len(top5))
        usable_w = max(80, W - pad_l - pad_r)

        def _draw_bar(idx, item, pct):
            y = pad_t + idx * (bar_h + gap)
            bar_w = int(usable_w * pct)
            col = BRAND_COLORS[idx % len(BRAND_COLORS)]

            # Product name on left
            name = item["name"]
            truncated = (name[:24] + "…") if len(name) > 24 else name
            canvas.create_text(pad_name, y + bar_h // 2,
                               text=truncated, font=("Segoe UI", 9),
                               fill=C["text_mid"], anchor="w")

            # Background track
            canvas.create_rectangle(pad_l, y, pad_l + usable_w, y + bar_h,
                                    fill=C["bg_panel"], outline="")

            # Animated bar
            def _anim(w=0):
                canvas.delete(f"bar{idx}")
                canvas.create_rectangle(pad_l, y, pad_l + w, y + bar_h,
                                         fill=col, outline="",
                                         tags=(f"bar{idx}",))
                if w >= bar_w:
                    # show revenue label; inside bar if space, else to the right
                    label_x = pad_l + min(bar_w, usable_w - 6)
                    if bar_w > 60:
                        canvas.create_text(label_x - 6, y + bar_h // 2,
                                           text=f"EGP {item['revenue']:,.2f}",
                                           font=("Segoe UI", 9, "bold"),
                                           fill="#ffffff", anchor="e")
                    else:
                        canvas.create_text(pad_l + bar_w + 8, y + bar_h // 2,
                                           text=f"EGP {item['revenue']:,.2f}",
                                           font=("Segoe UI", 9),
                                           fill=C["text_mid"], anchor="w")
                    return
                canvas.after(10, lambda: _anim(w + max(1, bar_w // 18)))

            _anim()

        for i, item in enumerate(top5):
            pct = item["revenue"] / max_rev if max_rev > 0 else 0
            _draw_bar(i, item, pct)

    def _render_chart(self, canvas, items):
        """Shared renderer for a canvas instance."""
        # We reuse the drawing logic above but target the given canvas
        try:
            # call the main draw routine by temporarily swapping self.chart_canvas
            current = self.chart_canvas
            self.chart_canvas = canvas
            self._draw_chart(items)
        finally:
            self.chart_canvas = current

    def _open_chart_popup(self, items):
        """Open a resizable popup with the chart and scrollbars."""
        popup = tk.Toplevel(self.root)
        popup.title("Best Sellers — Large View")
        popup.configure(bg=C["bg_root"])
        popup.geometry("800x500")
        popup.minsize(480, 320)

        # Make it resizable and center roughly
        popup.transient(self.root)

        frame = tk.Frame(popup, bg=C["bg_card"], padx=8, pady=8)
        frame.pack(fill="both", expand=True)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        canvas = tk.Canvas(frame, bg=C["bg_card"], highlightthickness=0)
        vsb = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        # Redraw on resize; throttle rapid events
        def _on_config(e=None):
            canvas.delete("all")
            canvas.update_idletasks()
            self._render_chart(canvas, items)
            canvas.configure(scrollregion=canvas.bbox("all"))

        popup.bind("<Configure>", lambda e: popup.after(120, _on_config))
        # Initial render
        _on_config()

        return popup

    def _load_product_category_map(self):
        """Build barcode→category map fresh from products.json every time load_data runs.
        We intentionally do NOT cache this permanently — products can be added/edited
        at any time and the category filter must reflect the current state.
        The map is stored as _product_category_map and rebuilt at the start of
        each load_data() call via _refresh_category_map().
        """
        products = load_json(os.path.join(self.data_dir, "products.json"))
        self._product_category_map = {
            str(p.get("barcode", "")): str(p.get("category", "")).strip()
            for p in products
        }
        return self._product_category_map

    def _matches_feedback_category(self, item):
        selected = self._feedback_category.get()
        if selected == "Both":
            return True

        # Try category stored directly on the sale item first
        category = str(item.get("category", "") or "").strip().lower()

        # Fall back to the product map (looked up by barcode)
        if not category and item.get("barcode") is not None:
            category = self._product_category_map.get(
                str(item.get("barcode", "")), "").strip().lower()

        if selected == "Makeup & Cosmetics":
            return category == "makeup & cosmetics"
        if selected == "Stationary":
            # Accept both spellings that may appear in products.json
            return category in {"stationary", "stationery", "library stuff"}
        return True

    def _parse_date(self, value, default=None):
        try:
            return date.fromisoformat(value)
        except Exception:
            return default

    def _selected_bs_range(self):
        if self._custom_range:
            start = self._parse_date(self._custom_bs_start.get(), None)
            end   = self._parse_date(self._custom_bs_end.get(), None)
            if start and end and start <= end:
                return start.isoformat(), end.isoformat()
            # Fall back to selected preset when custom dates are invalid.
        return _date_range_for(self._bs_range.get())

    def _apply_custom_bs_range(self):
        start = self._parse_date(self._custom_bs_start.get())
        end   = self._parse_date(self._custom_bs_end.get())
        if not start or not end:
            messagebox.showerror("Invalid Dates",
                                 "Enter valid dates in YYYY-MM-DD format.")
            return
        if start > end:
            messagebox.showerror("Invalid Range",
                                 "Start date must be before or equal to end date.")
            return
        self._custom_range = True
        self._select_bs_range(self._bs_range.get())

    def _select_bs_range(self, key):
        """Highlight the chosen range button and reload best sellers."""
        self._custom_range = False
        self._bs_range.set(key)
        for k, btn in self._range_btns.items():
            if k == key:
                btn.config(bg=C["pink"], fg="#FFFFFF",
                           highlightbackground=C["pink"])
            else:
                btn.config(bg=C["bg_panel"], fg=C["text_mid"],
                           highlightbackground=C["border_acc"])
        self._load_best_sellers()

    def _load_best_sellers(self):
        """Compute and display best-selling products for the selected time range."""
        for i in self.bs_tree.get_children():
            self.bs_tree.delete(i)

        sales = load_json(self._sales_path())
        start, end = self._selected_bs_range()
        product_summary = {}

        for sale in sales:
            sale_date = sale.get("date", "")
            if not (start <= sale_date <= end):
                continue
            for item in sale.get("items", []):
                if not self._matches_feedback_category(item):
                    continue
                key = item.get("barcode", item.get("name", "?"))
                if key not in product_summary:
                    product_summary[key] = {
                        "name":    item.get("name", "?"),
                        "qty":     0,
                        "revenue": 0.0,
                    }
                qty = int(item.get("quantity", 1))
                product_summary[key]["qty"]     += qty
                product_summary[key]["revenue"] += float(item.get("price", 0)) * qty

        sorted_prods = sorted(product_summary.values(),
                              key=lambda x: x["revenue"], reverse=True)

        rank_sym = ["🥇", "🥈", "🥉"] + ["·"] * 50
        for idx, item in enumerate(sorted_prods):
            tag = f"bs_rank{min(idx, len(RANK_COLORS)-1)}"
            self.bs_tree.insert("", "end", tags=(tag,),
                                values=(rank_sym[idx],
                                        item["name"],
                                        item["qty"],
                                        f"EGP {item['revenue']:,.2f}"))

        self._draw_chart(sorted_prods)

    def _get_best_sellers_data(self):
        """Return sorted best sellers list for the current range (used in print)."""
        sales = load_json(self._sales_path())
        start, end = self._selected_bs_range()
        product_summary = {}

        for sale in sales:
            sale_date = sale.get("date", "")
            if not (start <= sale_date <= end):
                continue
            for item in sale.get("items", []):
                if not self._matches_feedback_category(item):
                    continue
                key = item.get("barcode", item.get("name", "?"))
                if key not in product_summary:
                    product_summary[key] = {
                        "name":    item.get("name", "?"),
                        "qty":     0,
                        "revenue": 0.0,
                    }
                qty = int(item.get("quantity", 1))
                product_summary[key]["qty"]     += qty
                product_summary[key]["revenue"] += float(item.get("price", 0)) * qty

        return sorted(product_summary.values(),
                      key=lambda x: x["revenue"], reverse=True)

    # ══════════════════════════════════════════════════════════════════════════
    #  Data
    # ══════════════════════════════════════════════════════════════════════════

    def _pick_date(self):
        new_date = askstring("Select Date",
                             "Enter date (YYYY-MM-DD):",
                             initialvalue=self.feedback_date,
                             parent=self.frame)
        if new_date:
            self.feedback_date = new_date
            self.date_lbl.config(text=self.feedback_date)
            self.load_data()

    def load_data(self):
        # Refresh product→category map so new/edited products are reflected
        self._load_product_category_map()

        for i in self.tree.get_children():
            self.tree.delete(i)

        sales = load_json(self._sales_path())

        total_revenue  = 0.0
        total_sales    = 0
        total_items    = 0
        product_summary = {}

        for sale in sales:
            if sale.get("date", "") != self.feedback_date:
                continue
            sale_items = [item for item in sale.get("items", [])
                          if self._matches_feedback_category(item)]
            if not sale_items:
                continue
            sale_revenue = 0.0
            for item in sale_items:
                qty = int(item.get("quantity", 1))
                sale_revenue += float(item.get("price", 0)) * qty
                key = item.get("barcode", item.get("name", "?"))
                if key not in product_summary:
                    product_summary[key] = {
                        "name":    item.get("name", "?"),
                        "qty":     0,
                        "revenue": 0.0,
                    }
                product_summary[key]["qty"]     += qty
                product_summary[key]["revenue"] += float(item.get("price", 0)) * qty
                total_items += qty
            total_sales   += 1
            total_revenue += sale_revenue

        avg_sale = (total_revenue / total_sales) if total_sales > 0 else 0.0

        # Animate KPIs
        self._animate_float(self._kpi_revenue, total_revenue)
        self._animate_int  (self._kpi_sales,   total_sales)
        self._animate_int  (self._kpi_items,   total_items)
        self._animate_float(self._kpi_avg,     avg_sale)

        # Animate big total
        self._animate_float(self.total_lbl, total_revenue)
        self.sales_count_lbl.config(
            text=f"{total_sales} transaction{'s' if total_sales != 1 else ''}")

        # Populate table — sorted by revenue desc
        sorted_prods = sorted(product_summary.values(),
                              key=lambda x: x["revenue"], reverse=True)

        for idx, item in enumerate(sorted_prods):
            rank = idx
            tag_base = f"rank{min(rank, len(RANK_COLORS)-1)}"
            tag = tag_base + ("_odd" if idx % 2 else "")
            rank_sym = ["🥇", "🥈", "🥉"] + ["·"] * 10
            sym = rank_sym[rank] if rank < len(rank_sym) else "·"
            self.tree.insert("", "end", tags=(tag,),
                             values=(sym,
                                     item["name"],
                                     item["qty"],
                                     f"EGP {item['revenue']:,.2f}"))

        # Draw bar chart after geometry settles
        self.frame.after(80, lambda: self._draw_chart(sorted_prods))

        # Reload best sellers for current range
        self._load_best_sellers()

    # ── Print / Export ─────────────────────────────────────────────────────────

    def print_report(self):
        """Export options: TXT or CSV."""
        dialog = tk.Toplevel(self.frame)
        dialog.title("Export Report")
        dialog.resizable(False, False)
        dialog.configure(bg=C["bg_card"])
        dialog.grab_set()

        pw, ph = 300, 160
        sx = dialog.winfo_screenwidth()
        sy = dialog.winfo_screenheight()
        dialog.geometry(f"{pw}x{ph}+{(sx-pw)//2}+{(sy-ph)//2}")

        tk.Frame(dialog, bg=C["purple"], height=3).pack(fill="x")
        tk.Label(dialog, text="Export Report As",
                 font=("Segoe UI", 11, "bold"),
                 bg=C["bg_card"], fg=C["text_dark"]).pack(pady=(16, 12))

        btn_row = tk.Frame(dialog, bg=C["bg_card"])
        btn_row.pack(padx=20, fill="x")

        def _do(fmt):
            dialog.destroy()
            if fmt == "txt":
                self._export_txt()
            elif fmt == "csv":
                self._export_csv()

        _btn(btn_row, "📄  TXT", lambda: _do("txt"),
             C["text_mid"], C["text_dark"], padx=14, pady=10).pack(
                 side="left", expand=True, fill="x", padx=(0, 8))
        _btn(btn_row, "📊  CSV", lambda: _do("csv"),
             C["teal"], "#159F9F", padx=14, pady=10).pack(
                 side="left", expand=True, fill="x")

    def _export_txt(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            title="Save TXT Report",
            initialfile=f"JustB_Report_{self.feedback_date}.txt"
        )
        if not file_path:
            return

        range_key = self._bs_range.get()
        if self._custom_range:
            range_label = "Custom Range"
            start, end = self._selected_bs_range()
        else:
            range_label = next(lbl for lbl, k in TIME_RANGES if k == range_key)
            start, end = _date_range_for(range_key)
        best_sellers = self._get_best_sellers_data()

        lines = [
            "=" * 46,
            f"  JustB Daily Report — {self.feedback_date}",
            "=" * 46,
            f"  Revenue:      {self.total_lbl.cget('text')}",
            f"  Transactions: {self._kpi_sales.cget('text')}",
            f"  Items Sold:   {self._kpi_items.cget('text')}",
            f"  Avg Sale:     {self._kpi_avg.cget('text')}",
            "-" * 46,
            f"  {'Rank':<6} {'Product':<24} {'Qty':>5}  {'Revenue':>12}",
            "-" * 46,
        ]
        for item in self.tree.get_children():
            v = self.tree.item(item)["values"]
            lines.append(f"  {str(v[0]):<6} {str(v[1]):<24} {str(v[2]):>5}  {str(v[3]):>12}")

        lines += [
            "",
            "=" * 46,
            f"  BEST SELLING PRODUCTS — {range_label}",
            f"  (Period: {start}  to  {end})",
            "=" * 46,
            f"  {'Rank':<6} {'Product':<24} {'Qty':>5}  {'Revenue':>12}",
            "-" * 46,
        ]
        for idx, item in enumerate(best_sellers):
            lines.append(
                f"  #{idx+1:<5} {item['name']:<24} {item['qty']:>5}  "
                f"EGP {item['revenue']:>9,.2f}"
            )
        if not best_sellers:
            lines.append("  No sales data for this period.")
        lines += ["-" * 46, "  justb-eg.com", "=" * 46]

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        messagebox.showinfo("Saved", f"TXT report saved:\n{file_path}")

    def _export_csv(self):
        """Export today's individual sale line-items to CSV."""
        import csv
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Save CSV Report",
            initialfile=f"JustB_Sales_{self.feedback_date}.csv"
        )
        if not file_path:
            return

        sales = load_json(self._sales_path())
        day_sales = [s for s in sales if s.get("date", "") == self.feedback_date]

        with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Receipt ID", "Date", "Time", "Cashier",
                "Item Barcode", "Item Name", "Qty", "Unit Price", "Line Total",
                "Subtotal", "Discount %", "Discount Amt",
                "Tax %", "Tax Amt", "Total",
                "Promo Code", "Payment Method", "Status"
            ])
            for sale in day_sales:
                for item in sale.get("items", []):
                    qty   = int(item.get("quantity", 1))
                    price = float(item.get("price", 0))
                    writer.writerow([
                        sale.get("id", ""),
                        sale.get("date", ""),
                        sale.get("time", ""),
                        sale.get("user", ""),
                        item.get("barcode", ""),
                        item.get("name", ""),
                        qty,
                        f"{price:.2f}",
                        f"{qty * price:.2f}",
                        f"{sale.get('subtotal', 0):.2f}",
                        sale.get("discount_pct", 0),
                        f"{sale.get('discount_amt', 0):.2f}",
                        sale.get("tax_pct", 0),
                        f"{sale.get('tax_amt', 0):.2f}",
                        f"{sale.get('total', 0):.2f}",
                        sale.get("promo_code", ""),
                        sale.get("payment_method", ""),
                        sale.get("status", "Completed"),
                    ])
        messagebox.showinfo("Saved", f"CSV report saved:\n{file_path}")
        dialog = tk.Toplevel(self.frame)
        dialog.title("Export Daily Report")
        dialog.resizable(False, False)
        dialog.configure(bg=C["bg_card"])
        dialog.grab_set()

        pw, ph = 340, 220
        sx = dialog.winfo_screenwidth()
        sy = dialog.winfo_screenheight()
        dialog.geometry(f"{pw}x{ph}+{(sx-pw)//2}+{(sy-ph)//2}")

        tk.Frame(dialog, bg=C["purple"], height=3).pack(fill="x")
        tk.Label(dialog, text="Export Report As",
                 font=("Segoe UI", 11, "bold"),
                 bg=C["bg_card"], fg=C["text_dark"]).pack(pady=(16, 12))

        btn_row = tk.Frame(dialog, bg=C["bg_card"])
        btn_row.pack(padx=20, fill="x")

        def _do(fmt):
            dialog.destroy()
            if fmt == "txt":
                self._export_txt()
            elif fmt == "csv":
                self._export_csv()
            elif fmt == "pdf":
                self._export_pdf()

        _btn(btn_row, "📄  TXT",  lambda: _do("txt"),
             C["text_mid"], C["text_dark"], padx=14, pady=10).pack(
                 side="left", expand=True, fill="x", padx=(0, 6))
        _btn(btn_row, "📊  CSV",  lambda: _do("csv"),
             C["teal"], "#159F9F", padx=14, pady=10).pack(
                 side="left", expand=True, fill="x", padx=(0, 6))
        _btn(btn_row, "📑  PDF",  lambda: _do("pdf"),
             C["purple"], C["purple_dk"], padx=14, pady=10).pack(
                 side="left", expand=True, fill="x")

        tk.Label(dialog, text="PDF requires reportlab  (pip install reportlab)",
                 font=("Segoe UI", 8), bg=C["bg_card"],
                 fg=C["text_light"]).pack(pady=(14, 0))

    # ─────────────────────────────────────────────────────────────────────────
    def _report_lines(self):
        """Build the report body as a list of strings (shared by TXT and PDF)."""
        range_key = self._bs_range.get()
        if self._custom_range:
            range_label = "Custom Range"
            start, end = self._selected_bs_range()
        else:
            range_label = next(lbl for lbl, k in TIME_RANGES if k == range_key)
            start, end = _date_range_for(range_key)
        best_sellers = self._get_best_sellers_data()

        lines = [
            "=" * 46,
            f"  JustB Daily Report — {self.feedback_date}",
            "=" * 46,
            f"  Revenue:      {self.total_lbl.cget('text')}",
            f"  Transactions: {self._kpi_sales.cget('text')}",
            f"  Items Sold:   {self._kpi_items.cget('text')}",
            f"  Avg Sale:     {self._kpi_avg.cget('text')}",
            "-" * 46,
            f"  {'Rank':<6} {'Product':<24} {'Qty':>5}  {'Revenue':>12}",
            "-" * 46,
        ]
        for item in self.tree.get_children():
            v = self.tree.item(item)["values"]
            lines.append(f"  {str(v[0]):<6} {str(v[1]):<24} {str(v[2]):>5}  {str(v[3]):>12}")

        lines += [
            "",
            "=" * 46,
            f"  BEST SELLING PRODUCTS — {range_label}",
            f"  (Period: {start}  to  {end})",
            "=" * 46,
            f"  {'Rank':<6} {'Product':<24} {'Qty':>5}  {'Revenue':>12}",
            "-" * 46,
        ]
        rank_labels = [f"#{i+1}" for i in range(50)]
        for idx, item in enumerate(best_sellers):
            rank = rank_labels[idx] if idx < len(rank_labels) else f"#{idx+1}"
            lines.append(
                f"  {rank:<6} {item['name']:<24} {item['qty']:>5}  "
                f"EGP {item['revenue']:>9,.2f}"
            )
        if not best_sellers:
            lines.append("  No sales data for this period.")
        lines += ["-" * 46, "  justb-eg.com", "=" * 46]
        return lines

    def _export_txt(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            title="Save TXT Report",
            initialfile=f"JustB_Report_{self.feedback_date}.txt"
        )
        if not file_path:
            return
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(self._report_lines()))
        messagebox.showinfo("Saved", f"TXT report saved:\n{file_path}")

    def _export_csv(self):
        """Export today's sales to a proper CSV file."""
        import csv
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Save CSV Report",
            initialfile=f"JustB_Sales_{self.feedback_date}.csv"
        )
        if not file_path:
            return

        sales = load_json(self._sales_path())
        day_sales = [s for s in sales if s.get("date", "") == self.feedback_date]

        with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            # Header
            writer.writerow([
                "Receipt ID", "Date", "Time", "Cashier",
                "Item Barcode", "Item Name", "Qty", "Unit Price", "Line Total",
                "Subtotal", "Discount %", "Discount Amt", "Tax %", "Tax Amt",
                "Total", "Promo Code", "Payment Method", "Status"
            ])
            for sale in day_sales:
                items = sale.get("items", [])
                for item in items:
                    qty   = int(item.get("quantity", 1))
                    price = float(item.get("price", 0))
                    writer.writerow([
                        sale.get("id", ""),
                        sale.get("date", ""),
                        sale.get("time", ""),
                        sale.get("user", ""),
                        item.get("barcode", ""),
                        item.get("name", ""),
                        qty,
                        f"{price:.2f}",
                        f"{qty * price:.2f}",
                        f"{sale.get('subtotal', 0):.2f}",
                        sale.get("discount_pct", 0),
                        f"{sale.get('discount_amt', 0):.2f}",
                        sale.get("tax_pct", 0),
                        f"{sale.get('tax_amt', 0):.2f}",
                        f"{sale.get('total', 0):.2f}",
                        sale.get("promo_code", ""),
                        sale.get("payment_method", ""),
                        sale.get("status", "Completed"),
                    ])

        messagebox.showinfo("Saved", f"CSV report saved:\n{file_path}")

    def _export_pdf(self):
        """Export daily report as a formatted PDF using reportlab."""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                            Paragraph, Spacer)
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
        except ImportError:
            messagebox.showerror(
                "Missing Library",
                "reportlab is not installed.\n\nRun:  pip install reportlab\n\nThen try again."
            )
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            title="Save PDF Report",
            initialfile=f"JustB_Report_{self.feedback_date}.pdf"
        )
        if not file_path:
            return

        doc = SimpleDocTemplate(file_path, pagesize=A4,
                                leftMargin=2*cm, rightMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        story  = []

        title_style = ParagraphStyle("title", parent=styles["Heading1"],
                                     textColor=colors.HexColor("#8B5CF6"),
                                     fontSize=18, spaceAfter=4)
        sub_style   = ParagraphStyle("sub", parent=styles["Normal"],
                                     textColor=colors.HexColor("#6B6B8A"),
                                     fontSize=10, spaceAfter=12)
        head_style  = ParagraphStyle("head", parent=styles["Heading2"],
                                     textColor=colors.HexColor("#1A1035"),
                                     fontSize=13, spaceBefore=14, spaceAfter=6)

        story.append(Paragraph("JustB — Daily Sales Report", title_style))
        story.append(Paragraph(f"Date: {self.feedback_date}  |  Generated: "
                                f"{datetime.now().strftime('%H:%M:%S')}", sub_style))

        # KPI summary table
        kpi_data = [
            ["Revenue", "Transactions", "Items Sold", "Avg Sale"],
            [self.total_lbl.cget("text"),
             self._kpi_sales.cget("text"),
             self._kpi_items.cget("text"),
             self._kpi_avg.cget("text")],
        ]
        kpi_table = Table(kpi_data, colWidths=[4*cm]*4)
        kpi_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F0EDFF")),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.HexColor("#6B6B8A")),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, 0), 9),
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#FFFFFF")),
            ("FONTNAME",   (0, 1), (-1, 1), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 1), (-1, 1), 13),
            ("TEXTCOLOR",  (0, 1), (-1, 1), colors.HexColor("#8B5CF6")),
            ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
            ("BOX",        (0, 0), (-1, -1), 0.5, colors.HexColor("#E8E4F8")),
            ("INNERGRID",  (0, 0), (-1, -1), 0.5, colors.HexColor("#E8E4F8")),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(kpi_table)
        story.append(Spacer(1, 0.5*cm))

        # Today's sales detail table
        story.append(Paragraph("Today's Sales by Product", head_style))
        sales = load_json(self._sales_path())
        day_sales = [s for s in sales if s.get("date", "") == self.feedback_date]

        detail_data = [["Receipt", "Cashier", "Item", "Qty", "Price", "Line Total",
                        "Payment", "Status"]]
        for sale in day_sales:
            for item in sale.get("items", []):
                qty   = int(item.get("quantity", 1))
                price = float(item.get("price", 0))
                detail_data.append([
                    f"#{sale.get('id', '')}",
                    sale.get("user", "—"),
                    item.get("name", "")[:28],
                    str(qty),
                    f"EGP {price:.2f}",
                    f"EGP {qty*price:.2f}",
                    sale.get("payment_method", "Cash"),
                    sale.get("status", "Completed"),
                ])

        if len(detail_data) > 1:
            col_w = [1.5*cm, 2.2*cm, 5*cm, 1.2*cm, 2.2*cm, 2.5*cm, 2.2*cm, 2.2*cm]
            det_table = Table(detail_data, colWidths=col_w, repeatRows=1)
            det_table.setStyle(TableStyle([
                ("BACKGROUND",  (0, 0), (-1, 0), colors.HexColor("#8B5CF6")),
                ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
                ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE",    (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                 [colors.HexColor("#FFFFFF"), colors.HexColor("#FAF8FF")]),
                ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
                ("ALIGN",       (2, 1), (2, -1), "LEFT"),
                ("BOX",         (0, 0), (-1, -1), 0.4, colors.HexColor("#E8E4F8")),
                ("INNERGRID",   (0, 0), (-1, -1), 0.3, colors.HexColor("#E8E4F8")),
                ("TOPPADDING",    (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(det_table)
        else:
            story.append(Paragraph("No sales recorded for this date.", styles["Normal"]))

        # Best sellers section
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph("Best Selling Products", head_style))
        best_sellers = self._get_best_sellers_data()
        if best_sellers:
            bs_data = [["Rank", "Product", "Qty Sold", "Revenue"]]
            for idx, item in enumerate(best_sellers):
                bs_data.append([
                    f"#{idx+1}", item["name"],
                    str(item["qty"]),
                    f"EGP {item['revenue']:,.2f}"
                ])
            bs_table = Table(bs_data, colWidths=[1.5*cm, 9*cm, 2.5*cm, 3.5*cm],
                             repeatRows=1)
            bs_table.setStyle(TableStyle([
                ("BACKGROUND",  (0, 0), (-1, 0), colors.HexColor("#1BBFBF")),
                ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
                ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE",    (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                 [colors.HexColor("#FFFFFF"), colors.HexColor("#F0FFFF")]),
                ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
                ("ALIGN",       (1, 1), (1, -1), "LEFT"),
                ("BOX",         (0, 0), (-1, -1), 0.4, colors.HexColor("#E8E4F8")),
                ("INNERGRID",   (0, 0), (-1, -1), 0.3, colors.HexColor("#E8E4F8")),
                ("TOPPADDING",    (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(bs_table)
        else:
            story.append(Paragraph("No best-seller data for selected range.", styles["Normal"]))

        story.append(Spacer(1, 1*cm))
        story.append(Paragraph("justb-eg.com  ·  Stationery & Gifts",
                                ParagraphStyle("footer", parent=styles["Normal"],
                                               textColor=colors.HexColor("#A8A8C0"),
                                               fontSize=8, alignment=1)))

        doc.build(story)
        messagebox.showinfo("PDF Saved", f"PDF report saved:\n{file_path}")