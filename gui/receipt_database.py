"""
receipt_database.py  —  JustB Retail Management System
======================================================
Receipt Database - Browse individual transactions with hover previews
Dynamic features:
  • Live receipt list with time-sorted transactions
  • Hover to preview formatted receipt
  • Filter by date
  • Search receipts by ID, amount, product name, or receipt barcode code (RCPT-XXXXXX)
  • Export receipt data
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from tkinter.simpledialog import askstring
from utils.helpers import load_json, get_today_date
import os
from datetime import datetime, timedelta

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
FONT_RECEIPT = ("Courier New", 9)
FONT_BTN     = ("Segoe UI",  10, "bold")
FONT_SMALL   = ("Segoe UI",   9)
FONT_SECTION = ("Segoe UI",   8, "bold")


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
        self.root       = root
        self.data_dir   = data_dir
        self.admin      = admin
        self.view_date  = get_today_date()
        self.current_hover_receipt = None
        self.preview_window = None

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

        # Title with dots
        title_frame = tk.Frame(hdr, bg=C["bg_header"])
        title_frame.pack(side="left", padx=(16, 0), pady=10)
        for col in BRAND_COLORS[:3]:
            tk.Label(title_frame, text="●", font=("Segoe UI", 9),
                     bg=C["bg_header"], fg=col).pack(side="left", padx=1)
        tk.Label(hdr, text="Receipt Database",
                 font=FONT_HEAD, bg=C["bg_header"],
                 fg=C["text_dark"]).pack(side="left", padx=(6, 0), pady=10)

        # Date picker on right
        date_frame = tk.Frame(hdr, bg=C["bg_header"])
        date_frame.pack(side="right", padx=16, pady=8)

        tk.Label(date_frame, text="Filter date:",
                 font=FONT_SMALL, bg=C["bg_header"],
                 fg=C["text_light"]).pack(side="left", padx=(0, 8))

        self.date_lbl = tk.Label(date_frame,
                                  text=self.view_date,
                                  font=FONT_LABEL_B,
                                  bg=C["teal"], fg="#FFFFFF",
                                  padx=12, pady=5, cursor="hand2")
        self.date_lbl.pack(side="left")
        self.date_lbl.bind("<Button-1>", lambda e: self._pick_date())
        self.date_lbl.bind("<Enter>",    lambda e: self.date_lbl.config(bg="#159F9F"))
        self.date_lbl.bind("<Leave>",    lambda e: self.date_lbl.config(bg=C["teal"]))

        if self.admin:
            _btn(date_frame, "⟳  Refresh",
                 self.load_data,
                 C["orange"], "#E05F00",
                 padx=12, pady=5).pack(side="left", padx=(8, 0))

        # Print Report button
        _btn(date_frame, "🖨  Print Report",
             self._open_print_dialog,
             C["purple"], C["purple_dk"],
             padx=12, pady=5).pack(side="left", padx=(8, 0))

        # ── Search bar ─────────────────────────────────────────────────────────
        search_frame = tk.Frame(self.frame, bg=C["bg_root"])
        search_frame.pack(fill="x", padx=14, pady=(8, 0))

        tk.Label(search_frame, text="Search:",
                 font=FONT_SMALL, bg=C["bg_root"],
                 fg=C["text_mid"]).pack(side="left", padx=(0, 8))

        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self._filter_receipts())
        search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                                font=FONT_SMALL, bg=C["bg_input"],
                                fg=C["text_dark"], width=36,
                                relief="solid", borderwidth=1)
        search_entry.pack(side="left", padx=(0, 8))

        # Search hint label
        tk.Label(search_frame,
                 text="by ID · amount · product name · barcode code (RCPT-000001)",
                 font=("Segoe UI", 8), bg=C["bg_root"],
                 fg=C["text_light"]).pack(side="left")

        # ── Main content: Receipts list + Preview ─────────────────────────────
        body = tk.Frame(self.frame, bg=C["bg_root"])
        body.pack(fill="both", expand=True, padx=14, pady=10)
        body.columnconfigure(0, weight=2)
        body.columnconfigure(1, weight=1, minsize=320)
        body.rowconfigure(0, weight=1)

        # LEFT: Receipts list
        list_card = tk.Frame(body, bg=C["bg_card"],
                             highlightthickness=1,
                             highlightbackground=C["border"])
        list_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        list_card.rowconfigure(1, weight=1)
        list_card.columnconfigure(0, weight=1)

        # List header
        list_hdr = tk.Frame(list_card, bg=C["bg_panel"], padx=14, pady=10)
        list_hdr.grid(row=0, column=0, sticky="ew")
        tk.Label(list_hdr, text="📋  RECEIPTS",
                 font=FONT_SECTION, bg=C["bg_panel"],
                 fg=C["text_mid"]).pack(side="left")

        self.results_lbl = tk.Label(list_hdr, text="",
                                     font=FONT_SMALL,
                                     bg=C["bg_panel"], fg=C["purple"])
        self.results_lbl.pack(side="right")

        # Receipts treeview
        ts = ttk.Style()
        ts.configure("RDB.Treeview",
                     background=C["bg_card"],
                     foreground=C["text_dark"],
                     fieldbackground=C["bg_card"],
                     rowheight=44,
                     font=("Segoe UI", 10),
                     borderwidth=0, relief="flat")
        ts.configure("RDB.Treeview.Heading",
                     background=C["bg_panel"],
                     foreground=C["text_mid"],
                     font=("Segoe UI", 9, "bold"),
                     relief="flat", borderwidth=0)
        ts.map("RDB.Treeview",
               background=[("selected", C["bg_panel"])],
               foreground=[("selected", C["teal"])])
        ts.layout("RDB.Treeview",
                  [('Treeview.treearea', {'sticky': 'nswe'})])

        cols = ("ID", "Time", "Items", "Total")
        self.tree = ttk.Treeview(list_card, columns=cols,
                                  show="headings", selectmode="browse",
                                  style="RDB.Treeview")
        cw = {"ID": 60, "Time": 70, "Items": 50, "Total": 100}
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=cw[col], minwidth=40)

        # Hover preview binding
        self.tree.bind("<Motion>", self._on_tree_hover)
        self.tree.bind("<Leave>",  self._hide_preview)

        vsb = ttk.Scrollbar(list_card, orient="vertical",
                             command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=(0, 1))
        vsb.grid(row=1, column=1, sticky="ns")

        # RIGHT: Receipt preview panel
        preview_card = tk.Frame(body, bg=C["bg_card"],
                                highlightthickness=1,
                                highlightbackground=C["border"])
        preview_card.grid(row=0, column=1, sticky="nsew")
        preview_card.rowconfigure(1, weight=1)
        preview_card.columnconfigure(0, weight=1)

        prev_hdr = tk.Frame(preview_card, bg=C["bg_panel"], padx=14, pady=10)
        prev_hdr.grid(row=0, column=0, sticky="ew")
        tk.Label(prev_hdr, text="👁  PREVIEW",
                 font=FONT_SECTION, bg=C["bg_panel"],
                 fg=C["text_mid"]).pack(side="left")

        # Preview text area
        self.preview_text = tk.Text(preview_card, bg=C["bg_root"],
                                     fg=C["text_dark"],
                                     font=("Courier New", 9),
                                     relief="flat", borderwidth=0,
                                     padx=10, pady=10)
        self.preview_text.grid(row=1, column=0, sticky="nsew")
        self.preview_text.config(state="disabled")

        # Footer
        tk.Label(self.frame,
                 text="justb-eg.com  ·  Stationery & Gifts",
                 font=("Segoe UI", 8),
                 bg=C["bg_root"], fg=C["text_light"]).pack(side="bottom", pady=4)

    # ── Receipt hover preview ────────────────────────────────────────────────

    def _on_tree_hover(self, event):
        """Show receipt preview when hovering over a receipt."""
        item = self.tree.identify_row(event.y)
        if not item:
            return

        values = self.tree.item(item)["values"]
        receipt_id = values[0]

        # Only update if hovering over a different receipt
        if self.current_hover_receipt == receipt_id:
            return

        self.current_hover_receipt = receipt_id
        self._update_preview(receipt_id)

    def _hide_preview(self, event):
        """Clear preview when mouse leaves tree."""
        self.current_hover_receipt = None
        self.preview_text.config(state="normal")
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.config(state="disabled")

    def _update_preview(self, receipt_id):
        """Update preview panel with receipt text info."""
        if not self.receipts_data:
            return

        receipt = None
        for r in self.receipts_data:
            if str(r.get("id", "")) == str(receipt_id):
                receipt = r
                break

        if not receipt:
            return

        # Format receipt as text
        preview_text = self._format_receipt_text(receipt)

        self.preview_text.config(state="normal")
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.insert(1.0, preview_text)
        self.preview_text.config(state="disabled")

    def _format_receipt_text(self, receipt):
        """Generate a text-formatted receipt."""
        lines = []
        lines.append("=" * 42)
        lines.append("JustB - Stationery & Gifts".center(42))
        lines.append("=" * 42)
        lines.append("")

        receipt_id = receipt.get("id", "N/A")
        receipt_time = receipt.get("time", receipt.get("date", "N/A"))
        cashier = receipt.get("user", "—")

        lines.append(f"Receipt #   : {receipt_id}")
        lines.append(f"Date        : {receipt.get('date', 'N/A')}")
        lines.append(f"Time        : {receipt_time}")
        lines.append(f"Cashier     : {cashier}")
        lines.append("-" * 42)
        lines.append("")

        # Items
        items = receipt.get("items", [])
        if items:
            lines.append("ITEMS:")
            lines.append("-" * 42)
            for item in items:
                name = item.get("name", "?")
                qty = item.get("quantity", 1)
                price = float(item.get("price", 0))
                subtotal = qty * price
                lines.append(f"  {name}")
                lines.append(f"    Qty: {qty}  @  EGP {price:.2f}  =  EGP {subtotal:.2f}")
            lines.append("-" * 42)
        else:
            lines.append("No items in receipt")
            lines.append("-" * 42)

        lines.append("")

        # Totals
        subtotal = receipt.get("subtotal", 0)
        discount_amt = receipt.get("discount_amt", 0)
        discount_pct = receipt.get("discount_pct", 0)
        total = receipt.get("total", 0)

        lines.append(f"Subtotal    : EGP {subtotal:.2f}")
        if discount_amt > 0:
            lines.append(f"Discount ({discount_pct}%) : -EGP {discount_amt:.2f}")
        lines.append("=" * 42)
        lines.append(f"TOTAL       : EGP {total:.2f}")
        lines.append("=" * 42)

        # Promo
        promo = receipt.get("promo_code", "")
        if promo:
            lines.append(f"Promo Code  : {promo}")

        lines.append("")
        lines.append("Thank you for shopping at JustB!")
        lines.append("justb-eg.com")

        return "\n".join(lines)

    # ── Search / Filter ───────────────────────────────────────────────────────

    def _filter_receipts(self):
        """
        Filter receipts by:
          - Receipt ID (numeric)
          - Total amount
          - Product name (any item in the receipt)
          - Receipt barcode code e.g. 'RCPT-000001' or just '000001'
        """
        search_term = self.search_var.get().lower().strip()

        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not search_term:
            self._populate_receipts(self.receipts_data)
            return

        # Strip RCPT- prefix so typing either form works
        code_term = search_term
        if code_term.startswith("rcpt-"):
            code_term = code_term[5:]   # e.g. "000001"

        filtered = []
        for receipt in self.receipts_data:
            receipt_id  = str(receipt.get("id", "")).lower()
            total       = str(receipt.get("total", "")).lower()
            rcpt_code   = f"rcpt-{receipt.get('id', 0):06d}"   # e.g. rcpt-000001

            # Check product names inside the receipt
            items = receipt.get("items", [])
            product_names = [str(item.get("name", "")).lower() for item in items]
            product_match = any(search_term in name for name in product_names)

            if (search_term in receipt_id
                    or search_term in total
                    or search_term in rcpt_code
                    or code_term   in receipt_id
                    or product_match):
                filtered.append(receipt)

        self._populate_receipts(filtered)

    # ── Date picker ───────────────────────────────────────────────────────────

    def _pick_date(self):
        """Open date picker dialog."""
        new_date = askstring("Select Date",
                             "Enter date (YYYY-MM-DD):",
                             initialvalue=self.view_date,
                             parent=self.frame)
        if new_date:
            self.view_date = new_date
            self.date_lbl.config(text=self.view_date)
            self.search_var.set("")  # Clear search
            self.load_data()

    # ══════════════════════════════════════════════════════════════════════════
    #  Data Loading
    # ══════════════════════════════════════════════════════════════════════════

    def load_data(self):
        """Load receipts from sales.json and populate tree, consolidating duplicates."""
        sales = load_json(self._sales_path())
        self.receipts_data = []
        receipt_map = {}  # To consolidate duplicate receipt IDs

        for sale in sales:
            if sale.get("date", "") == self.view_date:
                receipt_id = sale.get("id", "?")

                # If we already have this receipt ID, consolidate items
                if receipt_id in receipt_map:
                    # Merge items and recalculate totals
                    existing = receipt_map[receipt_id]
                    existing["items"].extend(sale.get("items", []))
                    existing["subtotal"] = existing.get("subtotal", 0) + sale.get("subtotal", 0)
                    existing["discount_amt"] = existing.get("discount_amt", 0) + sale.get("discount_amt", 0)
                    existing["total"] = existing.get("total", 0) + sale.get("total", 0)
                else:
                    # New receipt ID
                    receipt_dict = {
                        "id": receipt_id,
                        "date": sale.get("date", ""),
                        "time": sale.get("time", sale.get("date", "")),
                        "items": sale.get("items", []),
                        "total": sale.get("total", 0),
                        "subtotal": sale.get("subtotal", 0),
                        "discount_amt": sale.get("discount_amt", 0),
                        "discount_pct": sale.get("discount_pct", 0),
                        "user": sale.get("user", "—"),
                        "promo_code": sale.get("promo_code", ""),
                    }
                    receipt_map[receipt_id] = receipt_dict

        # Convert map to list and sort by ID descending
        self.receipts_data = list(receipt_map.values())
        self.receipts_data.sort(key=lambda x: x["id"] if isinstance(x["id"], int) else 0, reverse=True)

        # Clear search and populate
        self.search_var.set("")
        self._populate_receipts(self.receipts_data)
        self._hide_preview(None)

    def _populate_receipts(self, receipts):
        """Populate tree with receipt list - one row per RECEIPT, not per item."""
        # Clear tree first to prevent duplicates
        for item in self.tree.get_children():
            self.tree.delete(item)

        for r in receipts:
            receipt_id  = r["id"]
            time_str    = r["time"]
            items_count = sum(int(item.get("quantity", 1)) for item in r["items"])
            total       = r["total"]

            self.tree.insert("", "end",
                             values=(receipt_id,
                                     time_str,
                                     items_count,
                                     f"EGP {total:,.2f}"))

        # Update results counter
        count = len(receipts)
        self.results_lbl.config(
            text=f"{count} receipt{'s' if count != 1 else ''}")

    # ══════════════════════════════════════════════════════════════════════════
    #  Print Report
    # ══════════════════════════════════════════════════════════════════════════

    def _open_print_dialog(self):
        """Open dialog to select date range and print method."""
        dialog = tk.Toplevel(self.frame)
        dialog.title("Print Report")
        dialog.geometry("400x300")
        dialog.transient(self.frame)
        dialog.resizable(False, False)

        # Center the dialog
        dialog.grab_set()

        # Main frame
        main = tk.Frame(dialog, bg=C["bg_root"], padx=20, pady=20)
        main.pack(fill="both", expand=True)

        tk.Label(main, text="Print Report", font=FONT_HEAD,
                bg=C["bg_root"], fg=C["text_dark"]).pack(anchor="w", pady=(0, 20))

        # Date range section
        tk.Label(main, text="Report Date Range", font=FONT_SECTION,
                bg=C["bg_root"], fg=C["text_mid"]).pack(anchor="w", pady=(0, 10))

        date_frame = tk.Frame(main, bg=C["bg_root"])
        date_frame.pack(fill="x", pady=(0, 20))

        tk.Label(date_frame, text="From:", font=FONT_LABEL,
                bg=C["bg_root"], fg=C["text_dark"]).pack(side="left", padx=(0, 8))
        self.from_date_entry = tk.Entry(date_frame, font=FONT_SMALL, width=15,
                                        relief="solid", borderwidth=1)
        self.from_date_entry.pack(side="left", padx=(0, 16))
        self.from_date_entry.insert(0, get_today_date())

        tk.Label(date_frame, text="To:", font=FONT_LABEL,
                bg=C["bg_root"], fg=C["text_dark"]).pack(side="left", padx=(0, 8))
        self.to_date_entry = tk.Entry(date_frame, font=FONT_SMALL, width=15,
                                      relief="solid", borderwidth=1)
        self.to_date_entry.pack(side="left")
        self.to_date_entry.insert(0, get_today_date())

        # Print method section
        tk.Label(main, text="Print Method", font=FONT_SECTION,
                bg=C["bg_root"], fg=C["text_mid"]).pack(anchor="w", pady=(0, 10))

        self.print_method = tk.StringVar(value="normal")

        tk.Radiobutton(main, text="📄 Normal Printer (A4, with formatting)",
                      variable=self.print_method, value="normal",
                      font=FONT_LABEL, bg=C["bg_root"],
                      fg=C["text_dark"]).pack(anchor="w", pady=5)

        tk.Radiobutton(main, text="🖨  POS58 Thermal Printer (receipt format)",
                      variable=self.print_method, value="pos58",
                      font=FONT_LABEL, bg=C["bg_root"],
                      fg=C["text_dark"]).pack(anchor="w", pady=5)

        # Buttons
        btn_frame = tk.Frame(main, bg=C["bg_root"])
        btn_frame.pack(fill="x", pady=(20, 0))

        _btn(btn_frame, "Print",
             lambda: self._print_report(self.from_date_entry.get(),
                                       self.to_date_entry.get(),
                                       self.print_method.get()),
             C["green"], "#16A34A",
             padx=20, pady=10).pack(side="left", padx=(0, 10))

        _btn(btn_frame, "Cancel",
             dialog.destroy,
             C["text_light"], "#9CA3AF",
             padx=20, pady=10).pack(side="left")

    def _print_report(self, from_date, to_date, method):
        """Generate and print report for date range."""
        # Validate dates
        try:
            datetime.strptime(from_date, "%Y-%m-%d")
            datetime.strptime(to_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Invalid Date", "Please use YYYY-MM-DD format")
            return

        # Load all sales
        sales = load_json(self._sales_path())

        # Filter by date range
        report_sales = []
        for sale in sales:
            sale_date = sale.get("date", "")
            if from_date <= sale_date <= to_date:
                report_sales.append(sale)

        if not report_sales:
            messagebox.showinfo("No Data", "No receipts found in this date range.")
            return

        if method == "pos58":
            self._print_pos58_report(report_sales, from_date, to_date)
        else:
            self._print_normal_report(report_sales, from_date, to_date)

    def _print_pos58_report(self, sales, from_date, to_date):
        """Generate POS58 thermal printer report."""
        try:
            import win32print
            import win32ui
            from win32.lib import win32con
        except:
            messagebox.showerror("Error", "Win32 printing not available")
            return

        lines = []
        lines.append("")

        # Logo placeholder (text-based)
        lines.append("        J U S T B")
        lines.append("   Stationery & Gifts")
        lines.append("")
        lines.append("=" * 42)
        lines.append("SALES REPORT".center(42))
        lines.append(f"From: {from_date}  To: {to_date}".center(42))
        lines.append("=" * 42)
        lines.append("")

        total_revenue = 0
        total_items = 0
        receipt_count = len(sales)

        for sale in sales:
            lines.append(f"Receipt #{sale.get('id', '?')}")
            lines.append(f"Date: {sale.get('date', '')}")
            items = sale.get("items", [])
            for item in items:
                name = item.get("name", "?")[:30]
                qty = item.get("quantity", 1)
                price = float(item.get("price", 0))
                subtotal = qty * price
                lines.append(f"  {name}")
                lines.append(f"    {qty} x EGP {price:.2f} = EGP {subtotal:.2f}")
                total_items += qty
            total = sale.get("total", 0)
            lines.append(f"Total: EGP {total:.2f}")
            total_revenue += total
            lines.append("-" * 42)
            lines.append("")

        # Summary
        lines.append("=" * 42)
        lines.append("SUMMARY".center(42))
        lines.append("=" * 42)
        lines.append(f"Receipts: {receipt_count}")
        lines.append(f"Items Sold: {total_items}")
        lines.append(f"Total Revenue: EGP {total_revenue:.2f}")
        lines.append("=" * 42)
        lines.append("Thank you!".center(42))
        lines.append("")

        report_text = "\n".join(lines)
        self._send_to_pos58(report_text)

    def _print_normal_report(self, sales, from_date, to_date):
        """Generate normal printer report (as text file or printed)."""
        lines = []
        lines.append("")
        lines.append("JUSTB - STATIONERY & GIFTS")
        lines.append("=" * 80)
        lines.append("SALES REPORT")
        lines.append(f"Report Period: {from_date} to {to_date}")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 80)
        lines.append("")

        total_revenue = 0
        total_items = 0
        total_discount = 0
        receipt_count = len(sales)

        for sale in sales:
            lines.append(f"Receipt #{sale.get('id', '?')} | Date: {sale.get('date', '')} | Time: {sale.get('time', '')}")
            lines.append(f"Cashier: {sale.get('user', '—')} | Payment: {sale.get('payment_method', '—')}")
            lines.append("-" * 80)

            items = sale.get("items", [])
            lines.append(f"{'Item':<40} {'Qty':>8} {'Price':>12} {'Total':>15}")
            lines.append("-" * 80)

            for item in items:
                name = item.get("name", "?")[:38]
                qty = item.get("quantity", 1)
                price = float(item.get("price", 0))
                subtotal = qty * price
                lines.append(f"{name:<40} {qty:>8} EGP {price:>10.2f} EGP {subtotal:>12.2f}")
                total_items += qty

            subtotal = sale.get("subtotal", 0)
            discount_amt = sale.get("discount_amt", 0)
            discount_pct = sale.get("discount_pct", 0)
            total = sale.get("total", 0)
            promo = sale.get("promo_code", "")

            lines.append("-" * 80)
            lines.append(f"Subtotal: {'EGP ' + str(round(subtotal, 2)):>71}")
            if discount_amt > 0:
                lines.append(f"Discount ({discount_pct}%): {'-EGP ' + str(round(discount_amt, 2)):>68}")
                total_discount += discount_amt
            if promo:
                lines.append(f"Promo Code: {promo:>68}")
            lines.append(f"{'RECEIPT TOTAL: EGP ' + str(round(total, 2)):>80}")
            lines.append("=" * 80)
            lines.append("")
            total_revenue += total

        # Summary
        lines.append("=" * 80)
        lines.append("SUMMARY".center(80))
        lines.append("=" * 80)
        lines.append(f"Period: {from_date} to {to_date}")
        lines.append(f"Total Receipts: {receipt_count}")
        lines.append(f"Total Items Sold: {total_items}")
        lines.append(f"Total Revenue: EGP {total_revenue:.2f}")
        if total_discount > 0:
            lines.append(f"Total Discounts: EGP {total_discount:.2f}")
        lines.append(f"Average Receipt: EGP {total_revenue/receipt_count:.2f}" if receipt_count > 0 else "Average Receipt: —")
        lines.append("=" * 80)
        lines.append("")
        lines.append("justb-eg.com")
        lines.append("")

        report_text = "\n".join(lines)

        # Save to file
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"JustB_Report_{from_date}_to_{to_date}.txt"
        )

        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(report_text)
            messagebox.showinfo("Success", f"Report saved:\n{file_path}")

    def _send_to_pos58(self, text):
        """Send text to POS58 thermal printer."""
        try:
            import win32print
            import win32ui
        except:
            messagebox.showerror("Error", "Win32 printing not available")
            return

        try:
            printer_name = win32print.GetDefaultPrinter()
            hprinter = win32print.OpenPrinter(printer_name)
            hdc = win32ui.CreateDC()
            hdc.CreatePrinterDC(printer_name)
            hdc.StartDoc(f"JustB_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            hdc.StartPage()

            # Print text
            hdc.TextOut(50, 50, text)

            hdc.EndPage()
            hdc.EndDoc()
            hdc.DeleteDC()
            win32print.ClosePrinter(hprinter)

            messagebox.showinfo("Success", "Report sent to POS58 printer!")
        except Exception as e:
            messagebox.showerror("Print Error", f"Failed to print:\n{str(e)}")