"""
promo_management.py  —  JustB Retail Management System
=======================================================
Redesigned to match the JustB bright luxury design system.
Dynamic features:
  • Animated stat cards (total codes, total uses available, avg discount)
  • Live colour-coded table rows (high discount = pink, medium = orange, low = teal)
  • Polished form panel with focus ring animations
  • QR export with success animation
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from utils.helpers import load_json, save_json
import os

try:
    import qrcode
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

# ══════════════════════════════════════════════════════════════════════════════
#  Design tokens
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

FONT_HEAD    = ("Georgia",   13, "bold")
FONT_LABEL   = ("Segoe UI",  10)
FONT_LABEL_B = ("Segoe UI",  10, "bold")
FONT_ENTRY   = ("Segoe UI",  11)
FONT_BTN     = ("Segoe UI",  10, "bold")
FONT_SMALL   = ("Segoe UI",   9)
FONT_SECTION = ("Segoe UI",   8, "bold")
FONT_STAT    = ("Georgia",   20, "bold")
FONT_STAT_LB = ("Segoe UI",   9)


def _btn(parent, text, command, bg, hover, fg="#FFFFFF",
         font=FONT_BTN, padx=16, pady=8):
    b = tk.Label(parent, text=text, font=font,
                 bg=bg, fg=fg, cursor="hand2",
                 relief="flat", padx=padx, pady=pady)
    b.bind("<Button-1>", lambda e: command())
    b.bind("<Enter>",    lambda e: b.config(bg=hover))
    b.bind("<Leave>",    lambda e: b.config(bg=bg))
    return b


def _entry(parent, width=22, font=FONT_ENTRY):
    return tk.Entry(
        parent, font=font, width=width,
        bg=C["bg_input"], fg=C["text_dark"],
        insertbackground=C["purple"],
        relief="flat",
        highlightthickness=2,
        highlightbackground=C["border"],
        highlightcolor=C["purple"],
    )


# ══════════════════════════════════════════════════════════════════════════════

class PromoManagementScreen:
    def __init__(self, root, frame_parent=None, data_dir=None):
        self.root      = root
        self.data_dir  = data_dir
        self._all_promos = []

        self.frame = tk.Frame(frame_parent or root, bg=C["bg_root"])
        self.frame.pack(fill="both", expand=True)

        self._build_ui()
        self.load_codes()

    def _promos_path(self):
        return os.path.join(self.data_dir, "promo_codes.json")

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
        tk.Label(hdr, text="Promotion Management",
                 font=FONT_HEAD, bg=C["bg_header"],
                 fg=C["text_dark"]).pack(side="left", padx=(6, 0), pady=10)

        # ── Stat cards ────────────────────────────────────────────────────────
        stats_bar = tk.Frame(self.frame, bg=C["bg_root"])
        stats_bar.pack(fill="x", padx=14, pady=(10, 0))
        for i in range(3):
            stats_bar.columnconfigure(i, weight=1)

        self._stat_codes   = self._stat_card(stats_bar, "ACTIVE CODES",    "0", C["pink"],   0)
        self._stat_uses    = self._stat_card(stats_bar, "USES REMAINING",   "0", C["teal"],   1)
        self._stat_avg_disc= self._stat_card(stats_bar, "AVG DISCOUNT",     "0%", C["orange"], 2)

        # ── Body split: left (table) + right (form) ───────────────────────────
        body = tk.Frame(self.frame, bg=C["bg_root"])
        body.pack(fill="both", expand=True, padx=14, pady=10)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2, minsize=280)
        body.rowconfigure(0, weight=1)

        # ── LEFT: Promo codes table ───────────────────────────────────────────
        tree_card = tk.Frame(body, bg=C["bg_card"],
                             highlightthickness=1,
                             highlightbackground=C["border"])
        tree_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        tree_card.rowconfigure(1, weight=1)
        tree_card.columnconfigure(0, weight=1)

        # Sub-header
        ch = tk.Frame(tree_card, bg=C["bg_panel"], padx=14, pady=10)
        ch.grid(row=0, column=0, columnspan=2, sticky="ew")
        dot_f = tk.Frame(ch, bg=C["bg_panel"])
        dot_f.pack(side="left")
        for col in BRAND_COLORS:
            tk.Label(dot_f, text="●", font=("Segoe UI", 8),
                     bg=C["bg_panel"], fg=col).pack(side="left", padx=1)
        tk.Label(ch, text="  PROMO CODES — click to select",
                 font=FONT_SECTION, bg=C["bg_panel"],
                 fg=C["text_mid"]).pack(side="left")
        self._count_lbl = tk.Label(ch, text="0 codes",
                                    font=FONT_SMALL,
                                    bg=C["bg_panel"], fg=C["purple"])
        self._count_lbl.pack(side="right")

        # Style
        ts = ttk.Style()
        ts.configure("PM2.Treeview",
                     background=C["bg_card"],
                     foreground=C["text_dark"],
                     fieldbackground=C["bg_card"],
                     rowheight=38,
                     font=("Segoe UI", 10),
                     borderwidth=0, relief="flat")
        ts.configure("PM2.Treeview.Heading",
                     background=C["bg_panel"],
                     foreground=C["text_mid"],
                     font=("Segoe UI", 9, "bold"),
                     relief="flat", borderwidth=0)
        ts.map("PM2.Treeview",
               background=[("selected", C["bg_panel"])],
               foreground=[("selected", C["purple"])])
        ts.layout("PM2.Treeview",
                  [('Treeview.treearea', {'sticky': 'nswe'})])

        cols = ("Code", "Discount %", "Uses Left", "Max Uses", "Level")
        self.tree = ttk.Treeview(tree_card, columns=cols,
                                  show="headings", selectmode="browse",
                                  style="PM2.Treeview")
        cw = {"Code": 120, "Discount %": 90, "Uses Left": 80,
              "Max Uses": 80, "Level": 90}
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center",
                              width=cw[col], minwidth=60)

        # Tag colours for discount tiers
        self.tree.tag_configure("high",     foreground=C["pink"])
        self.tree.tag_configure("high_odd", background=C["bg_row_alt"], foreground=C["pink"])
        self.tree.tag_configure("mid",      foreground=C["orange"])
        self.tree.tag_configure("mid_odd",  background=C["bg_row_alt"], foreground=C["orange"])
        self.tree.tag_configure("low",      foreground=C["teal"])
        self.tree.tag_configure("low_odd",  background=C["bg_row_alt"], foreground=C["teal"])

        vsb = ttk.Scrollbar(tree_card, orient="vertical",
                             command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=1, column=0, sticky="nsew")
        vsb.grid(row=1, column=1, sticky="ns")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # Action buttons under table
        btns = tk.Frame(tree_card, bg=C["bg_card"], padx=10, pady=10)
        btns.grid(row=2, column=0, columnspan=2, sticky="ew")
        _btn(btns, "🗑  Delete Selected",
             self.delete_code,
             C["danger"], "#B91C1C").pack(side="left")
        _btn(btns, "📷  Export QR",
             self.generate_qr,
             C["purple"], C["purple_dk"]).pack(side="left", padx=(8, 0))
        _btn(btns, "⟳  Refresh",
             self.load_codes,
             C["bg_panel"], C["border_acc"],
             fg=C["text_mid"]).pack(side="right")

        # ── RIGHT: Form card ──────────────────────────────────────────────────
        form_card = tk.Frame(body, bg=C["bg_card"],
                             highlightthickness=1,
                             highlightbackground=C["border"])
        form_card.grid(row=0, column=1, sticky="nsew")

        tk.Frame(form_card, bg=C["pink"], height=4).pack(fill="x")

        fhdr = tk.Frame(form_card, bg=C["bg_panel"], padx=14, pady=10)
        fhdr.pack(fill="x")
        tk.Label(fhdr, text="NEW PROMO CODE",
                 font=FONT_SECTION, bg=C["bg_panel"],
                 fg=C["text_mid"]).pack(side="left")

        inner = tk.Frame(form_card, bg=C["bg_card"], padx=24, pady=20)
        inner.pack(fill="both", expand=True)
        inner.columnconfigure(1, weight=1)

        def _lbl(text, row):
            tk.Label(inner, text=text, font=FONT_LABEL_B,
                     bg=C["bg_card"], fg=C["text_mid"]).grid(
                         row=row, column=0, sticky="w", pady=6, padx=(0, 14))

        self.code_entry     = _entry(inner)
        self.discount_entry = _entry(inner)
        self.max_entry      = _entry(inner)

        _lbl("Promo Code",  0)
        _lbl("Discount %",  1)
        _lbl("Max Uses",    2)

        self.code_entry.grid    (row=0, column=1, sticky="ew", ipady=7, pady=6)
        self.discount_entry.grid(row=1, column=1, sticky="ew", ipady=7, pady=6)
        self.max_entry.grid     (row=2, column=1, sticky="ew", ipady=7, pady=6)

        # Discount tier hint
        hint = tk.Frame(inner, bg=C["bg_card"])
        hint.grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 12))
        for label, col in [("< 15%: Low", C["teal"]),
                            ("15–30%: Mid", C["orange"]),
                            ("> 30%: High", C["pink"])]:
            tk.Label(hint, text="● " + label, font=FONT_SMALL,
                     bg=C["bg_card"], fg=col).pack(side="left", padx=(0, 12))

        # Status
        self._form_status = tk.Label(inner, text="", font=FONT_SMALL,
                                      bg=C["bg_card"], fg=C["success"])
        self._form_status.grid(row=4, column=0, columnspan=2,
                               sticky="w", pady=(4, 0))

        # Save button
        _btn(inner, "＋  Add Promo Code",
             self.add_code,
             C["pink"], "#D0457F",
             padx=20, pady=11).grid(
                 row=5, column=0, columnspan=2,
                 sticky="ew", pady=(14, 0))

        # Disclaimer
        tk.Label(form_card,
                 text="Select a code in the table to pre-fill this form",
                 font=FONT_SMALL, bg=C["bg_card"], fg=C["text_light"]
                 ).pack(pady=(0, 14))

    # ── Stat card helper ──────────────────────────────────────────────────────

    def _stat_card(self, parent, label, value, accent, col):
        card = tk.Frame(parent, bg=C["bg_card"],
                        highlightthickness=1,
                        highlightbackground=C["border"],
                        padx=16, pady=14)
        card.grid(row=0, column=col, sticky="ew",
                  padx=(0 if col == 0 else 8, 0))
        tk.Frame(card, bg=accent, height=3).pack(fill="x", pady=(0, 8))
        tk.Label(card, text=label, font=FONT_STAT_LB,
                 bg=C["bg_card"], fg=C["text_light"]).pack(anchor="w")
        val_lbl = tk.Label(card, text=value, font=FONT_STAT,
                           bg=C["bg_card"], fg=accent)
        val_lbl.pack(anchor="w")
        return val_lbl

    def _animate_counter(self, label, target, suffix="", steps=18):
        try:
            raw = label.cget("text").replace(suffix, "").replace(",", "").strip() or "0"
            current = int(float(raw))
        except Exception:
            current = 0
        delta = target - current

        def _step(i=0):
            if i > steps:
                label.config(text=f"{target}{suffix}")
                return
            label.config(text=f"{int(current + delta * i/steps)}{suffix}")
            label.after(16, lambda: _step(i + 1))

        _step()

    # ── Data ──────────────────────────────────────────────────────────────────

    def load_codes(self):
        self._all_promos = load_json(self._promos_path())
        self._refresh_tree()

    def _refresh_tree(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        total_uses = 0
        total_disc = 0

        for idx, p in enumerate(self._all_promos):
            disc = float(p.get("discount_percentage", 0))
            uses = int(p.get("uses_left", 0))
            maxu = int(p.get("max_uses", uses))
            total_uses += uses
            total_disc += disc

            if disc > 30:
                level, tag_base = "🔥 High", "high"
            elif disc >= 15:
                level, tag_base = "◆ Mid", "mid"
            else:
                level, tag_base = "◇ Low", "low"

            tag = tag_base + ("_odd" if idx % 2 else "")
            self.tree.insert("", "end", tags=(tag,),
                             values=(p["code"], f"{disc:.0f}%",
                                     uses, maxu, level))

        n = len(self._all_promos)
        avg = (total_disc / n) if n > 0 else 0

        self._animate_counter(self._stat_codes,    n)
        self._animate_counter(self._stat_uses,     total_uses)
        self._animate_counter(self._stat_avg_disc, int(avg), suffix="%")
        self._count_lbl.config(
            text=f"{n} code{'s' if n != 1 else ''}")

    def _on_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0])["values"]
        self.code_entry.delete(0, tk.END)
        self.code_entry.insert(0, vals[0])
        self.discount_entry.delete(0, tk.END)
        self.discount_entry.insert(0, str(vals[1]).replace("%", ""))
        self.max_entry.delete(0, tk.END)
        self.max_entry.insert(0, vals[3])

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def add_code(self):
        code = self.code_entry.get().strip().upper()
        disc_s = self.discount_entry.get().strip()
        max_s  = self.max_entry.get().strip()

        if not code:
            self._set_status("Promo code is required.", error=True); return
        try:
            disc = float(disc_s)
            assert 0 < disc <= 100
        except Exception:
            self._set_status("Discount must be a number between 1 and 100.", error=True); return
        try:
            maxu = int(max_s)
            assert maxu > 0
        except Exception:
            self._set_status("Max uses must be a positive integer.", error=True); return

        promos = load_json(self._promos_path())
        if any(p["code"].upper() == code for p in promos):
            self._set_status(f"Code '{code}' already exists.", error=True); return

        promos.append({"code": code, "discount_percentage": disc,
                        "max_uses": maxu, "uses_left": maxu})
        save_json(self._promos_path(), promos)

        self.code_entry.delete(0, tk.END)
        self.discount_entry.delete(0, tk.END)
        self.max_entry.delete(0, tk.END)
        self._set_status(f"'{code}' added successfully!")
        self.load_codes()

    def delete_code(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select Code", "Select a promo code first.")
            return
        code = self.tree.item(sel[0])["values"][0]
        if not messagebox.askyesno("Delete Code",
                                   f"Delete promo code '{code}'?"):
            return
        promos = load_json(self._promos_path())
        promos = [p for p in promos if p["code"] != code]
        save_json(self._promos_path(), promos)
        self._set_status(f"'{code}' deleted.")
        self.load_codes()

    def generate_qr(self):
        if not QR_AVAILABLE:
            messagebox.showerror("Missing Library",
                "qrcode library not installed.\nRun: pip install qrcode")
            return
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select Code", "Select a promo code first.")
            return
        code = self.tree.item(sel[0])["values"][0]
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Files", "*.png")],
            title="Save QR Code",
            initialfile=f"{code}_qr.png"
        )
        if not file_path:
            return
        qr_img = qrcode.make(code)
        qr_img.save(file_path)
        self._set_status(f"QR code saved for '{code}'!")
        messagebox.showinfo("Saved", f"QR Code saved:\n{file_path}")

    def _set_status(self, msg, error=False):
        self._form_status.config(
            text=msg, fg=C["danger"] if error else C["success"])
        self.frame.after(4000, lambda: self._form_status.config(text=""))