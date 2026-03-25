"""
daily_feedback.py  —  JustB Retail Management System
=====================================================
Redesigned with JustB bright luxury theme.
Dynamic features:
  • Animated revenue counter on load
  • Mini bar chart drawn on a Canvas (top 5 products by revenue)
  • Colour-coded rank badges in the table (gold / silver / bronze / …)
  • Live date picker with refresh pulse
  • Print report button
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.simpledialog import askstring
from utils.helpers import load_json, get_today_date
import os

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
}
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


def _btn(parent, text, command, bg, hover, fg="#FFFFFF",
         font=FONT_BTN, padx=16, pady=8):
    b = tk.Label(parent, text=text, font=font,
                 bg=bg, fg=fg, cursor="hand2",
                 relief="flat", padx=padx, pady=pady)
    b.bind("<Button-1>", lambda e: command())
    b.bind("<Enter>",    lambda e: b.config(bg=hover))
    b.bind("<Leave>",    lambda e: b.config(bg=bg))
    return b


# ══════════════════════════════════════════════════════════════════════════════

class ReceiptDatabaseScreen:
    def __init__(self, root, data_dir=None, frame_parent=None, admin=False):
        self.root      = root
        self.data_dir  = data_dir
        self.admin     = admin
        self.feedback_date = get_today_date()

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
        tk.Label(hdr, text="Daily Feedback",
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
        tk.Label(ch, text="  PRODUCT PERFORMANCE",
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

        # ── RIGHT: Totals + mini bar chart ────────────────────────────────────
        right = tk.Frame(body, bg=C["bg_root"])
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

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
        chart_card.grid(row=1, column=0, sticky="nsew")
        chart_card.rowconfigure(1, weight=1)
        chart_card.columnconfigure(0, weight=1)

        ch2 = tk.Frame(chart_card, bg=C["bg_panel"], padx=14, pady=10)
        ch2.grid(row=0, column=0, sticky="ew")
        tk.Label(ch2, text="TOP 5  BY REVENUE",
                 font=FONT_SECTION, bg=C["bg_panel"],
                 fg=C["text_mid"]).pack(side="left")

        self.chart_canvas = tk.Canvas(chart_card, bg=C["bg_card"],
                                       highlightthickness=0)
        self.chart_canvas.grid(row=1, column=0, sticky="nsew",
                               padx=12, pady=12)

        # Print button
        if self.admin:
            _btn(right, "🖨  Print Report",
                 self.print_report,
                 C["orange"], "#E05F00",
                 padx=0, pady=10).grid(
                     row=2, column=0, sticky="ew", pady=(8, 0))

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
                               text="No data for this date",
                               font=FONT_SMALL, fill=C["text_light"])
            return

        max_rev = max(x["revenue"] for x in top5)
        if max_rev == 0:
            return

        pad_l, pad_r = 12, 50
        pad_t, pad_b = 10, 10
        bar_h    = max(14, (H - pad_t - pad_b - (len(top5) - 1) * 6) // len(top5))
        usable_w = W - pad_l - pad_r

        def _draw_bar(idx, item, pct):
            y = pad_t + idx * (bar_h + 6)
            bar_w = int(usable_w * pct)
            col = BRAND_COLORS[idx % len(BRAND_COLORS)]

            # Background track
            canvas.create_rectangle(pad_l, y, pad_l + usable_w, y + bar_h,
                                     fill=C["bg_panel"], outline="")
            # Animate bar width
            def _anim(w=0):
                if w > bar_w:
                    # Value label
                    canvas.create_text(pad_l + bar_w + 6, y + bar_h // 2,
                                       text=f"EGP {item['revenue']:,.0f}",
                                       font=FONT_SMALL, fill=C["text_mid"],
                                       anchor="w")
                    return
                canvas.delete(f"bar{idx}")
                canvas.create_rectangle(pad_l, y, pad_l + w, y + bar_h,
                                         fill=col, outline="",
                                         tags=(f"bar{idx}",))
                canvas.after(8, lambda: _anim(w + max(1, bar_w // 18)))

            _anim()

            # Label (truncate at 14 chars)
            name = item["name"][:14] + ("…" if len(item["name"]) > 14 else "")
            canvas.create_text(pad_l, y - 2,
                               text=name, font=FONT_SMALL,
                               fill=C["text_mid"], anchor="sw")

        for i, item in enumerate(top5):
            _draw_bar(i, item, item["revenue"] / max_rev)

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
        for i in self.tree.get_children():
            self.tree.delete(i)

        sales = load_json(self._sales_path())

        total_revenue  = 0.0
        total_sales    = 0
        total_items    = 0
        product_summary = {}

        for sale in sales:
            if sale.get("date", "") == self.feedback_date:
                total_sales   += 1
                total_revenue += float(sale.get("total", 0))
                for item in sale.get("items", []):
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
                    total_items += qty

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
            rank = idx  # 0=gold, 1=silver, 2=bronze, …
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

    # ── Print ─────────────────────────────────────────────────────────────────

    def print_report(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            title="Save Report As",
            initialfile=f"JustB_Report_{self.feedback_date}.txt"
        )
        if not file_path:
            return

        lines = [
            "=" * 46,
            f"  JustB Daily Report — {self.feedback_date}",
            "=" * 46,
            f"  Revenue:     {self.total_lbl.cget('text')}",
            f"  Transactions:{self._kpi_sales.cget('text')}",
            f"  Items Sold:  {self._kpi_items.cget('text')}",
            f"  Avg Sale:    {self._kpi_avg.cget('text')}",
            "-" * 46,
            f"  {'Rank':<6} {'Product':<24} {'Qty':>5}  {'Revenue':>12}",
            "-" * 46,
        ]
        for item in self.tree.get_children():
            v = self.tree.item(item)["values"]
            lines.append(f"  {str(v[0]):<6} {str(v[1]):<24} {str(v[2]):>5}  {str(v[3]):>12}")

        lines += ["-" * 46, "  justb-eg.com", "=" * 46]

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        messagebox.showinfo("Report Saved", f"Report saved:\n{file_path}")